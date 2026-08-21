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
  setTier,
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
  type PaperItem,
} from "./db";
import { getVenueTier, credibilityBadge, isPreprint } from "./src/academicTiers";

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
  const token = process.env.TELEGRAM_BOT_TOKEN;
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

// ================= In-memory (demo-only) state =================
// 這些欄位 bot 未存入 Turso，僅在網頁程序生命週期內保留：
interface HistoryItem {
  id: string;
  action: 'archive' | 'seen' | 'skip' | 'deep_read' | 'search';
  paper_id?: string;
  paper_title: string;
  authors?: string[];
  year?: string;
  source?: string;
  category?: string;
  timestamp: string;
  details?: string;
}

let telegramHandle = "@ares_researcher";
const baseProfile = {
  username: "Ares (科研總監)",
  pro_expires_at: "2026-12-31",
};
let totalReadCount = 86;
let totalArchivedCount = 24;
let totalSkippedCount = 42;
let totalDeepReadCount = 18;

let userHistory: HistoryItem[] = [
  {
    id: "h_1",
    action: "archive",
    paper_id: "s2_dpo_preference",
    paper_title: "Direct Preference Optimization: Your Language Model is Secretly a Reward Model",
    authors: ["Rafael Rafailov", "Chelsea Finn"],
    year: "2023",
    source: "NeurIPS",
    category: "人工智慧",
    timestamp: new Date(Date.now() - 3600000 * 2).toISOString(),
    details: "雙軌歸檔至 Google Drive [人工智慧] & references.bib"
  },
  {
    id: "h_2",
    action: "deep_read",
    paper_id: "s2_dpo_preference",
    paper_title: "Direct Preference Optimization: Your Language Model is Secretly a Reward Model",
    authors: ["Rafael Rafailov", "Chelsea Finn"],
    year: "2023",
    source: "NeurIPS",
    category: "人工智慧",
    timestamp: new Date(Date.now() - 3600000 * 3).toISOString(),
    details: "完成 AI 4 大維度深度導讀與 BibTeX 提取"
  },
  {
    id: "h_3",
    action: "seen",
    paper_id: "s2_llama3",
    paper_title: "The Llama 3 Herd of Models",
    authors: ["Meta AI Research Team"],
    year: "2024",
    source: "arXiv (開源預印本)",
    category: "人工智慧",
    timestamp: new Date(Date.now() - 3600000 * 12).toISOString(),
    details: "標記為已讀，保留領域偏好 (+12分)"
  },
  {
    id: "h_4",
    action: "skip",
    paper_id: "s2_nft_rendering",
    paper_title: "NFT Rendering on Mobile GPUs",
    authors: ["Anonymous"],
    year: "2022",
    source: "IEEE Trans",
    category: "電腦圖形",
    timestamp: new Date(Date.now() - 3600000 * 24).toISOString(),
    details: "標記沒興趣，調降 rendering / nft 相關權重 (-6分)"
  },
  {
    id: "h_5",
    action: "archive",
    paper_id: "pmid_crispr_cas9",
    paper_title: "A programmable dual-RNA-guided DNA endonuclease in adaptive bacterial immunity",
    authors: ["Jennifer A Doudna", "Emmanuelle Charpentier"],
    year: "2012",
    source: "Science (頂刊 35.8 IF)",
    category: "生命科學",
    timestamp: new Date(Date.now() - 86400000 * 3).toISOString(),
    details: "歸檔至 Google Drive [生命科學]"
  }
];

let digestConfig = {
  is_active: true,
  frequency: "weekly" as "daily" | "weekly",
  push_time: "08:30",
  topics: ["Transformer", "CRISPR", "LLM Alignment", "Quantum Computing"],
  include_deep: true
};

let userBias = {
  positive: { transformer: 5, crispr: 4, alignment: 3, dpo: 3 } as Record<string, number>,
  negative: { animation: 2, rendering: 1, crypto: 3 } as Record<string, number>
};

// 網頁端 UI 專用欄位（starred / notes / tags）Turso 目前未儲存，先用 overlay 保留於程序記憶體
const paperOverlay: Record<string, { user_notes?: string; tags?: string[]; is_starred?: boolean }> = {};

// ================= Profile builder =================
async function buildProfile() {
  const dbp = await getProfile();
  const webUid = currentUserId();
  const link = await getLinkByWeb(webUid);
  const syncCode = (await getPendingCode(webUid)) || (await createBindCode(webUid));
  return {
    user_id: webUid,
    username: baseProfile.username,
    telegram_handle: telegramHandle,
    is_telegram_linked: !!link,
    telegram_id: link ? link.telegram_user_id : null,
    sync_code: syncCode,
    tier: dbp.tier,
    pro_expires_at: baseProfile.pro_expires_at,
    filter_mode: dbp.filter_mode,
    user_lang: dbp.user_lang,
    total_read_count: totalReadCount,
    total_archived_count: totalArchivedCount,
    total_skipped_count: totalSkippedCount,
    total_deep_read_count: totalDeepReadCount,
  };
}

async function loadLibrary(): Promise<PaperItem[]> {
  const lib = await getLibrary();
  return lib.map(p => {
    const o = paperOverlay[p.id];
    return o ? { ...p, ...o } : p;
  });
}

// 模型 -> 所需最低訂閱方案（全部使用 GPT-4o-mini，統一低成本）
const MODEL_TIERS: Record<string, "free" | "basic" | "standard" | "premium" | "ultra"> = {
  "gpt-4o-mini": "free",
};
const TIER_RANK: Record<string, number> = { free: 0, basic: 1, standard: 2, premium: 3, ultra: 4 };

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

// 4 大官方學術庫即時查詢 (arXiv, PubMed, Semantic Scholar, CrossRef)
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
      credibility_label: cred.label,
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
    if (uname) user.username = uname;
    const categories = await getCategories();
    const authors = await getAuthors();
    const library = await loadLibrary();
    res.json({
      success: true,
      user,
      categories,
      followed_authors: authors,
      library_count: library.length,
      history_count: userHistory.length
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

app.post("/api/auth/upgrade-tier", async (req, res) => {
  const { tier } = req.body;
  const validTiers = ["free", "basic", "standard", "premium", "ultra"];
  if (!tier || !validTiers.includes(tier)) {
    return res.status(400).json({ error: "無效的方案，請選擇 basic/standard/premium/ultra" });
  }
  await setTier(tier);
  res.json({
    success: true,
    message: `✅ 已成功升級至 ${tier} 方案！`,
    user: await buildProfile()
  });
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
  res.json({
    success: true,
    history: userHistory,
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
    const c = p.category || "未分類";
    categoryCounts[c] = (categoryCounts[c] || 0) + 1;
  }

  const now = new Date();
  const readingTrend = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 86400000);
    const dayLabel = `${d.getMonth() + 1}/${d.getDate()}`;
    readingTrend.push({
      date: dayLabel,
      searches: 8 + Math.floor(Math.sin(i) * 4 + (7 - i) * 2),
      archived: 2 + (i % 3 === 0 ? 3 : 1),
      deep_reads: 1 + (i % 2 === 0 ? 2 : 0)
    });
  }

  res.json({
    success: true,
    category_distribution: Object.entries(categoryCounts).map(([name, value]) => ({ name, value })),
    reading_trend: readingTrend,
    top_sources: [
      { name: "NeurIPS / ICML", count: 12 },
      { name: "Science / Nature", count: 8 },
      { name: "arXiv CS/AI", count: 15 },
      { name: "PubMed 生醫", count: 9 }
    ]
  });
});

// 3. Search endpoint
app.post("/api/search", async (req, res) => {
  try {
    const { query, mode } = req.body;
    if (!query) return res.status(400).json({ error: "請輸入搜尋關鍵字" });

    const profile = await buildProfile();
    const searchMode = mode || profile.filter_mode;

    totalReadCount += 1;
    userHistory.unshift({
      id: `h_${Date.now()}`,
      action: "search",
      paper_title: `搜尋主題：${query}`,
      timestamp: new Date().toISOString(),
      details: `以 [${searchMode}] 策略跨 4 大庫進行檢索`
    });

    const papers = await fetchAcademicPapers(query, searchMode);
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

    totalDeepReadCount += 1;
    userHistory.unshift({
      id: `h_${Date.now()}`,
      action: "deep_read",
      paper_title: title,
      authors,
      year,
      source,
      timestamp: new Date().toISOString(),
      details: "完成 AI 4 大維度深度導讀與 BibTeX 提取"
    });

    const gemini = getGeminiClient();
    let deepReport = "";

    if (gemini) {
      try {
        const response = await gemini.models.generateContent({
          model: req.body?.model,
          contents: `你是一位頂級學術期刊審稿專家與科研導讀專家。請針對以下學術論文進行深度 4 大維度導讀。

【嚴格誠信規則】：
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

    res.json({ success: true, deep_report: deepReport, bibtex });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "生成深度導讀失敗" });
  }
});

// 5. Literature Review & Gap Analysis
app.post("/api/review", async (req, res) => {
  try {
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

    res.json({ success: true, review: reviewText, paper_count: papers.length });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "文獻綜述生成失敗" });
  }
});

app.post("/api/gap", async (req, res) => {
  try {
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

    res.json({ success: true, gap_analysis: gapText });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "研究缺口分析失敗" });
  }
});

// 6. Pro: Chat with Library (RAG over user library)
app.post("/api/pro/chat-library", async (req, res) => {
  try {
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

    res.json({ success: true, matrix: matrixData });
  } catch (err: any) {
    res.status(500).json({ error: err.message || "生成對比矩陣失敗" });
  }
});

// 8. Digest Schedule
app.get("/api/digest/settings", (req, res) => {
  res.json({ success: true, config: digestConfig });
});

app.post("/api/digest/settings", (req, res) => {
  digestConfig = { ...digestConfig, ...req.body };
  res.json({ success: true, config: digestConfig, message: "定時推播設定已更新！" });
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

    const existing = (await getLibrary()).find(p => p.fingerprint === paper.fingerprint || p.id === paper.id);
    const bibtex = paper.bibtex || generateBibTeX(paper);
    const item: PaperItem = {
      ...paper,
      bibtex,
      category: paper.category || "人工智慧",
      user_notes: paper.user_notes || "",
      tags: paper.tags || ["已收藏"],
      is_starred: paper.is_starred ?? false,
      added_at: new Date().toISOString()
    };

    await addPaper(item);
    if (!existing) {
      totalArchivedCount += 1;
    }

    userHistory.unshift({
      id: `h_${Date.now()}`,
      action: "archive",
      paper_id: item.id,
      paper_title: item.title,
      authors: item.authors,
      year: item.year,
      source: item.source,
      category: item.category,
      timestamp: new Date().toISOString(),
      details: `歸檔至 [${item.category}] 雲端資料夾 & references.bib`
    });

    const updated = (await loadLibrary()).find(p => p.id === item.id) || item;
    res.json({ success: true, message: "論文已成功雙軌歸檔至大總部與 Google Drive！", paper: updated });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.post("/api/library/update-paper", async (req, res) => {
  try {
    const { id, user_notes, tags, is_starred, category } = req.body;
    if (category !== undefined) await updatePaper(id, { category });
    paperOverlay[id] = {
      ...(paperOverlay[id] || {}),
      ...(user_notes !== undefined ? { user_notes } : {}),
      ...(tags !== undefined ? { tags } : {}),
      ...(is_starred !== undefined ? { is_starred } : {}),
    };
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
    delete paperOverlay[id];
    res.json({ success: true, message: "已自大總部文獻庫移除" });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 10. Categories & Authors
app.post("/api/categories", async (req, res) => {
  try {
    const { action, name, oldName, newName } = req.body;
    if (action === "add" && name) await addCategory(name);
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
    if (action === "add" && name) await addAuthor(name);
    else if (action === "remove" && name) await removeAuthor(name);
    res.json({ success: true, followed_authors: await getAuthors() });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 11. Export endpoint
app.post("/api/export", async (req, res) => {
  try {
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

    res.json({ success: true, format, content, count: papers.length });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 12. Trend Analysis
app.post("/api/trend", async (req, res) => {
  try {
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

// 13. Telegram Bot Simulator Route (with instant sync to web history)
app.post("/api/simulate-bot", async (req, res) => {
  try {
    const { text, user_id = currentUserId() } = req.body;
    if (!text) return res.status(400).json({ error: "請輸入訊息" });

    const trimmed = text.trim();
    const profile = await buildProfile();
    const followedAuthors = await getAuthors();
    const userCategories = await getCategories();

    // Command handling
    if (trimmed === "/start") {
      return res.json({
        type: "text",
        text: `👋 您好！我是您的 <b>PaperFilterBot 全球學術研究秘書</b>。

🌐 <b>全網 4 大庫直連</b>：Semantic Scholar、CrossRef 頂刊、PubMed、arXiv

💡 <b>核心亮點</b>：
• 傳送關鍵字直接搜尋最新權威論文
• 點擊 <b>[🔍 深度導讀]</b> 獲得 4 大解析並隨附 BibTeX 代碼
• 支援 <b>[👁️ 我看過了]</b> 與 <b>[❌ 沒興趣]</b> 雙軌偏好過濾
• 歸檔自動在 Drive 維護 <code>references.bib</code> 引用總庫
• <code>/web</code> 或 <code>/bind</code>: 取得電腦科研大總部同步碼
• <code>/pro</code>: 查看 Pro 專業版特權（AI全庫問答、對比矩陣、週刊推播）
• <code>/mode</code>: 自訂檢索模式
• <code>/follow 作者名</code>: 追蹤頂尖學者 (+50 分權重)

輸入 <code>/help</code> 可隨時查看完整指令！`
      });
    }

    if (trimmed === "/bind" || trimmed === "/web") {
      const code = (await getPendingCode(user_id)) || (await createBindCode(user_id));
      return res.json({
        type: "text",
        text: `🔗 <b>電腦科研大總部同步帳號綁定</b>

您的專屬 6 位數同步碼為：<code>${code}</code>

🖥️ 請打開電腦瀏覽器大總部網頁，點擊右上角 <b>【綁定 Telegram】</b> 並輸入此代碼，即可將所有論文庫、標記已讀/沒興趣記錄與筆記進行雙向即時同步！`
      });
    }

    if (trimmed === "/pro") {
      return res.json({
        type: "text",
        text: `📊 <b>PaperFilterBot 方案比較</b>

👤 您目前的方案：<b>${profile.tier === 'ultra' ? 'Ultra' : profile.tier === 'premium' ? 'Premium' : profile.tier === 'standard' ? 'Standard' : profile.tier === 'basic' ? 'Basic' : 'Free'}</b>

<b>Free (免費)</b>
• 搜尋：10 次/日、深度導讀：1 次/日
• Google Drive：5 篇/月、有廣告

<b>Basic</b>
• 搜尋：30 次/日、深度導讀：5 次/日
• 解鎖 /chat 跨文獻問答（10次/月）
• Google Drive：30 篇/月、無廣告

<b>Standard</b>
• 搜尋：100 次/日、深度導讀：15 次/日
• 解鎖 /review 文獻綜述、/gap 研究缺口
• Google Drive：100 篇/月、每月 AI 分析報告

<b>Premium</b>
• 搜尋：200 次/日、深度導讀：30 次/日
• 所有功能量大幅增加、Google Drive 無限
• 每週 AI 分析報告

<b>Ultra</b>
• 搜尋：500 次/日、深度導讀：50 次/日
• 所有功能無限、每日 AI 分析報告`
      });
    }

    if (trimmed === "/help") {
      return res.json({
        type: "text",
        text: `📖 <b>PaperFilterBot 功能指南</b>

🔍 <b>論文搜尋與閱讀</b>
• 直接傳送關鍵字（如 <code>CRISPR</code>、<code>transformer</code>）或使用 <code>/search 關鍵字</code>
• 點擊 <b>[🔍 深度導讀]</b> 獲得 4 大解析，並附帶 <b>BibTeX 引用格式</b>

🎯 <b>看過/略過雙軌操作</b>
• <b>[👁️ 我看過了]</b>：標記已讀，保留正向興趣繼續推薦
• <b>[❌ 沒興趣]</b>：標記略過並調降該領域權重

📦 <b>Google Drive 雙拼歸檔</b>
• 筆記內自動附帶專屬 BibTeX 代碼
• 雲端資料夾自動維護 <code>references.bib</code> 總庫

👥 <b>學者追蹤</b>
• <code>/follow 作者名</code>：追蹤大牛學者（+50 權重）
• <code>/following</code>：查看追蹤名單

💻 <b>大總部同步</b>
• <code>/bind</code> 或 <code>/web</code>：取得電腦端同步碼`
      });
    }

    if (trimmed === "/following") {
      const list = followedAuthors.map(a => `• <code>${a}</code>`).join("\n");
      return res.json({
        type: "text",
        text: `📋 <b>您關注的學者清單</b>：

${list || "（尚無追蹤學者）"}

<i>輸入 <code>/unfollow 名字</code> 可取消關注</i>`
      });
    }

    if (trimmed.startsWith("/follow ")) {
      const name = trimmed.replace("/follow ", "").trim();
      if (!followedAuthors.includes(name)) await addAuthor(name);
      return res.json({
        type: "text",
        text: `🌟 <b>成功追蹤學者</b>：<code>${name}</code>

若為該學者著作將自動享有 <b>+50分權重優先推薦</b>！`
      });
    }

    if (trimmed.startsWith("新增 ")) {
      const folderName = trimmed.replace("新增 ", "").trim();
      if (folderName && !userCategories.includes(folderName)) {
        await addCategory(folderName);
      }
      return res.json({
        type: "text",
        text: `✅ 已成功新增分類資料夾：<b>${folderName}</b>`
      });
    }

    if (trimmed === "我的資料夾" || trimmed === "/folders") {
      const list = userCategories.map(c => `• ${c}`).join("\n");
      return res.json({
        type: "text",
        text: `📁 <b>您的雲端分類資料夾</b>：

${list || "（尚無分類資料夾）"}`
      });
    }

    // Default search flow
    let searchQuery = trimmed.replace(/^\/search\s+/, "");
    const papers = await fetchAcademicPapers(searchQuery, profile.filter_mode);

    if (papers.length === 0) {
      return res.json({
        type: "text",
        text: `😅 找不到與【${searchQuery}】相關的論文，請換個關鍵字試試。`
      });
    }

    const topPaper = papers[0];
    const authorsStr = topPaper.authors.slice(0, 3).join(", ") + (topPaper.authors.length > 3 ? ` 等 ${topPaper.authors.length} 位` : "");

    return res.json({
      type: "paper_card",
      paper: topPaper,
      text: `📄 <b>${topPaper.title}</b>\n\n👥 ${authorsStr} | 📅 ${topPaper.year} | 🗂 ${topPaper.source} ${topPaper.is_open_access ? "🟢 OA" : ""}\n\n🧠 <b>AI 導讀：</b>\n${topPaper.summary.slice(0, 200)}...\n\n🔗 <a href="${topPaper.link}">閱讀完整論文 / PDF</a>`,
      buttons: [
        { label: "🔍 深度導讀 (/deep)", action: "deep", data: topPaper.fingerprint },
        { label: "👁️ 我看過了 (保持興趣)", action: "seen", data: topPaper.id },
        { label: "❌ 沒興趣 (減少此類)", action: "skip", data: topPaper.id },
        { label: "☁️ 歸檔到 Google Drive", action: "archive", data: topPaper.id }
      ]
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

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
