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
    daily_search_limit INTEGER DEFAULT 20,
    daily_deep_limit INTEGER DEFAULT 3,
    daily_litreview_limit INTEGER DEFAULT 0,
    daily_gap_analysis_limit INTEGER DEFAULT 0,
    daily_export_limit INTEGER DEFAULT 5,
    daily_digest_limit INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    PRIMARY KEY (user_id, paper_id)
  )`);

  // 初始化使用者基本資料
  await q(`INSERT OR IGNORE INTO users (user_id) VALUES (?)`, [SEED_USER_ID]);
  await q(
    `INSERT OR IGNORE INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit)
     VALUES (?, 'free', 10, 1, 0, 0, 3, 0)`,
    [SEED_USER_ID]
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
    user_lang: (u.rows[0]?.user_lang as string) || "zh_hant",
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
  const limits: Record<string, number[]> = {
    free: [10, 1, 0, 0, 3, 0],
    basic: [30, 5, 0, 0, 10, 0],
    standard: [100, 15, 3, 3, 30, 1],
    premium: [200, 30, 10, 10, 60, 3],
    ultra: [500, 50, 20, 20, 999999, 7],
  };
  const l = limits[tier] || limits.free;
  await q(
    `INSERT INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
     ON CONFLICT(user_id) DO UPDATE SET tier = ?, daily_search_limit = ?, daily_deep_limit = ?, daily_litreview_limit = ?, daily_gap_analysis_limit = ?, daily_export_limit = ?, daily_digest_limit = ?, updated_at = CURRENT_TIMESTAMP`,
    [currentUserId(), tier, ...l, tier, ...l]
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
    bibtex: row.bibtex || "",
    category: row.category || "人工智慧",
    user_notes: "",
    tags: ["已收藏"],
    is_starred: false,
    added_at: row.added_at || "",
  };
}

export async function getLibrary(): Promise<PaperItem[]> {
  const r = await q(
    `SELECT paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category, added_at
     FROM user_paper_library WHERE user_id = ? ORDER BY added_at DESC`,
    [currentUserId()]
  );
  return r.rows.map(rowToPaper);
}

export async function addPaper(paper: PaperItem): Promise<void> {
  const paper_id = paper.id || paper.fingerprint || `p_${Date.now()}`;
  const authors = JSON.stringify(paper.authors || []);
  await q(
    `INSERT INTO user_paper_library (user_id, paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(user_id, paper_id) DO UPDATE SET
       title = ?, authors = ?, year = ?, source = ?, link = ?, abstract = ?, fingerprint = ?, bibtex = ?, category = ?`,
    [
      currentUserId(), paper_id, paper.title, authors, paper.year, paper.source, paper.link, paper.summary, paper.fingerprint, paper.bibtex, paper.category || "人工智慧",
      paper.title, authors, paper.year, paper.source, paper.link, paper.summary, paper.fingerprint, paper.bibtex, paper.category || "人工智慧",
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
