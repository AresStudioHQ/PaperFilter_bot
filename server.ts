import express from "express";
import path from "path";
import fs from "fs";
import { createServer as createViteServer } from "vite";
import OpenAI from "openai";
import dotenv from "dotenv";
import { createHmac, createHash } from "crypto";
import {
  initTables,
  getProfile,
  setFilterMode,
  setUserLang,
  getLibrary,
  addPaper,
  updatePaper,
  removePaper,
  getCategories,
  addCategory,
  renameCategory,
  deleteCategory,
  getAuthors,
  addAuthor,
  removeAuthor,
  setUserContext,
  currentUserId,
  createBindCode,
  getLinkByWeb,
  getPendingCode,
  migrateWebToTelegram,
  ensureUser,
  checkQuota,
  incrementUsage,
  logActivity,
  listActivity,
  getActivityStats,
  redeemPromoCode,
  type PaperItem,
  type QuotaAction,
} from "./db";
import { getVenueTier, credibilityBadge, isPreprint } from "./src/academicTiers";
import { TIER_DEFS, TIER_PRICES, normalizeTier, hasPaidTier, isUnlimited } from "./src/subscriptionTiers";

dotenv.config();

const app = express();
const PORT = Number(process.env.PORT) || 3000;

app.use(express.json());

// ================= Telegram Login（多使用者） =================
function getCookie(req: any, name: string): string | null {
  const c = req.headers.cookie;
  if (!c) return null;
  const m = c.split(";").map((s) => s.trim()).find((s) => s.startsWith(name + "="));
  return m ? decodeURIComponent(m.slice(name.length + 1)) : null;
}
function getUid(req: any): number | null {
  const v = getCookie(req, "uid");
  return v ? Number(v) : null;
}
function verifyTelegramAuth(data: any): boolean {
  const token = process.env.TELEGRAM_BOT_TOKEN || process.env.TELEGRAM_TOKEN;
  if (!token) {
    console.error("⚠️ 缺少 TELEGRAM_BOT_TOKEN，無法驗證 Telegram 登入");
    return false;
  }
  const { hash, ...rest } = data;
  if (!hash) return false;
  const buildCheck = (obj: any) =>
    Object.keys(obj).sort().map((k) => `${k}=${obj[k]}`).join("\n");
  // Login Widget：secret = SHA256(bot_token)；Mini App：secret = HMAC("WebAppData", bot_token)
  const secrets = [
    createHash("sha256").update(token).digest(),
    createHmac("sha256", "WebAppData").update(token).digest(),
  ];
  const withoutPhoto = { ...rest };
  delete withoutPhoto.photo_url;
  for (const sec of secrets) {
    if (
      createHmac("sha256", sec).update(buildCheck(rest)).digest("hex") === hash ||
      createHmac("sha256", sec).update(buildCheck(withoutPhoto)).digest("hex") === hash
    ) {
      if (Math.floor(Date.now() / 1000) - Number(data.auth_date) > 86400) {
        console.error("⚠️ Telegram 登入 auth_date 過期（auth_date=" + data.auth_date + "）");
        return false;
      }
      return true;
    }
  }
  console.error("⚠️ Telegram 登入 hash 不符（configured bot_username=" + (process.env.TELEGRAM_BOT_USERNAME || "PaperFilterBot(預設未設定)") + "）");
  return false;
}

// 登入保護：除公開路徑外，所有 /api 都必須帶有效的 uid cookie
// 注意：middleware 掛載在 /api 下，req.path 為相對路徑（不含 /api 前綴）
const PUBLIC_PATHS = new Set([
  "/auth/telegram-login",
  "/auth/config",
  "/auth/logout",
  "/auth/generate-code",
  "/auth/bind-telegram",
]);
app.use("/api", (req, res, next) => {
  if (PUBLIC_PATHS.has(req.path)) return next();
  const uid = getUid(req);
  if (!uid) return res.status(401).json({ success: false, error: "請先登入", loginRequired: true });
  return setUserContext(uid, async () => { await next(); });
});

let userBias = {
  positive: {} as Record<string, number>,
  negative: {} as Record<string, number>
};

async function enforceQuota(res: any, action: QuotaAction): Promise<boolean> {
  const result = await checkQuota(action);
  if (!result.allowed) {
    res.status(429).json({ success: false, error: result.error, quota: true });
    return false;
  }
  return true;
}

function activityToHistoryItem(row: { id: number; action: string; paper_title: string | null; details: string | null; created_at: string }) {
  return {
    id: String(row.id),
    action: row.action,
    paper_title: row.paper_title || "",
    timestamp: row.created_at,
    details: row.details || "",
  };
}

// ================= Profile builder =================
async function buildProfile() {
  const dbp = await getProfile();
  const webUid = currentUserId();
  const link = await getLinkByWeb(webUid);
  const syncCode = (await getPendingCode(webUid)) || (await createBindCode(webUid));
  let stats = { total: 0, read: 0, archived: 0, skipped: 0, deep: 0 };
  try {
    stats = await getActivityStats();
  } catch {
    // user_activity may not exist on a brand-new DB until initTables finishes
  }
  const tier = normalizeTier(dbp.tier);
  return {
    user_id: webUid,
    username: "",
    telegram_handle: "",
    is_telegram_linked: !!link,
    telegram_id: link ? link.telegram_user_id : null,
    sync_code: syncCode,
    tier,
    pro_expires_at: dbp.tier_expires_at || "",
    filter_mode: dbp.filter_mode,
    user_lang: dbp.user_lang,
    total_read_count: stats.read,
    total_archived_count: stats.archived,
    total_skipped_count: stats.skipped,
    total_deep_read_count: stats.deep,
    history_count: stats.total,
    is_pro: hasPaidTier(tier),
    pro_price: TIER_PRICES.pro,
  };
}

async function loadLibrary(): Promise<PaperItem[]> {
  return getLibrary();
}

// 模型 -> 所需最低訂閱方案（全部使用 GPT-4o-mini，統一低成本）
const MODEL_TIERS: Record<string, "free" | "basic" | "standard" | "premium" | "ultra"> = {
  "gpt-4o-mini": "free",
};
const TIER_RANK: Record<string, number> = { free: 0, basic: 1, standard: 2, premium: 3, ultra: 4, lab: 5 };

function getOpenAIClient(): OpenAI | null {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return null;
  return new OpenAI({ apiKey, baseURL: process.env.OPENAI_BASE_URL });
}

// 統一 AI 呼叫：全部使用 GPT-4o-mini（低成本、高速度）
async function generateAIContent({ contents }: { contents: string; model?: string }): Promise<{ text: string }> {
  const openai = getOpenAIClient();
  if (!openai) {
    const err: any = new Error("AI 服務尚未設定 API Key");
    err.code = "NO_KEY";
    throw err;
  }
  const resp = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: contents }],
  });
  return { text: resp.choices[0]?.message?.content || "" };
}

// 相容舊呼叫介面：web 端點仍呼叫 gemini.models.generateContent(...)
function getGeminiClient(): any {
  return { models: { generateContent: (args: any) => generateAIContent(args) } };
}

// 5 大官方學術庫即時查詢 (arXiv, PubMed, Semantic Scholar, CrossRef, OpenAlex)
async function fetchAcademicPapers(query: string, mode: string = "smart") {
  const words = query.trim().split(/\s+/).filter(Boolean);
  const results: PaperItem[] = [];

  // 1. Semantic Scholar
  try {
    const s2Url = `https://api.semanticscholar.org/graph/v1/paper/search?query=${encodeURIComponent(query)}&limit=8&fields=title,abstract,authors,year,publicationDate,citationCount,url,isOpenAccess,openAccessPdf`;
    const res = await fetch(s2Url, {
      headers: { "User-Agent": "PaperFilterBot/3.0" },
      signal: AbortSignal.timeout(6000)
    });
    if (res.ok) {
      const data = await res.json();
      for (const p of data.data || []) {
        if (!p.title || !p.abstract) continue;
        const authors = (p.authors || []).map((a: any) => a.name).filter(Boolean);
        const pubDate = p.publicationDate || (p.year ? `${p.year}-01-01` : new Date().toISOString().slice(0, 10));
        const citations = p.citationCount || 0;
        const id = p.paperId ? `s2_${p.paperId.slice(0, 16)}` : `s2_${Date.now()}`;
        const fp = p.title.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 50);
        const link = p.openAccessPdf?.url || p.url || `https://www.semanticscholar.org/paper/${p.paperId}`;
        results.push({
          id,
          fingerprint: fp,
          title: p.title,
          summary: p.abstract,
          authors,
          year: pubDate,
          source: "Semantic Scholar (權威庫)",
          link,
          citations,
          is_open_access: Boolean(p.isOpenAccess || p.openAccessPdf),
          is_top_journal: citations >= 20
        });
      }
    }
  } catch (err) {
    console.warn("Semantic Scholar fetch skipped/failed:", err);
  }

  // 2. CrossRef
  try {
    const crUrl = `https://api.crossref.org/works?query=${encodeURIComponent(query)}&rows=6&sort=relevance`;
    const res = await fetch(crUrl, {
      headers: { "User-Agent": "PaperFilterBot/3.0 (mailto:paperfilter-bot@example.com)" },
      signal: AbortSignal.timeout(6000)
    });
    if (res.ok) {
      const data = await res.json();
      for (const item of data.message?.items || []) {
        const title = item.title?.[0] || "";
        if (!title) continue;
        const rawAbstract = item.abstract || "";
        const abstract = rawAbstract.replace(/<[^>]+>/g, "").trim() || `發表於國際頂級學術期刊: ${item["container-title"]?.[0] || "CrossRef 權威來源"}`;
        const authors = (item.author || []).map((a: any) => `${a.given || ""} ${a.family || ""}`.trim()).filter(Boolean);
        const dateParts = item["published-print"]?.["date-parts"]?.[0] || item["published-online"]?.["date-parts"]?.[0] || item.created?.["date-parts"]?.[0];
        let exactDate = new Date().toISOString().slice(0, 10);
        if (dateParts && dateParts.length > 0) {
          const y = String(dateParts[0]);
          const m = dateParts[1] ? String(dateParts[1]).padStart(2, "0") : "01";
          const d = dateParts[2] ? String(dateParts[2]).padStart(2, "0") : "01";
          exactDate = `${y}-${m}-${d}`;
        }
        const citations = item["is-referenced-by-count"] || 0;
        const doi = item.DOI || "";
        const link = doi ? `https://doi.org/${doi}` : (item.URL || "#");
        const fp = title.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 50);
        const venueName = item["container-title"]?.[0] || "";
        results.push({
          id: doi ? `doi_${doi.replace(/\//g, "_")}` : `cr_${title.slice(0, 15)}`,
          fingerprint: fp,
          title,
          summary: abstract,
          authors,
          year: exactDate,
          source: venueName ? `CrossRef · ${venueName.slice(0, 24)}` : "CrossRef (權威庫)",
          link,
          citations,
          is_open_access: Boolean(item.license?.some((l: any) => l.URL?.toLowerCase().includes("open") || l.URL?.toLowerCase().includes("creative"))),
          is_top_journal: false,
          venue_name: venueName,
        });
      }
    }
  } catch (err) {
    console.warn("CrossRef fetch skipped/failed:", err);
  }

  // 3. PubMed
  try {
    const pmSearchUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(query)}&retmax=5&retmode=json`;
    const searchRes = await fetch(pmSearchUrl, { signal: AbortSignal.timeout(6000) });
    if (searchRes.ok) {
      const searchData = await searchRes.json();
      const idList = searchData.esearchresult?.idlist || [];
      if (idList.length > 0) {
        const sumUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=${idList.join(",")}&retmode=json`;
        const sumRes = await fetch(sumUrl, { signal: AbortSignal.timeout(6000) });
        if (sumRes.ok) {
          const sumData = await sumRes.json();
          for (const pmid of idList) {
            const doc = sumData.result?.[pmid];
            if (!doc) continue;
            const title = doc.title || "";
            const authors = (doc.authors || []).map((a: any) => a.name).filter(Boolean);

            let pubDate = new Date().toISOString().slice(0, 10);
            if (doc.pubdate) {
              const dateMatch = doc.pubdate.match(/^(\d{4})(?:\s+([A-Za-z]+))?(?:\s+(\d{1,2}))?/);
              if (dateMatch) {
                const y = dateMatch[1];
                const monthNames: Record<string, string> = {
                  jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06",
                  jul: "07", aug: "08", sep: "09", oct: "10", nov: "11", dec: "12"
                };
                const mStr = (dateMatch[2] || "").toLowerCase().slice(0, 3);
                const m = monthNames[mStr] || "01";
                const d = dateMatch[3] ? String(dateMatch[3]).padStart(2, "0") : "01";
                pubDate = `${y}-${m}-${d}`;
              }
            }
            const journal = doc.source || "PubMed 生醫文獻";
            const fp = title.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 50);
            results.push({
              id: `pmid_${pmid}`,
              fingerprint: fp,
              title,
              summary: `本篇生醫臨床與基礎研究發表於 ${journal} (${pubDate})。探討主題聚焦於「${title}」。`,
              authors,
              year: pubDate,
              source: `PubMed (${journal.slice(0, 18)})`,
              link: `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`,
              citations: 0,
              is_open_access: false,
              is_top_journal: false,
              venue_name: journal,
            });
          }
        }
      }
    }
  } catch (err) {
    console.warn("PubMed fetch skipped/failed:", err);
  }

  // 4. arXiv
  try {
    const arxivUrl = `https://export.arxiv.org/api/query?search_query=all:${encodeURIComponent(query)}&start=0&max_results=6&sortBy=submittedDate&sortOrder=descending`;
    const res = await fetch(arxivUrl, { signal: AbortSignal.timeout(6000) });
    if (res.ok) {
      const xml = await res.text();
      const entries = xml.split("<entry>").slice(1);
      for (const entry of entries) {
        const titleMatch = entry.match(/<title>([^<]+)<\/title>/);
        const summaryMatch = entry.match(/<summary>([^<]+)<\/summary>/);
        const idMatch = entry.match(/<id>([^<]+)<\/id>/);
        const publishedMatch = entry.match(/<published>([^<]+)<\/published>/);
        const authorMatches = [...entry.matchAll(/<author>\s*<name>([^<]+)<\/name>/g)].map(m => m[1]);

        if (titleMatch && summaryMatch) {
          const title = titleMatch[1].replace(/\n/g, " ").trim();
          const summary = summaryMatch[1].replace(/\n/g, " ").trim();
          const rawId = idMatch ? idMatch[1].trim() : "";
          const aid = rawId.match(/(\d{4}\.\d{4,5})/)?.[1] || rawId;
          const exactPublishedDate = publishedMatch ? publishedMatch[1].slice(0, 10) : new Date().toISOString().slice(0, 10);
          const fp = title.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 50);

          results.push({
            id: aid || `arxiv_${Date.now()}`,
            fingerprint: fp,
            title,
            summary,
            authors: authorMatches,
            year: exactPublishedDate,
            source: "arXiv (開源預印本)",
            link: aid ? `https://arxiv.org/pdf/${aid}.pdf` : rawId,
            citations: 18,
            is_open_access: true,
            is_top_journal: false
          });
        }
      }
    }
  } catch (err) {
    console.warn("arXiv fetch skipped/failed:", err);
  }

  // 5. OpenAlex (免費、學術權威元數據：期刊/會議、引用數、領域)
  try {
    const oaUrl = `https://api.openalex.org/works?search=${encodeURIComponent(query)}&per_page=8&sort=cited_by_count:desc&select=id,title,abstract_inverted_index,authorships,publication_year,cited_by_count,primary_location,type,open_access`;
    const res = await fetch(oaUrl, {
      headers: { "User-Agent": "PaperFilterBot/3.0 (mailto:paperfilter-bot@example.com)" },
      signal: AbortSignal.timeout(6000)
    });
    if (res.ok) {
      const data = await res.json();
      for (const w of data.results || []) {
        const title = (w.title || "").trim();
        if (!title) continue;
        const inv = w.abstract_inverted_index;
        let abstract = "";
        if (inv) {
          const pos: [number, string][] = [];
          for (const [word, positions] of Object.entries(inv)) {
            for (const p of positions as number[]) pos.push([p, word]);
          }
          pos.sort((a, b) => a[0] - b[0]);
          abstract = pos.map(x => x[1]).join(" ");
        }
        if (!abstract) continue;
        const authors = (w.authorships || []).slice(0, 10).map((a: any) => a.author?.display_name || "").filter(Boolean);
        const loc = w.primary_location || {};
        const src = loc.source || {};
        const venueName = src.display_name || "";
        const isOa = Boolean(w.open_access?.is_oa);
        const oaUrlLink = w.open_access?.oa_url;
        const link = oaUrlLink || loc.landing_page_url || `https://api.openalex.org/works/${String(w.id || '').split('/').pop()}`;
        const year = String(w.publication_year || new Date().getFullYear());
        const citations = w.cited_by_count || 0;
        const fp = title.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 50);
        results.push({
          id: `oa_${String(w.id || '').split('/').pop()}`,
          fingerprint: fp,
          title,
          summary: abstract,
          authors,
          year,
          source: venueName ? `OpenAlex · ${venueName.slice(0, 24)}` : "OpenAlex (權威庫)",
          link,
          citations,
          is_open_access: isOa,
          is_top_journal: false,
          venue_name: venueName,
        });
      }
    }
  } catch (err) {
    console.warn("OpenAlex fetch skipped/failed:", err);
  }

  // Deduplicate by title fingerprint
  const uniqueMap = new Map<string, PaperItem>();
  for (const p of results) {
    if (!uniqueMap.has(p.fingerprint)) {
      uniqueMap.set(p.id, p);
    }
  }
  const uniqueList = Array.from(uniqueMap.values());

  // Rank according to mode, recency, author boost, user preference
  const currentYear = new Date().getFullYear();
  const followedAuthors = await getAuthors();
  const scored = uniqueList.map(p => {
    // 真實權威等級（取代虛假 is_top_journal）
    const vname = p.venue_name || p.source || "";
    const tier = p.tier || getVenueTier(vname) || null;
    const isPre = p.is_preprint !== undefined ? p.is_preprint : isPreprint(p.source || "");
    const cred = credibilityBadge(p.venue_name || "", p.source || "");
    const isTopTier = !isPre && (tier === "TOP" || tier === "CCF-A" || tier === "CCF-B" || tier === "Q1");

    let matchScore = 0;
    const titleLower = p.title.toLowerCase();
    const summaryLower = p.summary.toLowerCase();

    for (const w of words) {
      const wl = w.toLowerCase();
      if (titleLower.includes(wl)) matchScore += 30;
      else if (summaryLower.includes(wl)) matchScore += 12;
    }

    const yearNum = parseInt(p.year) || 2020;
    const diff = currentYear - yearNum;
    let recencyScore = 0;
    if (diff <= 1) recencyScore = 20;
    else if (diff <= 2) recencyScore = 10;
    else if (diff <= 4) recencyScore = 5;

    let modeScore = 0;
    if (mode === "top_tier") {
      modeScore = Math.min(Math.floor(p.citations / 3), 50) + (isTopTier ? 30 : 0);
    } else if (mode === "free_only") {
      modeScore = Math.min(Math.floor(p.citations / 10), 15) + (p.is_open_access ? 30 : -20);
    } else {
      modeScore = Math.min(Math.floor(p.citations / 5), 30) + (isTopTier ? 15 : 0) + (p.is_open_access ? 10 : 0);
    }

    let authorBonus = 0;
    for (const author of p.authors) {
      for (const target of followedAuthors) {
        if (target.toLowerCase() && author.toLowerCase().includes(target.toLowerCase())) {
          authorBonus += 50;
        }
      }
    }

    let prefScore = 0;
    for (const [w, weight] of Object.entries(userBias.positive)) {
      if (titleLower.includes(w) || summaryLower.includes(w)) prefScore += weight * 2;
    }
    for (const [w, weight] of Object.entries(userBias.negative)) {
      if (titleLower.includes(w) || summaryLower.includes(w)) prefScore -= weight * 3;
    }

    const totalScore = matchScore + recencyScore + modeScore + authorBonus + prefScore;
    return {
      ...p,
      score: totalScore,
      tier,
      is_preprint: isPre,
      is_top_journal: isTopTier,
      credibility_emoji: cred.emoji,
      credibility_label: cred.key,
    };
  });

  scored.sort((a, b) => (b.score || 0) - (a.score || 0));
  return scored;
}

// Generate BibTeX Helper
function generateBibTeX(paper: PaperItem): string {
  const cleanTitle = paper.title.replace(/[<>:"/\\|?*]/g, "").trim();
  const firstAuthor = paper.authors[0] ? paper.authors[0].split(" ").pop()?.toLowerCase() : "researcher";
  const shortTitle = cleanTitle.split(" ")[0]?.replace(/[^a-zA-Z0-9]/g, "").toLowerCase() || "paper";
  const citeKey = `${firstAuthor}${paper.year || "2024"}_${shortTitle}`;
  const authorField = paper.authors.length > 0 ? paper.authors.join(" and ") : "Unknown Authors";

  return `@article{${citeKey},
  title = {${cleanTitle}},
  author = {${authorField}},
  year = {${paper.year || new Date().getFullYear()}},
  journal = {${paper.source || "Academic Publication"}},
  url = {${paper.link}}
}`;
}

// ================= API Endpoints =================

// 1. User Profile & Telegram Sync
app.get("/api/auth/profile", async (req, res) => {
  try {
    const user = await buildProfile();
    // 綁定後讓網頁採用 Telegram 的 user_id，確保論文庫雙向同步對得上同一把鍵
    if (user.is_telegram_linked && user.telegram_id && user.telegram_id !== currentUserId()) {
      res.cookie("uid", String(user.telegram_id), { httpOnly: true, sameSite: "lax", maxAge: 30 * 86400 * 1000 });
    }
    const uname = getCookie(req, "uname");
    if (uname) {
      user.username = uname;
      user.telegram_handle = user.is_telegram_linked
        ? (uname.startsWith("@") ? uname : `@${uname}`)
        : "";
    }
    const categories = await getCategories();
    const authors = await getAuthors();
    const library = await loadLibrary();
    res.json({
      success: true,
      user,
      categories,
      followed_authors: authors,
      library_count: library.length,
      history_count: user.history_count || 0
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "取得個人檔案失敗" });
  }
});

app.post("/api/auth/generate-code", async (req, res) => {
  const webUid = getUid(req);
  if (!webUid) return res.status(401).json({ success: false, error: "請先開啟網頁端" });
  try {
    const code = await createBindCode(webUid);
    res.json({ success: true, sync_code: code });
  } catch (e: any) {
    res.status(500).json({ success: false, error: e.message || "產生驗證碼失敗" });
  }
});

app.post("/api/auth/bind-telegram", async (req, res) => {
  const webUid = getUid(req);
  const link = webUid ? await getLinkByWeb(webUid) : null;
  const user = await buildProfile();
  // 綁定後讓網頁採用 Telegram 的 user_id，確保論文庫雙向同步對得上同一把鍵
  if (link && link.telegram_user_id !== webUid) {
    await migrateWebToTelegram(webUid, link.telegram_user_id);
    res.cookie("uid", String(link.telegram_user_id), { httpOnly: true, sameSite: "lax", maxAge: 30 * 86400 * 1000 });
  }
  res.json({
    success: true,
    linked: !!link,
    message: link
      ? "🎉 Telegram 帳號已成功綁定！所有歷史紀錄與文獻庫將雙向即時同步。"
      : "尚未綁定，請在 Telegram 輸入 /bind 你的驗證碼。",
    user: link ? { ...user, telegram_id: link.telegram_user_id } : user,
  });
});

// Telegram Login Widget 驗證與登入
app.post("/api/auth/telegram-login", async (req, res) => {
  try {
    const data = req.body;
    if (!verifyTelegramAuth(data)) {
      return res.status(401).json({ success: false, error: "Telegram 登入驗證失敗" });
    }
    const id = Number(data.id);
    const uname = data.username || data.first_name || `user${id}`;
    await setUserContext(id, async () => { await ensureUser(id); });
    res.cookie("uid", String(id), { httpOnly: true, sameSite: "lax", maxAge: 30 * 86400 * 1000 });
    res.cookie("uname", uname, { httpOnly: false, sameSite: "lax", maxAge: 30 * 86400 * 1000 });
    res.json({ success: true });
  } catch (e: any) {
    res.status(500).json({ success: false, error: e.message || "登入失敗" });
  }
});

app.get("/api/auth/config", (req, res) => {
  res.json({ success: true, bot_username: process.env.TELEGRAM_BOT_USERNAME || "PaperFilterBot" });
});

app.post("/api/auth/logout", (req, res) => {
  res.clearCookie("uid");
  res.clearCookie("uname");
  res.json({ success: true });
});

app.post("/api/auth/upgrade-tier", async (_req, res) => {
  res.status(402).json({
    success: false,
    error: "Payment not enabled yet. Redeem a beta code with /api/auth/redeem.",
  });
});

app.post("/api/auth/redeem", async (req, res) => {
  try {
    const { code } = req.body || {};
    const result = await redeemPromoCode(String(code || ""));
    if (!result.ok) {
      return res.status(400).json({ success: false, error: result.errorKey || "promo_invalid" });
    }
    res.json({ success: true, expiresAt: result.expiresAt, user: await buildProfile() });
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message || "兌換失敗" });
  }
});

app.post("/api/lab-inquiry", async (_req, res) => {
  res.status(410).json({ success: false, error: "Gone" });
});

app.post("/api/auth/update-mode", async (req, res) => {
  const { mode } = req.body;
  if (mode) await setFilterMode(mode);
  res.json({ success: true, mode: (await buildProfile()).filter_mode });
});

app.post("/api/user/language", async (req, res) => {
  const { lang } = req.body;
  if (lang) await setUserLang(lang);
  res.json({ success: true, lang: (await buildProfile()).user_lang });
});

// 2. History & Analytics
app.get("/api/history", async (req, res) => {
  const user = await buildProfile();
  const rows = await listActivity(80);
  res.json({
    success: true,
    history: rows.map(activityToHistoryItem),
    stats: {
      read: user.total_read_count,
      archived: user.total_archived_count,
      skipped: user.total_skipped_count,
      deep_read: user.total_deep_read_count
    }
  });
});

app.get("/api/analytics/charts", async (req, res) => {
  const library = await loadLibrary();

  const categoryCounts: Record<string, number> = {};
  for (const p of library) {
    const c = p.category || "Uncategorized";
    categoryCounts[c] = (categoryCounts[c] || 0) + 1;
  }

  const hist = (await listActivity(400)).map(activityToHistoryItem);
  const now = new Date();
  const readingTrend = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 86400000);
    const dayKey = d.toISOString().slice(0, 10);
    const dayLabel = `${d.getMonth() + 1}/${d.getDate()}`;
    readingTrend.push({
      date: dayLabel,
      searches: hist.filter(h => h.action === "search" && String(h.timestamp).slice(0, 10) === dayKey).length,
      archived: hist.filter(h => h.action === "archive" && String(h.timestamp).slice(0, 10) === dayKey).length,
      deep_reads: hist.filter(h => h.action === "deep_read" && String(h.timestamp).slice(0, 10) === dayKey).length
    });
  }

  res.json({
    success: true,
    category_distribution: Object.entries(categoryCounts).map(([name, value]) => ({ name, value })),
    reading_trend: readingTrend,
    top_sources: []
  });
});

// 3. Search endpoint
app.post("/api/search", async (req, res) => {
  try {
    const { query, mode } = req.body;
    if (!query) return res.status(400).json({ error: "請輸入搜尋關鍵字" });
    if (!(await enforceQuota(res, "search"))) return;

    const profile = await buildProfile();
    const searchMode = mode || profile.filter_mode;

    const papers = await fetchAcademicPapers(query, searchMode);
    await incrementUsage("search");
    await logActivity({
      action: "search",
      paper_title: `搜尋主題：${query}`,
      details: `以 [${searchMode}] 策略跨 5 大庫進行檢索`,
    });

    res.json({ success: true, count: papers.length, papers });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "搜尋發生異常" });
  }
});

// 4. Deep Analysis
app.post("/api/deep", async (req, res) => {
  try {
    const { title, summary, authors = [], year = "2024", link = "", source = "" } = req.body;
    if (!title) return res.status(400).json({ error: "缺少論文標題" });
    if (!(await enforceQuota(res, "deep"))) return;

    const gemini = getGeminiClient();
    let deepReport = "";

    if (gemini) {
      try {
        const response = await gemini.models.generateContent({
          model: req.body?.model,
          contents: `你是一位頂級學術期刊審稿專家與科研導讀專家。請針對以下學術論文進行深度 4 大維度導讀。

【嚴格誠信規則】：
- 依據標題與摘要，禁止捏造數字。
- 只能使用下方【論文標題】與【論文摘要全文】中實際出現的資訊，嚴禁杜撰作者姓名、具體數據、數據集、指標或結論。
- 若摘要未提及具體量化結果，請明確寫「未提供具體量化數據」，不要編造數字或 SOTA 提升幅度。
- 清楚區分「論文作者聲稱的內容」與「你自身的領域背景知識」。

【論文標題】：${title}
【作者陣容】：${authors.join(", ") || "未提供"}
【發表年份/來源】：${year} 年 / ${source || "學術資料庫"}
【論文摘要全文】：
${summary || "（無摘要提供，請根據標題與領域學術背景深入解構）"}

請用嚴謹、清晰且富有啟發性的繁體中文，精準依照以下 4 個結構標題輸出（請務必保留 Emoji 與【】符號）：

🎯 【研究痛點與動機】
（深入剖析該論文要解決的本質難題、現有方法的具體缺陷或理論盲點）

⚙️ 【核心方法與技術創新】
（條列式拆解論文提出的模型架構、關鍵演算法、數學原理或實驗設計）

📊 【關鍵發現與突破數據】
（列出論文的主要實驗結果、對比基準 SOTA 的提升幅度、關鍵結論）

⚠️ 【研究限制與未來方向】
（指出該方法的適用邊界、未解瓶頸，以及給後續研究者的實質啟發）`,
        });
        deepReport = response.text || "";
      } catch (e: any) {
        if (e?.code === "MODEL_TIER") return res.status(403).json({ success: false, error: e.message });
        if (e?.code === "NO_KEY") return res.status(502).json({ success: false, error: "🚫 AI 服務尚未設定 API Key，請聯絡管理員。" });
        console.warn("OpenAI API call error:", e);
      }
    }

    if (!deepReport) {
      return res.status(502).json({ success: false, error: "🚫 AI 服務暫時無法使用，可能是 API 額度用盡或服務異常。請稍後再試，或檢查 OPENAI_API_KEY 設定。" });
    }

    const bibtex = generateBibTeX({
      id: "tmp",
      fingerprint: "tmp",
      title,
      summary,
      authors,
      year,
      link,
      source,
      citations: 0,
      is_open_access: true,
      is_top_journal: true
    });

    await incrementUsage("deep");
    await logActivity({
      action: "deep_read",
      paper_title: title,
      details: "完成 AI 4 大維度深度導讀與 BibTeX 提取",
    });

    res.json({
      success: true,
      deep_report: `【資料來源：標題與摘要】依據標題與摘要，禁止捏造數字。\n\n${deepReport}`,
      bibtex,
      source: "abstract",
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "生成深度導讀失敗" });
  }
});

// 5. Literature Review & Gap Analysis
app.post("/api/review", async (req, res) => {
  try {
    if (!(await enforceQuota(res, "litreview"))) return;
    const papers: PaperItem[] = req.body.papers || (await loadLibrary());
    if (!papers || papers.length === 0) {
      return res.status(400).json({ error: "尚未收藏任何論文可供生成文獻綜述" });
    }

    const papersText = papers.slice(0, 15).map((p, i) => {
      const auth = p.authors.slice(0, 3).join(", ") || "Unknown";
      return `${i + 1}. 《${p.title}》\n   作者: ${auth} (${p.year})\n   摘要: ${p.summary.slice(0, 250)}`;
    }).join("\n\n");

    const gemini = getGeminiClient();
    let reviewText = "";

    if (gemini) {
      try {
        const response = await gemini.models.generateContent({
          model: req.body?.model,
          contents: `以下是用戶收藏的 ${papers.length} 篇學術論文，請撰寫一份結構完整的學術文獻綜述（繁體中文）：
${papersText}

請按以下結構輸出：
1. **研究背景與主題概述**（2-3句）
2. **主要研究方向與發現**（逐條列出各篇論文的核心貢獻）
3. **研究方法比較**
4. **共同結論與趨勢**
5. **研究缺口與未來展望**

請保持嚴謹學術風格，引用論文時使用（作者, 年份）格式。`
        });
        reviewText = response.text || "";
      } catch (e: any) {
        if (e?.code === "MODEL_TIER") return res.status(403).json({ success: false, error: e.message });
        if (e?.code === "NO_KEY") return res.status(502).json({ success: false, error: "🚫 AI 服務尚未設定 API Key，請聯絡管理員。" });
        console.warn("OpenAI lit review error:", e);
      }
    }

    if (!reviewText) {
      return res.status(502).json({ success: false, error: "🚫 AI 服務暫時無法使用，可能是 API 額度用盡或服務異常。請稍後再試。" });
    }

    await incrementUsage("litreview");
    await logActivity({ action: "litreview", paper_title: "文獻綜述", details: `${papers.length} 篇` });

    res.json({ success: true, review: reviewText, paper_count: papers.length });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "文獻綜述生成失敗" });
  }
});

app.post("/api/gap", async (req, res) => {
  try {
    if (!(await enforceQuota(res, "gap_analysis"))) return;
    const papers: PaperItem[] = req.body.papers || (await loadLibrary());
    if (!papers || papers.length === 0) {
      return res.status(400).json({ error: "尚未收藏任何論文可供分析研究缺口" });
    }

    const papersText = papers.slice(0, 12).map((p, i) => `${i + 1}. 《${p.title}》 (${p.year})\n   摘要: ${p.summary.slice(0, 200)}`).join("\n\n");
    const gemini = getGeminiClient();
    let gapText = "";

    if (gemini) {
      try {
        const response = await gemini.models.generateContent({
          model: req.body?.model,
          contents: `以下是 ${papers.length} 篇學術論文，請深入分析這些研究中尚未解決的研究缺口（繁體中文）：
${papersText}

請輸出：
1. **現有研究涵蓋範圍**
2. **主要研究缺口**（至少列出 5 個具體缺口，每個附簡短說明）
3. **最具潛力的研究方向建議**（3-5 個）
4. **方法論層面的不足**`
        });
        gapText = response.text || "";
      } catch (e: any) {
        if (e?.code === "MODEL_TIER") return res.status(403).json({ success: false, error: e.message });
        if (e?.code === "NO_KEY") return res.status(502).json({ success: false, error: "🚫 AI 服務尚未設定 API Key，請聯絡管理員。" });
        console.warn("OpenAI gap error:", e);
      }
    }

    if (!gapText) {
      return res.status(502).json({ success: false, error: "🚫 AI 服務暫時無法使用，可能是 API 額度用盡或服務異常。請稍後再試。" });
    }

    await incrementUsage("gap_analysis");
    await logActivity({ action: "gap_analysis", paper_title: "研究缺口分析", details: `${papers.length} 篇` });

    res.json({ success: true, gap_analysis: gapText });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "研究缺口分析失敗" });
  }
});

// 6. Pro: Chat with Library (RAG over user library)
app.post("/api/pro/chat-library", async (req, res) => {
  try {
    if (!(await enforceQuota(res, "chat"))) return;
    const { question, papers = await loadLibrary() } = req.body;
    if (!question) return res.status(400).json({ error: "請輸入問答問題" });

    const libraryContext = papers.map((p: PaperItem, i: number) => {
      return `[文獻 ${i + 1}] 《${p.title}》 (${p.authors.slice(0, 2).join(", ")}, ${p.year})
分類: ${p.category}
摘要: ${p.summary}
筆記: ${p.user_notes || "無"}
---`;
    }).join("\n");

    const gemini = getGeminiClient();
    let reply = "";
    const citedPapers: string[] = [];

    if (gemini) {
      try {
        const response = await gemini.models.generateContent({
          model: req.body?.model,
          contents: `你是一位頂級學術研究助理。以下是用戶個人論文總部收藏的文獻知識庫：

${libraryContext}

用戶提問：
${question}

請根據上述收藏的文獻內容進行深度解答（繁體中文）。
在論述過程中，請精確標註引用來源（例如：引用自《Attention Is All You Need》或（Vaswani et al., 2017））。如果知識庫不足以完全回答，請基於學術常識進行延伸並註明。`
        });
        reply = response.text || "";
      } catch (e: any) {
        if (e?.code === "MODEL_TIER") return res.status(403).json({ success: false, error: e.message });
        if (e?.code === "NO_KEY") return res.status(502).json({ success: false, error: "🚫 AI 服務尚未設定 API Key，請聯絡管理員。" });
        console.warn("Chat library error:", e);
      }
    }

    if (!reply) {
      return res.status(502).json({ success: false, error: "🚫 AI 服務暫時無法使用，可能是 API 額度用盡或服務異常。請稍後再試。" });
    }

    for (const p of papers) {
      if (reply.includes(p.title) || (p.authors[0] && reply.includes(p.authors[0]))) {
        citedPapers.push(p.title);
      }
    }
    if (citedPapers.length === 0 && papers.length > 0) {
      citedPapers.push(papers[0].title);
    }

    await incrementUsage("chat");
    await logActivity({ action: "chat", paper_title: String(question).slice(0, 120) });

    res.json({
      success: true,
      answer: reply,
      cited_papers: citedPapers
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "知識庫問答失敗" });
  }
});

// 7. Pro: Multi-Paper Matrix Comparison
app.post("/api/pro/matrix-compare", async (req, res) => {
  try {
    if (!(await enforceQuota(res, "litreview"))) return;
    const papers: PaperItem[] = req.body.papers || (await loadLibrary()).slice(0, 4);
    if (!papers || papers.length < 2) {
      return res.status(400).json({ error: "請至少選擇 2 篇論文以進行橫向矩陣對比" });
    }

    const gemini = getGeminiClient();
    let matrixData = [];

    if (gemini) {
      try {
        const response = await gemini.models.generateContent({
          model: req.body?.model,
          contents: `請對以下 ${papers.length} 篇論文進行橫向結構化矩陣對比，以 JSON 陣列格式輸出：
${papers.map((p, i) => `${i + 1}. 標題: ${p.title}\n   摘要: ${p.summary}`).join("\n")}

請輸出嚴格的 JSON 格式（無多餘文字），每個物件包含欄位：
- title: 論文標題
- year: 年份
- authors: 主要作者（簡稱）
- pain_point: 研究痛點（20字內）
- core_method: 核心技術/演算法（20字內）
- key_metric: 關鍵突破指標（20字內）
- limitations: 局限性/缺點（20字內）`
        });
        const cleaned = (response.text || "").replace(/```json/g, "").replace(/```/g, "").trim();
        matrixData = JSON.parse(cleaned);
      } catch (e: any) {
        if (e?.code === "MODEL_TIER") return res.status(403).json({ success: false, error: e.message });
        if (e?.code === "NO_KEY") return res.status(502).json({ success: false, error: "🚫 AI 服務尚未設定 API Key，請聯絡管理員。" });
        console.warn("Matrix comparison JSON parse error:", e);
      }
    }

    if (!matrixData || matrixData.length === 0) {
      return res.status(502).json({ success: false, error: "🚫 AI 服務暫時無法使用，可能是 API 額度用盡或服務異常。請稍後再試。" });
    }

    await incrementUsage("litreview");
    await logActivity({ action: "litreview", paper_title: "矩陣對比", details: `${papers.length} 篇` });

    res.json({ success: true, matrix: matrixData });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "生成對比矩陣失敗" });
  }
});

// 8. Digest Schedule
app.get("/api/digest/settings", (_req, res) => {
  res.status(501).json({ success: false, error: "Daily Telegram digest is not live yet" });
});

app.post("/api/digest/settings", (_req, res) => {
  res.status(501).json({ success: false, error: "Daily Telegram digest is not live yet" });
});

// AI 模型清單（全部使用 GPT-4o-mini，統一低成本）
app.get("/api/ai/models", async (req, res) => {
  try {
    const profile = await getProfile();
    const models = [
      { id: "gpt-4o-mini", name: "GPT-4o-mini", required_tier: "free", unlocked: true }
    ];
    res.json({
      success: true,
      models,
      default: "gpt-4o-mini",
      user_tier: profile.tier,
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 9. Library CRUD & Notes
app.get("/api/library", async (req, res) => {
  try {
    const library = await loadLibrary();
    const categories = await getCategories();
    const authors = await getAuthors();
    const profile = await buildProfile();
    res.json({
      success: true,
      library,
      categories,
      followed_authors: authors,
      mode: profile.filter_mode,
      lang: profile.user_lang,
      bias: userBias
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.post("/api/library/add", async (req, res) => {
  try {
    const paper: PaperItem = req.body;
    if (!paper || !paper.title) return res.status(400).json({ error: "論文資料不完整" });

    const bibtex = paper.bibtex || generateBibTeX(paper);
    const item: PaperItem = {
      ...paper,
      bibtex,
      category: paper.category || "AI",
      user_notes: paper.user_notes || "",
      tags: paper.tags || ["saved"],
      is_starred: paper.is_starred ?? false,
      added_at: new Date().toISOString()
    };

    await addPaper(item);
    await logActivity({
      action: "archive",
      paper_id: item.id,
      paper_title: item.title,
      details: `歸檔至 [${item.category}]`,
    });

    const updated = (await loadLibrary()).find(p => p.id === item.id) || item;
    res.json({ success: true, message: "論文已成功雙軌歸檔至大總部與 Google Drive！", paper: updated });
  } catch (err: any) {
    if (err?.code === "LIBRARY_FULL") {
      return res.status(403).json({ success: false, error: err.message, code: "LIBRARY_FULL" });
    }
    res.status(500).json({ error: err.message });
  }
});

app.post("/api/library/update-paper", async (req, res) => {
  try {
    const { id, user_notes, tags, is_starred, category } = req.body;
    await updatePaper(id, {
      ...(user_notes !== undefined ? { user_notes } : {}),
      ...(tags !== undefined ? { tags } : {}),
      ...(is_starred !== undefined ? { is_starred } : {}),
      ...(category !== undefined ? { category } : {}),
    });
    const lib = await loadLibrary();
    const updated = lib.find(p => p.id === id || p.fingerprint === id);
    if (updated) return res.json({ success: true, paper: updated });
    res.status(404).json({ error: "找不到該論文" });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.delete("/api/library/:id", async (req, res) => {
  try {
    const { id } = req.params;
    await removePaper(id);
    res.json({ success: true, message: "已自大總部文獻庫移除" });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 10. Categories & Authors
app.post("/api/categories", async (req, res) => {
  try {
    const { action, name, oldName, newName } = req.body;
    if (action === "add" && name) {
      const cats = await getCategories();
      const clean = String(name).trim();
      if (clean && !cats.includes(clean)) {
        const profile = await getProfile();
        const limit = TIER_DEFS[normalizeTier(profile.tier)].category_limit;
        if (!isUnlimited(limit) && cats.length >= limit) {
          return res.status(403).json({ success: false, error: `分類已達方案上限 (${cats.length}/${limit})` });
        }
      }
      await addCategory(name);
    }
    else if (action === "rename" && oldName && newName) await renameCategory(oldName, newName);
    else if (action === "delete" && name) await deleteCategory(name);
    res.json({ success: true, categories: await getCategories() });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.post("/api/authors", async (req, res) => {
  try {
    const { action, name } = req.body;
    if (action === "add" && name) {
      const authors = await getAuthors();
      const clean = String(name).trim();
      if (clean && !authors.includes(clean)) {
        const profile = await getProfile();
        const limit = TIER_DEFS[normalizeTier(profile.tier)].follow_limit;
        if (!isUnlimited(limit) && authors.length >= limit) {
          return res.status(403).json({ success: false, error: `追蹤學者已達方案上限 (${authors.length}/${limit})` });
        }
      }
      await addAuthor(name);
    }
    else if (action === "remove" && name) await removeAuthor(name);
    res.json({ success: true, followed_authors: await getAuthors() });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 11. Export endpoint
app.post("/api/export", async (req, res) => {
  try {
    if (!(await enforceQuota(res, "export"))) return;
    const { format = "BibTeX", papers = await loadLibrary() } = req.body;
    if (!papers || papers.length === 0) {
      return res.status(400).json({ error: "沒有論文可供匯出" });
    }

    let content = "";
    if (format === "BibTeX") {
      content = papers.map((p: PaperItem) => p.bibtex || generateBibTeX(p)).join("\n\n");
    } else if (format === "RIS") {
      content = papers.map((p: PaperItem) => {
        const lines = [
          "TY  - JOUR",
          `TI  - ${p.title}`,
          ...(p.authors || []).map((a: string) => `AU  - ${a}`),
          `PY  - ${p.year}`,
          `JO  - ${p.source}`,
          `UR  - ${p.link}`,
          p.summary ? `AB  - ${p.summary.slice(0, 500)}` : "",
          "ER  - \n"
        ].filter(Boolean);
        return lines.join("\n");
      }).join("\n");
    } else if (format === "CSV") {
      const header = "Title,Authors,Year,Source,Link,Category,Notes,Abstract";
      const rows = papers.map((p: PaperItem) => {
        const clean = (s: string) => `"${(s || '').replace(/"/g, '""')}"`;
        return [clean(p.title), clean(p.authors.join("; ")), clean(p.year), clean(p.source), clean(p.link), clean(p.category || ""), clean(p.user_notes || ""), clean(p.summary.slice(0, 300))].join(",");
      });
      content = [header, ...rows].join("\n");
    }

    await incrementUsage("export");
    await logActivity({ action: "export", paper_title: format, details: `${papers.length} 篇` });

    res.json({ success: true, format, content, count: papers.length });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 12. Trend Analysis
app.post("/api/trend", async (req, res) => {
  try {
    if (!(await enforceQuota(res, "search"))) return;
    const { topic = "machine learning" } = req.body;
    const papers = await fetchAcademicPapers(topic, "smart");

    const yearCounts: Record<string, number> = {};
    for (const p of papers) {
      const y = p.year || "2024";
      yearCounts[y] = (yearCounts[y] || 0) + 1;
    }

    const gemini = getGeminiClient();
    let aiAnalysis = "";

    if (gemini) {
      try {
        const response = await gemini.models.generateContent({
          model: req.body?.model,
          contents: `以下是關於「${topic}」的近期學術論文：
${papers.slice(0, 10).map(p => `- ${p.title} (${p.year})`).join("\n")}

請用繁體中文分析這個領域的研究趨勢，包含：
1. 主流研究方向
2. 新興技術/方法
3. 研究熱度變化
4. 預測未來 2-3 年的發展方向

請精簡有力，控制在 300 字以內。`
        });
        aiAnalysis = response.text || "";
      } catch (e: any) {
        if (e?.code === "MODEL_TIER") return res.status(403).json({ success: false, error: e.message });
        if (e?.code === "NO_KEY") return res.status(502).json({ success: false, error: "🚫 AI 服務尚未設定 API Key，請聯絡管理員。" });
        console.warn("OpenAI trend error:", e);
      }
    }

    if (!aiAnalysis) {
      return res.status(502).json({ success: false, error: "🚫 AI 服務暫時無法使用，可能是 API 額度用盡或服務異常。請稍後再試。" });
    }

    await incrementUsage("search");
    await logActivity({ action: "search", paper_title: `趨勢：${topic}` });

    res.json({
      success: true,
      topic,
      total_papers_found: papers.length,
      year_distribution: yearCounts,
      recent_publications: papers.slice(0, 5).map(p => p.title),
      ai_analysis: aiAnalysis
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "趨勢分析失敗" });
  }
});

type SimLang = "en" | "zh_hant" | "zh_hans" | "ja";
function normSimLang(l?: string): SimLang {
  const s = String(l || "").toLowerCase().replace(/-/g, "_");
  if (s === "zh_hant" || s === "zh_tw") return "zh_hant";
  if (s === "zh_hans" || s === "zh_cn" || s === "zh") return "zh_hans";
  if (s === "ja" || s === "jp") return "ja";
  return "en";
}
function parseLangArg(arg: string): SimLang | null {
  const s = arg.trim().toLowerCase().replace(/-/g, "_");
  if (!s) return null;
  if (["en", "eng", "english"].includes(s)) return "en";
  if (["ja", "jp", "japanese", "日本語"].includes(s)) return "ja";
  if (["zh_hans", "zh_cn", "cn", "simplified"].includes(s) || s.includes("简")) return "zh_hans";
  if (["zh_hant", "zh_tw", "tw", "traditional"].includes(s) || s.includes("繁")) return "zh_hant";
  return null;
}
const SIM: Record<SimLang, Record<string, string>> = {
  en: {
    start: "👋 Hi <b>{name}</b>, welcome to <b>PaperFilterBot HQ</b>!\n\n🔬 <b>What only PaperFilterBot does</b>:\n• Cross-search <b>5</b> scholarly repositories (arXiv, PubMed, Semantic Scholar, CrossRef, OpenAlex)\n• 💡 4-dimension AI Deep Reading (Motivation, Method, Finding, Limits)\n• 🔄 Telegram ↔ Web HQ two-way sync — same library on phone and desktop\n• 👁 Seen vs Skip dual filter: ranking learns what you actually want (most tools only save or delete)\n• ☁️ Google Drive dual archive with auto-maintained <code>references.bib</code>\n• 👤 Follow a scholar — their new papers get +50 ranking weight in every search\n\n👇 Choose a shortcut below or send <b>keywords</b> directly to search:",
    help: "📖 <b>PaperFilterBot Command Suite</b>\n\n🔍 <b>Search</b>: Send keywords directly (e.g. LLM Agent)\n💬 <b>/chat</b> - Toggle cross-paper Q&A\n📚 <b>/my</b> - View library, folders & Drive\n🔗 <b>/bind</b> - 6-digit sync code to link Telegram\n💎 <b>/pro</b> - Plans & upgrade info\n📂 <b>/following</b> · ➕ <code>/follow Name</code> · ➖ <code>/unfollow Name</code>\n📑 <code>/review</code> · 🔍 <code>/gap</code> · 📈 <code>/trend Field</code>\n⚙️ <code>/mode</code> · 🌐 <code>/lang</code>\n📱 <code>/web</code> - Open the live Telegram bot (this is the web simulator)\n\nSlash commands are never treated as search.",
    bind: "🔗 <b>Bind web HQ to Telegram</b>\n\nYour sync code: <code>{code}</code>\n\nOpen the website, click <b>Bind TG</b>, and enter this code.",
    pro_head: "📊 <b>PaperFilterBot plans</b>\n\n👤 Current plan: <b>{tier}</b>\n\n",
    pro_foot: "\n\n<i>Pricing is not live yet. Testers: use a /redeem code on the real Telegram bot for 7-day full access. Lab is sales-assisted, not instant unlock.</i>",
    lang_pick: "🌐 <b>Interface language</b>\n\nCurrent: <b>{current}</b>\n\nTap a button or send <code>/lang en</code>, <code>/lang ja</code>, <code>/lang zh_hant</code>, <code>/lang zh_hans</code>.",
    lang_ok: "✅ Language set to <b>{current}</b>.",
    mode_pick: "⚙️ <b>Filter mode</b>\n\nCurrent: <b>{current}</b>\n\nSend <code>/mode smart</code>, <code>/mode top_tier</code>, or <code>/mode free_only</code>.",
    mode_ok: "✅ Filter mode set to <b>{mode}</b>.",
    following: "📋 <b>Scholars you follow</b>\n\n{list}\n\n<i><code>/unfollow Name</code> to remove</i>",
    following_empty: "(none yet)",
    follow_ok: "🌟 Now following <code>{name}</code> (+50 ranking weight).",
    follow_need: "Usage: <code>/follow Yann LeCun</code>",
    unfollow_ok: "✅ Unfollowed <code>{name}</code>.",
    unfollow_miss: "⚠️ <code>{name}</code> was not on your list.",
    folders: "📁 <b>Your folders</b>\n\n{list}",
    folders_empty: "(no folders yet — try <code>add folder Quantum AI</code>)",
    folder_add: "✅ Folder created: <b>{name}</b>",
    folder_rename: "✅ Renamed <b>{old}</b> → <b>{new}</b>",
    folder_del: "✅ Removed folder: <b>{name}</b>",
    unknown: "❓ Unknown command <code>{cmd}</code>. Send <code>/help</code> for the list. Keywords without / still search papers.",
    no_papers: "😅 No papers found for [{q}]. Try another keyword.",
    ai_label: "AI briefing:",
    pdf_label: "Read full paper / PDF",
    and_others: " and {n} others",
    btn_deep: "💡 Deep Reading",
    btn_seen: "👀 Seen",
    btn_skip: "👎 Not Interested",
    btn_archive: "☁️ Cloud Archive",
    review_hint: "📑 Literature review runs on the real bot and in Pro Suite → Writer / RAG. This simulator does not treat /review as a search.",
    gap_hint: "🔍 Gap analysis runs in Pro Suite → Research Gap Scanner. /gap is not a search keyword.",
    trend_need: "Usage: <code>/trend quantum computing</code>",
    unlimited: "unlimited",
    pro_search: "{n}/day search",
    pro_deep: "{n}/day deep read",
    pro_combo: "{n}/day /review + /gap + /chat",
    pro_drive: "Drive: {n}/mo",
    pro_report: "AI Report: {n}/week",
    pro_report_unlim: "AI Report: unlimited",
    welcome: "👋 Hi <b>{name}</b>, welcome to <b>PaperFilterBot HQ</b>!\n\n🔬 <b>What only PaperFilterBot does</b>:\n• Cross-search <b>5</b> scholarly repositories (arXiv, PubMed, Semantic Scholar, CrossRef, OpenAlex)\n• 💡 4-dimension AI Deep Reading (Motivation, Method, Finding, Limits)\n• 🔄 Telegram ↔ Web HQ two-way sync — same library on phone and desktop\n• 👁 Seen vs Skip dual filter: ranking learns what you actually want (most tools only save or delete)\n• ☁️ Google Drive dual archive with auto-maintained <code>references.bib</code>\n• 👤 Follow a scholar — their new papers get +50 ranking weight in every search\n\n👇 Choose a shortcut below or send <b>keywords</b> directly to search:",
    btn_hot_transformer: "🔍 Hot: Transformer",
    btn_hot_crispr: "🧬 Hot: CRISPR",
    btn_bind: "🔗 Bind Telegram",
    btn_view_pro: "👑 View Pro Features",
    btn_full_help: "📖 Full Command Guide",
    btn_open_tg: "📱 Open Telegram bot",
    btn_oa: "🟢 Open Access",
    btn_doi: "🔗 Official DOI",
    web_tg: "📱 You are already on Web HQ.\n\nOn the real Telegram bot this button opens the website. Here it is reversed — open the live bot:\n\nhttps://t.me/{bot}",
    mode_top: "🏆 Top-tier",
    mode_smart: "⚡ Smart Balanced",
    mode_free: "🟢 Open Access only",
  },
  zh_hant: {
    start: "👋 嗨 <b>{name}</b>，歡迎使用 <b>PaperFilterBot 科研大總部</b>！\n\n🔬 <b>只有這裡才有的科研特權</b>：\n• 5 大學術庫交叉檢索（arXiv / PubMed / Semantic Scholar / CrossRef / OpenAlex）\n• 💡 4 維 AI 深度導讀（動機、方法、發現、限制）\n• 🔄 Telegram ↔ 網頁大總部雙向同步：手機與電腦同一文獻庫\n• 👁 看過 / 沒興趣雙軌學習：排序會記住你真正要的論文（多數工具只有收藏或刪除）\n• ☁️ Google Drive 雙軌歸檔，資料夾自動維護 <code>references.bib</code>\n• 👤 追蹤學者：其新作在每次搜尋中權重 +50\n\n👇 請選擇下方快捷功能，或直接在聊天室發送<b>論文關鍵字</b>進行檢索：",
    help: "📖 <b>PaperFilterBot 全指令導覽</b>\n\n🔍 <b>論文檢索</b>：直接發送關鍵字（例如：LLM Agent）\n💬 <b>/chat</b> - 跨文獻問答\n📚 <b>/my</b> - 文獻庫、資料夾與 Drive\n🔗 <b>/bind</b> - 產生同步碼以綁定 Telegram\n💎 <b>/pro</b> - 方案比較\n📂 <b>/following</b> · ➕ <code>/follow 學者</code> · ➖ <code>/unfollow 學者</code>\n📑 <code>/review</code> · 🔍 <code>/gap</code> · 📈 <code>/trend 領域</code>\n⚙️ <code>/mode</code> · 🌐 <code>/lang</code>\n📱 <code>/web</code> - 開啟真實 Telegram 機器人（此處為網頁模擬器）\n\n以 / 開頭的指令不會被當成搜尋。",
    bind: "🔗 <b>綁定網頁大總部</b>\n\n同步碼：<code>{code}</code>\n\n請在網頁點擊「綁定 TG」後輸入此代碼。",
    pro_head: "📊 <b>方案比較</b>\n\n👤 目前方案：<b>{tier}</b>\n\n",
    pro_foot: "\n\n<i>定價尚未上線。測試員請在真實 Telegram bot 用 /redeem 兌換 7 天全功能。Lab 為業務洽詢，不會即時解鎖。</i>",
    lang_pick: "🌐 <b>介面語言</b>\n\n目前：<b>{current}</b>\n\n請點按鈕，或傳送 <code>/lang en</code> 等。",
    lang_ok: "✅ 語言已切換為 <b>{current}</b>。",
    mode_pick: "⚙️ <b>過濾模式</b>\n\n目前：<b>{current}</b>\n\n傳送 <code>/mode smart</code>、<code>/mode top_tier</code> 或 <code>/mode free_only</code>。",
    mode_ok: "✅ 過濾模式已設為 <b>{mode}</b>。",
    following: "📋 <b>追蹤中的學者</b>\n\n{list}\n\n<i><code>/unfollow 名字</code> 可取消</i>",
    following_empty: "（尚無）",
    follow_ok: "🌟 已追蹤 <code>{name}</code>（+50 權重）。",
    follow_need: "用法：<code>/follow Yann LeCun</code>",
    unfollow_ok: "✅ 已取消追蹤 <code>{name}</code>。",
    unfollow_miss: "⚠️ 名單中沒有 <code>{name}</code>。",
    folders: "📁 <b>你的資料夾</b>\n\n{list}",
    folders_empty: "（尚無資料夾 — 可試 <code>新增 量子計算</code>）",
    folder_add: "✅ 已新增資料夾：<b>{name}</b>",
    folder_rename: "✅ 已更名 <b>{old}</b> → <b>{new}</b>",
    folder_del: "✅ 已刪除資料夾：<b>{name}</b>",
    unknown: "❓ 未知指令 <code>{cmd}</code>。請用 <code>/help</code> 查看。沒有 / 的關鍵字才會搜尋論文。",
    no_papers: "😅 找不到與【{q}】相關的論文，請換個關鍵字。",
    ai_label: "AI 導讀：",
    pdf_label: "閱讀完整論文 / PDF",
    and_others: " 等 {n} 位",
    btn_deep: "💡 深度導讀",
    btn_seen: "👀 看過了",
    btn_skip: "👎 沒興趣",
    btn_archive: "☁️ 歸檔到雲端",
    review_hint: "📑 文獻綜述請到真實 bot 或 Pro 專區。模擬器不會把 /review 當成搜尋。",
    gap_hint: "🔍 缺口分析請到 Pro 專區的 Gap Scanner。/gap 不是搜尋關鍵字。",
    trend_need: "用法：<code>/trend quantum computing</code>",
    unlimited: "無限",
    pro_search: "搜尋 {n}/日",
    pro_deep: "深度導讀 {n}/日",
    pro_combo: "/review + /gap + /chat 各 {n}/日",
    pro_drive: "Drive：{n}/月",
    pro_report: "AI 分析報告：每週 {n} 次",
    pro_report_unlim: "AI 分析報告：無限制",
    btn_hot_transformer: "🔍 熱門：Transformer",
    btn_hot_crispr: "🧬 熱門：CRISPR",
    btn_bind: "🔗 綁定 Telegram",
    btn_view_pro: "👑 查看 Pro 特權",
    btn_full_help: "📖 完整指令幫助",
    btn_open_tg: "📱 開啟 Telegram 機器人",
    btn_oa: "🟢 免費全文 (OA)",
    btn_doi: "🔗 官方 DOI 頁面",
    web_tg: "📱 你已經在網頁大總部。\n\n真實 Telegram bot 這顆按鈕會開啟網頁；模擬器則反過來——開啟真實 bot：\n\nhttps://t.me/{bot}",
    mode_top: "🏆 頂級期刊/頂會",
    mode_smart: "⚡ 智慧精選",
    mode_free: "🟢 僅免費全文",
  },
  zh_hans: {
    start: "👋 嗨 <b>{name}</b>，欢迎使用 <b>PaperFilterBot 科研大总部</b>！\n\n🔬 <b>只有这里才有的科研特权</b>：\n• 5 大学术库交叉检索（arXiv / PubMed / Semantic Scholar / CrossRef / OpenAlex）\n• 💡 4 维 AI 深度导读（动机、方法、发现、限制）\n• 🔄 Telegram ↔ 网页大总部双向同步：手机与电脑同一文献库\n• 👁 看过 / 没兴趣双轨学习：排序会记住你真正要的论文（多数工具只有收藏或删除）\n• ☁️ Google Drive 双轨归档，文件夹自动维护 <code>references.bib</code>\n• 👤 追踪学者：其新作在每次搜索中权重 +50\n\n👇 请选择下方快捷功能，或直接发送<b>论文关键字</b>检索：",
    help: "📖 <b>PaperFilterBot 全指令导览</b>\n\n🔍 直接发送关键字检索\n💬 <b>/chat</b> · 📚 <b>/my</b> · 🔗 <b>/bind</b> · 💎 <b>/pro</b>\n📂 <b>/following</b> · ➕ <code>/follow 学者</code>\n📑 <code>/review</code> · 🔍 <code>/gap</code> · 📈 <code>/trend 领域</code>\n⚙️ <code>/mode</code> · 🌐 <code>/lang</code>\n📱 <code>/web</code> - 打开真实 Telegram 机器人（此处为网页模拟器）\n\n以 / 开头的指令不会被当成搜索。",
    bind: "🔗 <b>绑定网页总部</b>\n\n同步码：<code>{code}</code>\n\n请在网页点击「绑定 TG」后输入此代码。",
    pro_head: "📊 <b>方案比较</b>\n\n👤 当前方案：<b>{tier}</b>\n\n",
    pro_foot: "\n\n<i>定价尚未上线。测试员请在真实 Telegram bot 用 /redeem 兑换 7 天全功能。Lab 为商务洽询，不会即时解锁。</i>",
    lang_pick: "🌐 <b>界面语言</b>\n\n当前：<b>{current}</b>\n\n请点按钮，或发送 <code>/lang en</code> 等。",
    lang_ok: "✅ 语言已切换为 <b>{current}</b>。",
    mode_pick: "⚙️ <b>过滤模式</b>\n\n当前：<b>{current}</b>\n\n发送 <code>/mode smart</code>、<code>/mode top_tier</code> 或 <code>/mode free_only</code>。",
    mode_ok: "✅ 过滤模式已设为 <b>{mode}</b>。",
    following: "📋 <b>正在追踪的学者</b>\n\n{list}\n\n<i><code>/unfollow 名字</code> 可取消</i>",
    following_empty: "（暂无）",
    follow_ok: "🌟 已追踪 <code>{name}</code>（+50 权重）。",
    follow_need: "用法：<code>/follow Yann LeCun</code>",
    unfollow_ok: "✅ 已取消追踪 <code>{name}</code>。",
    unfollow_miss: "⚠️ 名单中没有 <code>{name}</code>。",
    folders: "📁 <b>你的文件夹</b>\n\n{list}",
    folders_empty: "（暂无文件夹）",
    folder_add: "✅ 已新增文件夹：<b>{name}</b>",
    folder_rename: "✅ 已更名 <b>{old}</b> → <b>{new}</b>",
    folder_del: "✅ 已删除文件夹：<b>{name}</b>",
    unknown: "❓ 未知指令 <code>{cmd}</code>。请用 <code>/help</code>。没有 / 的关键字才会搜索论文。",
    no_papers: "😅 找不到与【{q}】相关的论文，请换个关键字。",
    ai_label: "AI 导读：",
    pdf_label: "阅读完整论文 / PDF",
    and_others: " 等 {n} 位",
    btn_deep: "💡 深度导读",
    btn_seen: "👀 看过了",
    btn_skip: "👎 没兴趣",
    btn_archive: "☁️ 归档到云端",
    review_hint: "📑 文献综述请到真实 bot 或 Pro 专区。模拟器不会把 /review 当成搜索。",
    gap_hint: "🔍 缺口分析请到 Pro 专区。/gap 不是搜索关键字。",
    trend_need: "用法：<code>/trend quantum computing</code>",
    unlimited: "无限",
    pro_search: "搜索 {n}/日",
    pro_deep: "深度导读 {n}/日",
    pro_combo: "/review + /gap + /chat 各 {n}/日",
    pro_drive: "Drive：{n}/月",
    pro_report: "AI 分析报告：每周 {n} 次",
    pro_report_unlim: "AI 分析报告：无限制",
    btn_hot_transformer: "🔍 热门：Transformer",
    btn_hot_crispr: "🧬 热门：CRISPR",
    btn_bind: "🔗 绑定 Telegram",
    btn_view_pro: "👑 查看 Pro 特权",
    btn_full_help: "📖 完整指令帮助",
    btn_open_tg: "📱 打开 Telegram 机器人",
    btn_oa: "🟢 免费全文 (OA)",
    btn_doi: "🔗 官方 DOI 页面",
    web_tg: "📱 你已经在网页总部。\n\n真实 Telegram bot 这颗按钮会打开网页；模拟器则反过来——打开真实 bot：\n\nhttps://t.me/{bot}",
    mode_top: "🏆 顶级期刊/顶会",
    mode_smart: "⚡ 智慧精选",
    mode_free: "🟢 仅免费全文",
  },
  ja: {
    start: "👋 こんにちは <b>{name}</b>、<b>PaperFilterBot HQ</b> へようこそ！\n\n🔬 <b>ここだけの研究特権</b>：\n• 5大学術DB横断検索（arXiv / PubMed / Semantic Scholar / CrossRef / OpenAlex）\n• 💡 4次元 AI ディープ読解（動機・手法・発見・限界）\n• 🔄 Telegram ↔ Web HQ 双方向同期：スマホとPCで同じ文献庫\n• 👁 既読 / 興味なしの二重学習：順位が本当に欲しい論文を覚える\n• ☁️ Google Drive 二重保存と <code>references.bib</code> 自動更新\n• 👤 学者フォロー：新著が毎回の検索で +50 加点\n\n👇 下のショートカットを選ぶか、<b>キーワード</b>を送って検索：",
    help: "📖 <b>PaperFilterBot コマンド一覧</b>\n\n🔍 キーワードを直接送信\n💬 <b>/chat</b> · 📚 <b>/my</b> · 🔗 <b>/bind</b> · 💎 <b>/pro</b>\n📂 <b>/following</b> · ➕ <code>/follow 名前</code>\n📑 <code>/review</code> · 🔍 <code>/gap</code> · 📈 <code>/trend 分野</code>\n⚙️ <code>/mode</code> · 🌐 <code>/lang</code>\n📱 <code>/web</code> - 本番 Telegram bot を開く（ここは Web シミュレータ）\n\n/ で始まるコマンドは検索しません。",
    bind: "🔗 <b>Web HQ を Telegram に連携</b>\n\n同期コード：<code>{code}</code>\n\nサイトで「Bind TG」を押し、このコードを入力してください。",
    pro_head: "📊 <b>プラン比較</b>\n\n👤 現在のプラン：<b>{tier}</b>\n\n",
    pro_foot: "\n\n<i>価格は未公開です。テスターは本番 bot で /redeem。Lab は営業相談で即時解除されません。</i>",
    lang_pick: "🌐 <b>表示言語</b>\n\n現在：<b>{current}</b>\n\nボタンを押すか <code>/lang en</code> などを送ってください。",
    lang_ok: "✅ 言語を <b>{current}</b> に設定しました。",
    mode_pick: "⚙️ <b>フィルタモード</b>\n\n現在：<b>{current}</b>\n\n<code>/mode smart</code> / <code>top_tier</code> / <code>free_only</code>",
    mode_ok: "✅ モードを <b>{mode}</b> に設定しました。",
    following: "📋 <b>フォロー中の学者</b>\n\n{list}\n\n<i><code>/unfollow 名前</code> で解除</i>",
    following_empty: "（まだいません）",
    follow_ok: "🌟 <code>{name}</code> をフォローしました（+50）。",
    follow_need: "使い方：<code>/follow Yann LeCun</code>",
    unfollow_ok: "✅ <code>{name}</code> のフォローを解除しました。",
    unfollow_miss: "⚠️ <code>{name}</code> はリストにありません。",
    folders: "📁 <b>フォルダ</b>\n\n{list}",
    folders_empty: "（フォルダなし）",
    folder_add: "✅ フォルダを作成：<b>{name}</b>",
    folder_rename: "✅ 改名 <b>{old}</b> → <b>{new}</b>",
    folder_del: "✅ フォルダ削除：<b>{name}</b>",
    unknown: "❓ 未知のコマンド <code>{cmd}</code>。<code>/help</code> を見てください。/ なしの語句だけが検索になります。",
    no_papers: "😅 [{q}] に一致する論文が見つかりません。",
    ai_label: "AI ガイド：",
    pdf_label: "全文 / PDF を読む",
    and_others: " ほか {n} 名",
    btn_deep: "💡 詳細解説",
    btn_seen: "👀 閲覧済み",
    btn_skip: "👎 興味なし",
    btn_archive: "☁️ ドライブ保存",
    review_hint: "📑 文献レビューは本番 bot または Pro Suite で実行します。/review は検索しません。",
    gap_hint: "🔍 ギャップ分析は Pro Suite の Gap Scanner です。/gap は検索しません。",
    trend_need: "使い方：<code>/trend quantum computing</code>",
    unlimited: "無制限",
    pro_search: "検索 {n}/日",
    pro_deep: "詳細解説 {n}/日",
    pro_combo: "/review + /gap + /chat 各 {n}/日",
    pro_drive: "Drive：{n}/月",
    pro_report: "AI レポート：週 {n} 回",
    pro_report_unlim: "AI レポート：無制限",
    btn_hot_transformer: "🔍 人気：Transformer",
    btn_hot_crispr: "🧬 人気：CRISPR",
    btn_bind: "🔗 Telegram を連携",
    btn_view_pro: "👑 Pro機能を見る",
    btn_full_help: "📖 コマンド一覧",
    btn_open_tg: "📱 Telegram bot を開く",
    btn_oa: "🟢 オープンアクセス",
    btn_doi: "🔗 公式DOIページ",
    web_tg: "📱 すでに Web HQ にいます。\n\n本番 bot ではこのボタンが Web を開きます。シミュレータでは逆で、本番 bot を開きます：\n\nhttps://t.me/{bot}",
    mode_top: "🏆 トップジャーナル",
    mode_smart: "⚡ スマート精選",
    mode_free: "🟢 OA のみ",
  },
};
function st(lang: SimLang, key: string, vars: Record<string, string | number> = {}): string {
  let text = SIM[lang]?.[key] || SIM.en[key] || key;
  for (const [k, v] of Object.entries(vars)) text = text.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
  return text;
}
const LANG_LABEL: Record<SimLang, string> = { en: "English", zh_hant: "繁體中文", zh_hans: "简体中文", ja: "日本語" };

// 13. Telegram Bot Simulator — commands are never treated as keyword search
app.post("/api/simulate-bot", async (_req, res) => {
  res.status(410).json({ success: false, error: "Gone" });
});

/* disabled bot simulator body
  try {
    const { text, lang: bodyLang, user_id = currentUserId() } = req.body;
    if (!text) return res.status(400).json({ error: "Message required" });

    const trimmed = text.trim();
    const profile = await buildProfile();
    let lang = normSimLang(bodyLang || profile.user_lang);
    const followedAuthors = await getAuthors();
    const userCategories = await getCategories();

    const botHandle = (process.env.TELEGRAM_BOT_USERNAME || "paper_filter_bot").replace(/^@/, "");
    const startButtons = () => [
      { label: st(lang, "btn_hot_transformer"), action: "search:Transformer" },
      { label: st(lang, "btn_hot_crispr"), action: "search:CRISPR" },
      { label: st(lang, "btn_bind"), action: "bind" },
      { label: st(lang, "btn_view_pro"), action: "pro" },
      { label: st(lang, "btn_full_help"), action: "help" },
      { label: st(lang, "btn_open_tg"), action: "open_telegram" },
    ];

    const paperCard = (paper: PaperItem) => {
      const extra = paper.authors.length > 3 ? st(lang, "and_others", { n: paper.authors.length - 3 }) : "";
      const authorsStr = paper.authors.slice(0, 3).join(", ") + extra;
      const oa = paper.is_open_access ? "🟢 OA" : "";
      const summary = (paper.summary || "").slice(0, 200);
      return {
        type: "paper_card",
        paper,
        text: `📄 <b>${paper.title}</b>\n\n👥 ${authorsStr} | 📅 ${paper.year} | 🗂 ${paper.source} ${oa}\n\n🧠 <b>${st(lang, "ai_label")}</b>\n${summary}...\n\n🔗 <a href="${paper.link}">${st(lang, "pdf_label")}</a>`,
        buttons: [
          { label: st(lang, "btn_deep"), action: "deep" },
          { label: st(lang, "btn_seen"), action: "seen" },
          { label: st(lang, "btn_skip"), action: "skip" },
          { label: st(lang, "btn_archive"), action: "archive" },
          {
            label: paper.is_open_access ? st(lang, "btn_oa") : st(lang, "btn_doi"),
            action: paper.is_open_access ? "oa" : "doi",
            url: paper.link,
          },
        ],
      };
    };

    const doSearch = async (q: string) => {
      const papers = await fetchAcademicPapers(q, profile.filter_mode);
      if (!papers.length) return res.json({ type: "text", text: st(lang, "no_papers", { q }) });
      return res.json(paperCard(papers[0]));
    };

    const isSlash = trimmed.startsWith("/");
    const [rawCmd, ...restParts] = isSlash ? trimmed.slice(1).split(/\s+/) : ["", ""];
    const cmd = rawCmd.toLowerCase();
    const arg = isSlash ? restParts.join(" ").trim() : "";

    if (isSlash && cmd && cmd !== "search") {
      if (cmd === "start" || cmd === "welcome") {
        const name = profile.username || "Researcher";
        return res.json({ type: "text", text: st(lang, "start", { name }), buttons: startButtons() });
      }
      if (cmd === "help" || cmd === "h" || cmd === "guide") {
        return res.json({
          type: "text",
          text: st(lang, "help"),
          buttons: [
            { label: st(lang, "btn_bind"), action: "bind" },
            { label: st(lang, "btn_view_pro"), action: "pro" },
            { label: st(lang, "btn_open_tg"), action: "open_telegram" },
          ],
        });
      }
      if (cmd === "web") {
        return res.json({
          type: "text",
          text: st(lang, "web_tg", { bot: botHandle }),
          buttons: [{ label: st(lang, "btn_open_tg"), action: "open_telegram" }],
        });
      }
      if (cmd === "bind") {
        const code = (await getPendingCode(user_id)) || (await createBindCode(user_id));
        return res.json({
          type: "text",
          text: st(lang, "bind", { code }),
          buttons: [{ label: st(lang, "btn_open_tg"), action: "open_telegram" }],
        });
      }
      if (cmd === "pro") {
        const fmtN = (n: number) => isUnlimited(n) ? st(lang, "unlimited") : String(n);
        const blocks = TIER_ORDER.map((tc) => {
          const d = TIER_DEFS[tc];
          const report = isUnlimited(d.daily_digest_limit)
            ? st(lang, "pro_report_unlim")
            : st(lang, "pro_report", { n: d.daily_digest_limit });
          return `<b>${tc}</b>\n• ${st(lang, "pro_search", { n: fmtN(d.daily_search_limit) })}\n• ${st(lang, "pro_deep", { n: fmtN(d.daily_deep_limit) })}\n• ${st(lang, "pro_combo", { n: fmtN(d.daily_chat_limit) })}\n• ${st(lang, "pro_drive", { n: fmtN(d.drive_monthly_limit) })}\n• ${report}`;
        }).join("\n\n");
        return res.json({ type: "text", text: st(lang, "pro_head", { tier: profile.tier }) + blocks + st(lang, "pro_foot") });
      }
      if (cmd === "lang" || cmd === "language") {
        const next = parseLangArg(arg);
        if (next) {
          await setUserLang(next);
          return res.json({ type: "text", text: st(next, "lang_ok", { current: LANG_LABEL[next] }), switched_lang: next });
        }
        return res.json({
          type: "text",
          text: st(lang, "lang_pick", { current: LANG_LABEL[lang] }),
          buttons: [
            { label: "English", action: "lang_en" },
            { label: "日本語", action: "lang_ja" },
            { label: "繁體中文", action: "lang_zh_hant" },
            { label: "简体中文", action: "lang_zh_hans" },
          ],
        });
      }
      if (cmd === "mode") {
        const allowed = ["smart", "top_tier", "free_only"];
        if (arg && allowed.includes(arg)) {
          await setFilterMode(arg);
          return res.json({ type: "text", text: st(lang, "mode_ok", { mode: arg }) });
        }
        return res.json({
          type: "text",
          text: st(lang, "mode_pick", { current: profile.filter_mode }),
          buttons: [
            { label: st(lang, "mode_smart"), action: "mode:smart" },
            { label: st(lang, "mode_top"), action: "mode:top_tier" },
            { label: st(lang, "mode_free"), action: "mode:free_only" },
          ],
        });
      }
      if (cmd === "following" || cmd === "authors") {
        const list = followedAuthors.map((a) => `• <code>${a}</code>`).join("\n") || st(lang, "following_empty");
        return res.json({ type: "text", text: st(lang, "following", { list }) });
      }
      if (cmd === "follow" || cmd === "track") {
        if (!arg) return res.json({ type: "text", text: st(lang, "follow_need") });
        if (!followedAuthors.includes(arg)) await addAuthor(arg);
        return res.json({ type: "text", text: st(lang, "follow_ok", { name: arg }) });
      }
      if (cmd === "unfollow" || cmd === "untrack") {
        if (!arg) return res.json({ type: "text", text: st(lang, "follow_need") });
        if (!followedAuthors.includes(arg)) return res.json({ type: "text", text: st(lang, "unfollow_miss", { name: arg }) });
        await removeAuthor(arg);
        return res.json({ type: "text", text: st(lang, "unfollow_ok", { name: arg }) });
      }
      if (cmd === "folders" || cmd === "myfolders" || cmd === "categories") {
        const list = userCategories.map((c) => `• ${c}`).join("\n") || st(lang, "folders_empty");
        return res.json({ type: "text", text: st(lang, "folders", { list }) });
      }
      if (cmd === "review") return res.json({ type: "text", text: st(lang, "review_hint") });
      if (cmd === "gap") return res.json({ type: "text", text: st(lang, "gap_hint") });
      if (cmd === "trend") {
        if (!arg) return res.json({ type: "text", text: st(lang, "trend_need") });
        return doSearch(arg);
      }
      if (cmd === "deep") return res.json({ type: "text", text: st(lang, "help") });
      return res.json({ type: "text", text: st(lang, "unknown", { cmd: "/" + cmd }) });
    }

    const lower = trimmed.toLowerCase();
    const folderListCmds = ["my folders", "我的資料夾", "我的文件夹", "マイフォルダ"];
    if (folderListCmds.includes(lower) || folderListCmds.includes(trimmed)) {
      const list = userCategories.map((c) => `• ${c}`).join("\n") || st(lang, "folders_empty");
      return res.json({ type: "text", text: st(lang, "folders", { list }) });
    }
    const addFolder = trimmed.match(/^(?:add folder|新增|添加|追加)\s+(.+)$/i);
    if (addFolder) {
      const name = addFolder[1].trim();
      if (name) await addCategory(name);
      return res.json({ type: "text", text: st(lang, "folder_add", { name }) });
    }
    const renameFolder = trimmed.match(/^(?:rename|改名|更名)\s+(.+?)\s*(?:->|→|-)\s*(.+)$/i);
    if (renameFolder) {
      const oldName = renameFolder[1].trim();
      const newName = renameFolder[2].trim();
      await renameCategory(oldName, newName);
      return res.json({ type: "text", text: st(lang, "folder_rename", { old: oldName, new: newName }) });
    }
    const delFolder = trimmed.match(/^(?:delete folder|刪除|删除|削除)\s+(.+)$/i);
    if (delFolder) {
      const name = delFolder[1].trim();
      await deleteCategory(name);
      return res.json({ type: "text", text: st(lang, "folder_del", { name }) });
    }
    const followNl = trimmed.match(/^(?:follow|追蹤|追踪|フォロー)\s+(.+)$/i);
    if (followNl) {
      const name = followNl[1].trim();
      if (!followedAuthors.includes(name)) await addAuthor(name);
      return res.json({ type: "text", text: st(lang, "follow_ok", { name }) });
    }

    const searchQuery = trimmed.replace(/^\/search\s+/i, "");
    return doSearch(searchQuery);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});
disabled bot simulator body */

// 14. System files content provider
app.get("/api/files", (req, res) => {
  try {
    const files = [
      "bot.py",
      "paper_search.py",
      "OAuthur2.py",
      "database.py",
      "classifier.py",
      "i18n.py",
      "requirements.txt",
      "README.md",
      ".env.example"
    ];

    const result: Record<string, string> = {};
    for (const f of files) {
      const fullPath = path.join(process.cwd(), f);
      if (fs.existsSync(fullPath)) {
        result[f] = fs.readFileSync(fullPath, "utf-8");
      }
    }

    res.json({ success: true, files: result });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Vite middleware for development & Static files in production
async function startServer() {
  try {
    await initTables();
    console.log("✅ Turso 資料表初始化完成");
  } catch (e) {
    console.error("⚠️ Turso 初始化失敗（網頁將以空資料運作）：", e);
  }

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`PaperFilterBot Headquarters Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
