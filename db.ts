import { createClient, type Client } from "@libsql/client";
import { AsyncLocalStorage } from "async_hooks";
import { TIER_DEFS, normalizeTier, type TierCode } from "./src/subscriptionTiers";

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

const FREE_LIMITS = TIER_DEFS.free;

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

export type QuotaAction = "search" | "deep" | "litreview" | "gap_analysis" | "export" | "digest" | "chat";

export interface QuotaResult {
  allowed: boolean;
  error?: string;
  used?: number;
  limit?: number;
}

export interface ActivityRow {
  id: number;
  user_id: number;
  action: string;
  paper_id: string | null;
  paper_title: string | null;
  details: string | null;
  created_at: string;
}

export interface ActivityInput {
  action: string;
  paper_id?: string;
  paper_title?: string;
  details?: string;
}

const QUOTA_COL: Record<QuotaAction, string> = {
  search: "searches",
  deep: "deep_reads",
  litreview: "lit_reviews",
  gap_analysis: "gap_analyses",
  export: "exports",
  digest: "digests",
  chat: "chats",
};

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

function utcWeekStartMonday(): string {
  const now = new Date();
  const utc = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const day = utc.getUTCDay(); // 0 Sun … 6 Sat
  const diff = day === 0 ? 6 : day - 1;
  utc.setUTCDate(utc.getUTCDate() - diff);
  return utc.toISOString().slice(0, 10);
}

function parseJsonArray(raw: any): string[] {
  try {
    const v = typeof raw === "string" ? JSON.parse(raw || "[]") : raw;
    return Array.isArray(v) ? v.map(String) : [];
  } catch {
    return [];
  }
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
    user_notes TEXT,
    tags TEXT,
    is_starred INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, paper_id)
  )`);

  await q(`CREATE TABLE IF NOT EXISTS usage_tracking (
    user_id INTEGER,
    date TEXT,
    searches INTEGER DEFAULT 0,
    deep_reads INTEGER DEFAULT 0,
    lit_reviews INTEGER DEFAULT 0,
    gap_analyses INTEGER DEFAULT 0,
    exports INTEGER DEFAULT 0,
    digests INTEGER DEFAULT 0,
    chats INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date)
  )`);

  await q(`CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    paper_id TEXT,
    paper_title TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )`);

  await q(`CREATE TABLE IF NOT EXISTS promo_codes (
    code TEXT PRIMARY KEY,
    note TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    redeem_deadline TIMESTAMP,
    redeemed_by INTEGER,
    redeemed_at TIMESTAMP,
    status TEXT DEFAULT 'unused'
  )`);
  await q(`CREATE TABLE IF NOT EXISTS launch_waitlist (
    user_id INTEGER PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT DEFAULT ''
  )`);
  await q(`CREATE TABLE IF NOT EXISTS beta_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    body TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )`);

  // 欄位遷移（舊資料庫補上可信度 / 筆記 / 配額欄位）
  await q(`ALTER TABLE user_paper_library ADD COLUMN venue_name TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN tier TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN is_preprint INTEGER DEFAULT 0`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN credibility_emoji TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN credibility_label TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN user_notes TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN tags TEXT`).catch(() => {});
  await q(`ALTER TABLE user_paper_library ADD COLUMN is_starred INTEGER DEFAULT 0`).catch(() => {});

  await q(`ALTER TABLE user_tier ADD COLUMN tier_expires_at TEXT`).catch(() => {});
  await q(`ALTER TABLE user_tier ADD COLUMN is_founder INTEGER DEFAULT 0`).catch(() => {});
  await q(`ALTER TABLE user_tier ADD COLUMN expiry_notified INTEGER DEFAULT 0`).catch(() => {});
  await q(`ALTER TABLE user_tier ADD COLUMN daily_chat_limit INTEGER DEFAULT 2`).catch(() => {});

  await q(`ALTER TABLE usage_tracking ADD COLUMN chats INTEGER DEFAULT 0`).catch(() => {});

  // 初始化使用者基本資料
  await q(`INSERT OR IGNORE INTO users (user_id) VALUES (?)`, [SEED_USER_ID]);
  await q(
    `INSERT OR IGNORE INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit)
     VALUES (?, 'free', ?, ?, ?, ?, ?, ?)`,
    [
      SEED_USER_ID,
      FREE_LIMITS.daily_search_limit,
      FREE_LIMITS.daily_deep_limit,
      FREE_LIMITS.daily_litreview_limit,
      FREE_LIMITS.daily_gap_analysis_limit,
      FREE_LIMITS.daily_export_limit,
      FREE_LIMITS.daily_digest_limit,
    ]
  );
}

/** Create a free-tier row for a newly logged-in user so they never inherit demo Ultra data. */
export async function ensureUser(userId: number): Promise<void> {
  await q(`INSERT OR IGNORE INTO users (user_id) VALUES (?)`, [userId]);
  await q(
    `INSERT OR IGNORE INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit)
     VALUES (?, 'free', ?, ?, ?, ?, ?, ?)`,
    [
      userId,
      FREE_LIMITS.daily_search_limit,
      FREE_LIMITS.daily_deep_limit,
      FREE_LIMITS.daily_litreview_limit,
      FREE_LIMITS.daily_gap_analysis_limit,
      FREE_LIMITS.daily_export_limit,
      FREE_LIMITS.daily_digest_limit,
    ]
  );
}

// ===================== Profile =====================
export interface DbProfile {
  user_id: number;
  tier: string;
  filter_mode: string;
  user_lang: string;
  tier_expires_at?: string | null;
}

export async function getProfile(): Promise<DbProfile> {
  const uid = currentUserId();
  const u = await q(
    `SELECT filter_mode, user_lang FROM users WHERE user_id = ?`,
    [uid]
  );
  let t: any;
  try {
    t = await q(
      `SELECT tier, tier_expires_at, is_founder FROM user_tier WHERE user_id = ?`,
      [uid]
    );
  } catch {
    t = await q(`SELECT tier FROM user_tier WHERE user_id = ?`, [uid]);
  }
  const row = t.rows[0] || {};
  let tier = normalizeTier(row.tier as string);
  let expires = (row.tier_expires_at as string) || null;
  const isFounder = Boolean(row.is_founder);

  if (expires && !isFounder && tier !== "free") {
    try {
      if (Date.now() > new Date(expires).getTime()) {
        await setTier("free");
        tier = "free";
        expires = null;
      }
    } catch {
      // malformed expiry — keep current normalized tier
    }
  }

  return {
    user_id: uid,
    tier,
    filter_mode: (u.rows[0]?.filter_mode as string) || "smart",
    user_lang: (u.rows[0]?.user_lang as string) || "en",
    tier_expires_at: expires,
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
  const t: TierCode = tier === "pro" ? "pro" : "free";
  const l = TIER_DEFS[t];
  const uid = currentUserId();
  await q(
    `INSERT INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
     ON CONFLICT(user_id) DO UPDATE SET tier = ?, daily_search_limit = ?, daily_deep_limit = ?, daily_litreview_limit = ?, daily_gap_analysis_limit = ?, daily_export_limit = ?, daily_digest_limit = ?, updated_at = CURRENT_TIMESTAMP`,
    [
      uid, t, l.daily_search_limit, l.daily_deep_limit, l.daily_litreview_limit, l.daily_gap_analysis_limit, l.daily_export_limit, l.daily_digest_limit,
      t, l.daily_search_limit, l.daily_deep_limit, l.daily_litreview_limit, l.daily_gap_analysis_limit, l.daily_export_limit, l.daily_digest_limit,
    ]
  );
  await q(
    `UPDATE user_tier SET daily_chat_limit = ? WHERE user_id = ?`,
    [l.daily_chat_limit, uid]
  ).catch(() => {});
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
    user_notes: row.user_notes || "",
    tags: parseJsonArray(row.tags),
    is_starred: Boolean(Number(row.is_starred) || row.is_starred),
    added_at: row.added_at || "",
  };
}

export async function getLibrary(): Promise<PaperItem[]> {
  const r = await q(
    `SELECT paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category, added_at, venue_name, tier, is_preprint, credibility_emoji, credibility_label, user_notes, tags, is_starred
     FROM user_paper_library WHERE user_id = ? ORDER BY added_at DESC`,
    [currentUserId()]
  );
  return r.rows.map(rowToPaper);
}

export async function addPaper(paper: PaperItem): Promise<void> {
  const paper_id = paper.id || paper.fingerprint || `p_${Date.now()}`;
  const authors = JSON.stringify(paper.authors || []);
  const uid = currentUserId();
  const existing = await q(
    `SELECT 1 FROM user_paper_library WHERE user_id = ? AND paper_id = ?`,
    [uid, paper_id]
  );
  if (!existing.rows[0]) {
    const profile = await getProfile();
    const limit = TIER_DEFS[normalizeTier(profile.tier)].library_limit;
    const cnt = await q(
      `SELECT COUNT(*) AS n FROM user_paper_library WHERE user_id = ?`,
      [uid]
    );
    const used = Number(cnt.rows[0]?.n || 0);
    if (used >= limit) {
      const err: any = new Error(`文獻庫已達方案上限 (${used}/${limit})`);
      err.code = "LIBRARY_FULL";
      throw err;
    }
  }
  const tags = JSON.stringify(paper.tags || []);
  const notes = paper.user_notes || "";
  const starred = paper.is_starred ? 1 : 0;
  await q(
    `INSERT INTO user_paper_library (user_id, paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category, venue_name, tier, is_preprint, credibility_emoji, credibility_label, user_notes, tags, is_starred)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(user_id, paper_id) DO UPDATE SET
       title = ?, authors = ?, year = ?, source = ?, link = ?, abstract = ?, fingerprint = ?, bibtex = ?, category = ?, venue_name = ?, tier = ?, is_preprint = ?, credibility_emoji = ?, credibility_label = ?, user_notes = ?, tags = ?, is_starred = ?`,
    [
      uid, paper_id, paper.title, authors, paper.year, paper.source, paper.link, paper.summary, paper.fingerprint, paper.bibtex, paper.category || "AI",
      paper.venue_name || "", paper.tier || null, paper.is_preprint ? 1 : 0, paper.credibility_emoji || "", paper.credibility_label || "", notes, tags, starred,
      paper.title, authors, paper.year, paper.source, paper.link, paper.summary, paper.fingerprint, paper.bibtex, paper.category || "AI",
      paper.venue_name || "", paper.tier || null, paper.is_preprint ? 1 : 0, paper.credibility_emoji || "", paper.credibility_label || "", notes, tags, starred,
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
    sets.push("user_notes = ?");
    args.push(fields.user_notes);
  }
  if (fields.tags !== undefined) {
    sets.push("tags = ?");
    args.push(JSON.stringify(fields.tags));
  }
  if (fields.is_starred !== undefined) {
    sets.push("is_starred = ?");
    args.push(fields.is_starred ? 1 : 0);
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

// ===================== Quota =====================
export async function checkQuota(action: QuotaAction): Promise<QuotaResult> {
  const uid = currentUserId();
  const profile = await getProfile();
  const defs = TIER_DEFS[normalizeTier(profile.tier)];
  const limitMap: Record<QuotaAction, number> = {
    search: defs.daily_search_limit,
    deep: defs.daily_deep_limit,
    litreview: defs.daily_litreview_limit,
    gap_analysis: defs.daily_gap_analysis_limit,
    export: defs.daily_export_limit,
    digest: defs.daily_digest_limit,
    chat: defs.daily_chat_limit,
  };
  const col = QUOTA_COL[action];
  const limit = limitMap[action];
  if (limit <= 0) {
    return { allowed: false, error: `您的方案 (${profile.tier}) 不支援此功能，請升級訂閱。`, used: 0, limit };
  }
  if (limit >= 999999) {
    return { allowed: true, used: 0, limit };
  }
  if (action === "digest") {
    const weekStart = utcWeekStartMonday();
    const r = await q(
      `SELECT COALESCE(SUM(${col}), 0) AS n FROM usage_tracking WHERE user_id = ? AND date >= ?`,
      [uid, weekStart]
    );
    const used = Number(r.rows[0]?.n || 0);
    if (used >= limit) {
      return { allowed: false, error: `本週 AI Report 配額已用盡 (${used}/${limit})，下週一重置或升級方案。`, used, limit };
    }
    return { allowed: true, used, limit };
  }
  const today = utcToday();
  const r = await q(
    `SELECT ${col} FROM usage_tracking WHERE user_id = ? AND date = ?`,
    [uid, today]
  );
  const used = Number(r.rows[0]?.[col] || 0);
  if (used >= limit) {
    return { allowed: false, error: `今日 ${action} 配額已用盡 (${used}/${limit})，請明天再試或升級方案。`, used, limit };
  }
  return { allowed: true, used, limit };
}

export async function incrementUsage(action: QuotaAction): Promise<void> {
  const col = QUOTA_COL[action];
  if (!col) return;
  const today = utcToday();
  await q(
    `INSERT INTO usage_tracking (user_id, date, ${col})
     VALUES (?, ?, 1)
     ON CONFLICT(user_id, date) DO UPDATE SET ${col} = ${col} + 1`,
    [currentUserId(), today]
  );
}

export async function getUsageToday(): Promise<Record<string, number>> {
  const r = await q(
    `SELECT searches, deep_reads, lit_reviews, gap_analyses, exports, digests, chats
     FROM usage_tracking WHERE user_id = ? AND date = ?`,
    [currentUserId(), utcToday()]
  );
  const row = r.rows[0] || {};
  return {
    searches: Number(row.searches || 0),
    deep_reads: Number(row.deep_reads || 0),
    lit_reviews: Number(row.lit_reviews || 0),
    gap_analyses: Number(row.gap_analyses || 0),
    exports: Number(row.exports || 0),
    digests: Number(row.digests || 0),
    chats: Number(row.chats || 0),
  };
}

// ===================== Promo codes =====================
const PROMO_ACCESS_DAYS = 7;

export async function redeemPromoCode(code: string): Promise<{ ok: boolean; expiresAt?: string; errorKey?: string }> {
  const uid = currentUserId();
  const normalized = (code || "").trim().toUpperCase();
  if (!normalized) return { ok: false, errorKey: "promo_invalid" };
  const r = await q(
    `SELECT status, redeem_deadline, redeemed_by FROM promo_codes WHERE code = ?`,
    [normalized]
  );
  const row = r.rows[0];
  if (!row) return { ok: false, errorKey: "promo_invalid" };
  if (String(row.status || "") === "used") return { ok: false, errorKey: "promo_already_used" };
  try {
    const deadline = row.redeem_deadline ? new Date(row.redeem_deadline as string) : null;
    if (deadline && Date.now() > deadline.getTime()) {
      await q(`UPDATE promo_codes SET status = 'expired' WHERE code = ?`, [normalized]);
      return { ok: false, errorKey: "promo_expired" };
    }
  } catch {
    return { ok: false, errorKey: "promo_invalid" };
  }
  const expiresAt = new Date(Date.now() + PROMO_ACCESS_DAYS * 86400000).toISOString();
  await setTier("pro");
  await q(
    `UPDATE user_tier SET tier_expires_at = ?, expiry_notified = 0 WHERE user_id = ?`,
    [expiresAt, uid]
  ).catch(async () => {
    await q(`ALTER TABLE user_tier ADD COLUMN tier_expires_at TEXT`).catch(() => {});
    await q(`ALTER TABLE user_tier ADD COLUMN expiry_notified INTEGER DEFAULT 0`).catch(() => {});
    await q(
      `UPDATE user_tier SET tier_expires_at = ? WHERE user_id = ?`,
      [expiresAt, uid]
    );
  });
  await q(
    `UPDATE promo_codes SET status = 'used', redeemed_by = ?, redeemed_at = CURRENT_TIMESTAMP WHERE code = ?`,
    [uid, normalized]
  );
  return { ok: true, expiresAt };
}

// ===================== Activity =====================
export async function logActivity(input: ActivityInput): Promise<void> {
  await q(
    `INSERT INTO user_activity (user_id, action, paper_id, paper_title, details)
     VALUES (?, ?, ?, ?, ?)`,
    [currentUserId(), input.action, input.paper_id || null, input.paper_title || null, input.details || null]
  );
}

export async function listActivity(limit = 80): Promise<ActivityRow[]> {
  const r = await q(
    `SELECT id, user_id, action, paper_id, paper_title, details, created_at
     FROM user_activity WHERE user_id = ? ORDER BY id DESC LIMIT ?`,
    [currentUserId(), limit]
  );
  return r.rows.map((row: any) => ({
    id: Number(row.id),
    user_id: Number(row.user_id),
    action: String(row.action || ""),
    paper_id: row.paper_id || null,
    paper_title: row.paper_title || null,
    details: row.details || null,
    created_at: String(row.created_at || ""),
  }));
}

export async function getActivityStats(): Promise<{
  total: number;
  read: number;
  archived: number;
  skipped: number;
  deep: number;
}> {
  const r = await q(
    `SELECT action, COUNT(*) AS n FROM user_activity WHERE user_id = ? GROUP BY action`,
    [currentUserId()]
  );
  const by: Record<string, number> = {};
  let total = 0;
  for (const row of r.rows) {
    const n = Number(row.n || 0);
    by[String(row.action)] = n;
    total += n;
  }
  return {
    total,
    read: (by.search || 0) + (by.seen || 0),
    archived: by.archive || 0,
    skipped: by.skip || 0,
    deep: by.deep_read || 0,
  };
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

export async function joinWaitlist(note = ""): Promise<{ already: boolean }> {
  const uid = currentUserId();
  const existing = await q(`SELECT user_id FROM launch_waitlist WHERE user_id = ?`, [uid]);
  if (existing.rows[0]) return { already: true };
  await q(
    `INSERT INTO launch_waitlist (user_id, note) VALUES (?, ?)`,
    [uid, String(note || "").slice(0, 500)]
  );
  return { already: false };
}
