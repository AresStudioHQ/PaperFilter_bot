import { createClient, type Client } from "@libsql/client";
import { AsyncLocalStorage } from "async_hooks";

const url = process.env.TURSO_DATABASE_URL;
const token = process.env.TURSO_AUTH_TOKEN;

if (!url || !token) {
  console.warn(
    "⚠️ 未偵測到 TURSO_DATABASE_URL / TURSO_AUTH_TOKEN，網頁端將無法與 Telegram bot 同步資料。"
  );
}

export const turso: Client = createClient({
  url: url || "file:local_fallback.db",
  authToken: token || "",
});

// @libsql/client v0.14 的 execute 僅接受單一物件引數 { sql, args }，
// 舊式 (sql, args) 雙引數在 TypeScript 下會報錯，故統一包一層。
async function q(sql: string, args: any[] = []): Promise<any> {
  return turso.execute({ sql, args });
}

// ===================== 多使用者上下文 =====================
// 每次 HTTP 請求由 server.ts 用 setUserContext(uid, ...) 包裹，
// 所有 db 函式透過 currentUserId() 取得「當前登入使用者」的 Telegram user_id，
// 藉此實現多租戶隔離（每位使用者只看得到自己的文獻庫）。
const userCtx = new AsyncLocalStorage<number>();

export function setUserContext(userId: number, fn: () => any): any {
  return userCtx.run(userId, fn);
}

export function currentUserId(): number {
  const id = userCtx.getStore();
  if (id == null) throw new Error("缺少使用者上下文（尚未登入）");
  return id;
}

// 僅供 initTables 初始化示範資料時使用
const SEED_USER_ID = Number(process.env.WEB_USER_ID || 88921473);

export interface PaperItem {
  id: string;
  fingerprint: string;
  title: string;
  summary: string;
  authors: string[];
  year: string;
  source: string;
  link: string;
  citations: number;
  is_open_access: boolean;
  is_top_journal: boolean;
  venue_name?: string;
  tier?: string | null;
  is_preprint?: boolean;
  credibility_label?: string;
  credibility_emoji?: string;
  score?: number;
  bibtex?: string;
  category?: string;
  user_notes?: string;
  tags?: string[];
  is_starred?: boolean;
  added_at?: string;
}

// 確保所需資料表存在（bot 通常已建好，此處僅做安全防護）
export async function initTables(): Promise<void> {
  await q(`CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    gdrive_token TEXT,
    positive_keywords TEXT DEFAULT '{}',
    negative_keywords TEXT DEFAULT '{}',
    filter_mode TEXT DEFAULT 'smart',
    user_lang TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )`);

  await q(`CREATE TABLE IF NOT EXISTS user_categories (
    user_id INTEGER,
    category_name TEXT,
    PRIMARY KEY (user_id, category_name)
  )`);

  await q(`CREATE TABLE IF NOT EXISTS author_tracking (
    user_id INTEGER,
    author_name TEXT,
    PRIMARY KEY (user_id, author_name)
  )`);

  await q(`CREATE TABLE IF NOT EXISTS user_tier (
    user_id INTEGER PRIMARY KEY,
    tier TEXT DEFAULT 'free',
    daily_search_limit INTEGER DEFAULT 500,
    daily_deep_limit INTEGER DEFAULT 50,
    daily_litreview_limit INTEGER DEFAULT 20,
    daily_gap_analysis_limit INTEGER DEFAULT 20,
    daily_export_limit INTEGER DEFAULT 5,
    daily_digest_limit INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )`);

  await q(`CREATE TABLE IF NOT EXISTS telegram_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_code TEXT UNIQUE,
    web_uid TEXT,
    telegram_user_id INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
  )`);

  await q(`CREATE TABLE IF NOT EXISTS user_paper_library (
    user_id INTEGER,
    paper_id TEXT,
    title TEXT,
    authors TEXT,
    year TEXT,
    source TEXT,
    link TEXT,
    abstract TEXT,
    fingerprint TEXT,
    bibtex TEXT,
    category TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    venue_name TEXT,
    tier TEXT,
    is_preprint INTEGER DEFAULT 0,
    credibility_emoji TEXT,
    credibility_label TEXT,
    PRIMARY KEY (user_id, paper_id)
  )`);

  // 欄位遷移（舊資料庫補上可信度欄位）
  await q(`ALTER TABLE user_paper_library ADD COLUMN venue_name TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN tier TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN is_preprint INTEGER DEFAULT 0`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN credibility_emoji TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN credibility_label TEXT`).catch(() => {});

  // 初始化使用者基本資料
  await q(`INSERT OR IGNORE INTO users (user_id) VALUES (?)`, [SEED_USER_ID]);
  await q(
    `INSERT OR IGNORE INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit)
     VALUES (?, 'free', 20, 5, 3, 3, 10, 2)`,
    [SEED_USER_ID]
  );
}

/** Create a free-tier row for a newly logged-in user so they never inherit demo Ultra data. */
export async function ensureUser(userId: number): Promise<void> {
  await q(`INSERT OR IGNORE INTO users (user_id) VALUES (?)`, [userId]);
  await q(
    `INSERT OR IGNORE INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit)
     VALUES (?, 'free', 20, 5, 3, 3, 10, 2)`,
    [userId]
  );
}

// ===================== Profile =====================
export interface DbProfile {
  user_id: number;
  tier: string;
  filter_mode: string;
  user_lang: string;
}

export async function getProfile(): Promise<DbProfile> {
  const u = await q(
    `SELECT filter_mode, user_lang FROM users WHERE user_id = ?`,
    [currentUserId()]
  );
  const t = await q(`SELECT tier FROM user_tier WHERE user_id = ?`, [currentUserId()]);
  return {
    user_id: currentUserId(),
    tier: (t.rows[0]?.tier as string) || "free",
    filter_mode: (u.rows[0]?.filter_mode as string) || "smart",
    user_lang: (u.rows[0]?.user_lang as string) || "en",
  };
}

export async function setFilterMode(mode: string): Promise<void> {
  await q(
    `INSERT INTO users (user_id, filter_mode) VALUES (?, ?)
     ON CONFLICT(user_id) DO UPDATE SET filter_mode = ?`,
    [currentUserId(), mode, mode]
  );
}

export async function setUserLang(lang: string): Promise<void> {
  await q(
    `INSERT INTO users (user_id, user_lang) VALUES (?, ?)
     ON CONFLICT(user_id) DO UPDATE SET user_lang = ?`,
    [currentUserId(), lang, lang]
  );
}

export async function setTier(tier: string): Promise<void> {
  const LIMITS: Record<string, Record<string, number>> = {
    free:     { daily_search_limit: 20, daily_deep_limit: 5, daily_litreview_limit: 3, daily_gap_analysis_limit: 3, daily_export_limit: 10, daily_digest_limit: 2 },
    basic:    { daily_search_limit: 50, daily_deep_limit: 15, daily_litreview_limit: 10, daily_gap_analysis_limit: 10, daily_export_limit: 25, daily_digest_limit: 5 },
    standard: { daily_search_limit: 150, daily_deep_limit: 50, daily_litreview_limit: 25, daily_gap_analysis_limit: 25, daily_export_limit: 80, daily_digest_limit: 10 },
    premium:  { daily_search_limit: 300, daily_deep_limit: 150, daily_litreview_limit: 100, daily_gap_analysis_limit: 100, daily_export_limit: 250, daily_digest_limit: 20 },
    ultra:    { daily_search_limit: 500, daily_deep_limit: 300, daily_litreview_limit: 999999, daily_gap_analysis_limit: 999999, daily_export_limit: 999999, daily_digest_limit: 50 },
    lab:      { daily_search_limit: 999999, daily_deep_limit: 999999, daily_litreview_limit: 999999, daily_gap_analysis_limit: 999999, daily_export_limit: 999999, daily_digest_limit: 999999 },
  };
  const l = LIMITS[tier] || LIMITS.free;
  await q(
    `INSERT INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
     ON CONFLICT(user_id) DO UPDATE SET tier = ?, daily_search_limit = ?, daily_deep_limit = ?, daily_litreview_limit = ?, daily_gap_analysis_limit = ?, daily_export_limit = ?, daily_digest_limit = ?, updated_at = CURRENT_TIMESTAMP`,
    [currentUserId(), tier, l.daily_search_limit, l.daily_deep_limit, l.daily_litreview_limit, l.daily_gap_analysis_limit, l.daily_export_limit, l.daily_digest_limit, tier, l.daily_search_limit, l.daily_deep_limit, l.daily_litreview_limit, l.daily_gap_analysis_limit, l.daily_export_limit, l.daily_digest_limit]
  );
}

// ===================== Library =====================
function rowToPaper(row: any): PaperItem {
  let authors: string[] = [];
  try {
    authors = JSON.parse(row.authors || "[]");
  } catch {
    authors = [];
  }
  return {
    id: String(row.paper_id),
    fingerprint: row.fingerprint || "",
    title: row.title || "",
    summary: row.abstract || "",
    authors,
    year: row.year || "",
    source: row.source || "",
    link: row.link || "",
    citations: 0,
    is_open_access: false,
    is_top_journal: false,
    venue_name: row.venue_name || "",
    tier: row.tier || null,
    is_preprint: Boolean(row.is_preprint),
    credibility_emoji: row.credibility_emoji || "",
    credibility_label: row.credibility_label || "",
    bibtex: row.bibtex || "",
    category: row.category || "AI",
    user_notes: "",
    tags: ["已收藏"],
    is_starred: false,
    added_at: row.added_at || "",
  };
}

export async function getLibrary(): Promise<PaperItem[]> {
  const r = await q(
    `SELECT paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category, added_at, venue_name, tier, is_preprint, credibility_emoji, credibility_label
     FROM user_paper_library WHERE user_id = ? ORDER BY added_at DESC`,
    [currentUserId()]
  );
  return r.rows.map(rowToPaper);
}

export async function addPaper(paper: PaperItem): Promise<void> {
  const paper_id = paper.id || paper.fingerprint || `p_${Date.now()}`;
  const authors = JSON.stringify(paper.authors || []);
  await q(
    `INSERT INTO user_paper_library (user_id, paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category, venue_name, tier, is_preprint, credibility_emoji, credibility_label)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(user_id, paper_id) DO UPDATE SET
       title = ?, authors = ?, year = ?, source = ?, link = ?, abstract = ?, fingerprint = ?, bibtex = ?, category = ?, venue_name = ?, tier = ?, is_preprint = ?, credibility_emoji = ?, credibility_label = ?`,
    [
      currentUserId(), paper_id, paper.title, authors, paper.year, paper.source, paper.link, paper.summary, paper.fingerprint, paper.bibtex, paper.category || "AI",
      paper.venue_name || "", paper.tier || null, paper.is_preprint ? 1 : 0, paper.credibility_emoji || "", paper.credibility_label || "",
      paper.title, authors, paper.year, paper.source, paper.link, paper.summary, paper.fingerprint, paper.bibtex, paper.category || "AI",
      paper.venue_name || "", paper.tier || null, paper.is_preprint ? 1 : 0, paper.credibility_emoji || "", paper.credibility_label || "",
    ]
  );
}

export async function updatePaper(
  id: string,
  fields: { user_notes?: string; tags?: string[]; is_starred?: boolean; category?: string }
): Promise<void> {
  const sets: string[] = [];
  const args: any[] = [];
  if (fields.user_notes !== undefined) {
    sets.push("abstract = abstract"); // no-op placeholder to keep sql valid; notes not stored in this table
  }
  if (fields.category !== undefined) {
    sets.push("category = ?");
    args.push(fields.category);
  }
  if (sets.length === 0) return;
  await q(
    `UPDATE user_paper_library SET ${sets.join(", ")} WHERE user_id = ? AND paper_id = ?`,
    [...args, currentUserId(), id]
  );
}

export async function removePaper(id: string): Promise<void> {
  await q(
    `DELETE FROM user_paper_library WHERE user_id = ? AND (paper_id = ? OR fingerprint = ?)`,
    [currentUserId(), id, id]
  );
}

// ===================== Categories =====================
export async function getCategories(): Promise<string[]> {
  const r = await q(
    `SELECT category_name FROM user_categories WHERE user_id = ? ORDER BY category_name`,
    [currentUserId()]
  );
  return r.rows.map((row) => row.category_name as string);
}

export async function addCategory(name: string): Promise<void> {
  const clean = name.trim();
  if (!clean) return;
  await q(
    `INSERT OR IGNORE INTO user_categories (user_id, category_name) VALUES (?, ?)`,
    [currentUserId(), clean]
  );
}

export async function renameCategory(oldName: string, newName: string): Promise<void> {
  await q(
    `UPDATE user_categories SET category_name = ? WHERE user_id = ? AND category_name = ?`,
    [newName.trim(), currentUserId(), oldName.trim()]
  );
  await q(
    `UPDATE user_paper_library SET category = ? WHERE user_id = ? AND category = ?`,
    [newName.trim(), currentUserId(), oldName.trim()]
  );
}

export async function deleteCategory(name: string): Promise<void> {
  await q(
    `DELETE FROM user_categories WHERE user_id = ? AND category_name = ?`,
    [currentUserId(), name.trim()]
  );
}

// ===================== Authors =====================
export async function getAuthors(): Promise<string[]> {
  const r = await q(
    `SELECT author_name FROM author_tracking WHERE user_id = ? ORDER BY author_name`,
    [currentUserId()]
  );
  return r.rows.map((row) => row.author_name as string);
}

export async function addAuthor(name: string): Promise<void> {
  const clean = name.trim();
  if (!clean) return;
  await q(
    `INSERT OR IGNORE INTO author_tracking (user_id, author_name) VALUES (?, ?)`,
    [currentUserId(), clean]
  );
}

export async function removeAuthor(name: string): Promise<void> {
  await q(
    `DELETE FROM author_tracking WHERE user_id = ? AND author_name = ?`,
    [currentUserId(), name.trim()]
  );
}

// ===================== Telegram ↔ Web 綁定 =====================
// 驗證碼僅為暫時憑證；用戶資料始終以 telegram_user_id 為鍵，與碼無關。
// Bot 端的 /bind <code> 會呼叫對應的 link 邏輯，把 telegram_user_id 寫入同一張表。
export async function createBindCode(webUid: number, ttlMinutes = 10): Promise<string> {
  await q(
    `UPDATE telegram_links SET status='expired' WHERE web_uid=? AND status='pending'`,
    [webUid]
  );
  for (let i = 0; i < 20; i++) {
    const code = "PF" + Math.floor(100000 + Math.random() * 900000);
    try {
      await q(
        `INSERT INTO telegram_links (link_code, web_uid, status, expires_at)
         VALUES (?, ?, 'pending', datetime('now', '+${ttlMinutes} minutes'))`,
        [code, webUid]
      );
      return code;
    } catch (e) {
      continue; // link_code UNIQUE 衝突 → 重試
    }
  }
  throw new Error("無法產生唯一綁定碼");
}

export async function getPendingCode(webUid: number): Promise<string | null> {
  const r = await q(
    `SELECT link_code FROM telegram_links
     WHERE web_uid=? AND status='pending' AND expires_at > datetime('now')
     ORDER BY id DESC LIMIT 1`,
    [webUid]
  );
  return (r.rows[0]?.link_code as string) || null;
}

export async function getLinkByWeb(webUid: number): Promise<any> {
  const r = await q(
    `SELECT id, link_code, web_uid, telegram_user_id, status
     FROM telegram_links WHERE (web_uid=? OR telegram_user_id=?) AND status='linked' ORDER BY id DESC LIMIT 1`,
    [webUid, webUid]
  );
  return r.rows[0] || null;
}

// 綁定後把網頁端（webUid）既有的資料併入 Telegram 帳號（tgUid），衝突者忽略
export async function migrateWebToTelegram(webUid: number, tgUid: number): Promise<void> {
  if (webUid === tgUid) return;
  await q(
    `INSERT OR IGNORE INTO user_paper_library
       (user_id, fingerprint, title, authors, year, venue, citation_count, link, abstract,
        category, note, is_read, is_skipped, read_at, archived, relevance_score, created_at)
     SELECT ?, fingerprint, title, authors, year, venue, citation_count, link, abstract,
        category, note, is_read, is_skipped, read_at, archived, relevance_score, created_at
     FROM user_paper_library WHERE user_id=?`,
    [tgUid, webUid]
  );
  await q(`DELETE FROM user_paper_library WHERE user_id=?`, [webUid]);
  await q(
    `INSERT OR IGNORE INTO user_categories (user_id, category_name)
     SELECT ?, category_name FROM user_categories WHERE user_id=?`,
    [tgUid, webUid]
  );
  await q(`DELETE FROM user_categories WHERE user_id=?`, [webUid]);
  await q(
    `INSERT OR IGNORE INTO author_tracking (user_id, author_name)
     SELECT ?, author_name FROM author_tracking WHERE user_id=?`,
    [tgUid, webUid]
  );
  await q(`DELETE FROM author_tracking WHERE user_id=?`, [webUid]);
  await q(
    `UPDATE user_tier SET user_id=? WHERE user_id=? AND NOT EXISTS (SELECT 1 FROM user_tier t WHERE t.user_id=?)`,
    [tgUid, webUid, tgUid]
  );
  await q(`DELETE FROM user_tier WHERE user_id=?`, [webUid]);
}
