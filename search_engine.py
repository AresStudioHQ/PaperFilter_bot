"""arXiv + PubMed + Semantic Scholar + CrossRef + OpenAlex 全球權威論文多源檢索引擎
支援：
1. 檢索模式自訂 (filter_mode):
   - 'top_tier': 頂刊權威優先模式
   - 'smart': 智慧平衡模式
   - 'free_only': 開源全文優先模式
2. 跨平台智慧標題指紋去重
3. 關注學者加權 + 引用數加權
4. 【統一 AI 引擎】：全部使用 GPT-4o-mini（低成本、高速度）
5. 【跨文獻 RAG 智慧問答】(/chat [問題])
6. 本地 SQLite / Turso 快取 (Cache Layer)
7. 自動文獻綜述生成 (Literature Review)
8. 研究缺口分析 (Research Gap Analysis)
9. 國際研究趨勢分析 (Trend Analysis)
10. 多格式匯出 (RIS/BibTeX/CSV)
"""
import re
import sys
import urllib.parse
import os
import json
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from collections import Counter
import feedparser
import requests
from Bio import Entrez
from openai import OpenAI
from database import db

# 學術期刊/會議權威分級資料庫
try:
    import academic_tiers
except ImportError:
    academic_tiers = None

Entrez.email = os.getenv("ENTREZ_EMAIL", "paperfilter-bot@example.com")
ARXIV_API = "https://export.arxiv.org/api/query"
USER_AGENT = "PaperFilterBot/3.0 (academic-paper-filter; mailto:paperfilter-bot@example.com)"
ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
REQUEST_TIMEOUT = 8

KEYWORD_ALIASES: dict[str, list[str]] = {
    "psycology": ["psychology", "psychological", "psychologist"],
    "psychology": ["psychology", "psychological", "psychologist"],
    "financial": ["financial", "finance", "financing"],
    "finance": ["finance", "financial", "financing"],
    "animal": ["animal", "animals"],
    "animals": ["animal", "animals"],
    "creature": ["creature", "creatures"],
    "creatures": ["creature", "creatures"],
}

DOMAIN_RULES: dict[str, dict] = {
    "animal": {
        "reject_title": [
            "animation", "animated", "facial", "talking head", "talking face",
            "3d", "mesh", "rendering", "avatar", "blendshape", "graphics",
            "videogame", "game engine", "motion capture", "mocap",
            "neural radiance", "diffusion model", "generative model",
            "computer vision", "deepfake",
        ],
        "boost": [
            "species", "wildlife", "zoology", "mammal", "insect", "behavior",
            "behaviour", "ecology", "organism", "drosophila", "vertebrate",
            "fauna", "birds", "fish", "mouse", "mice", "rats", "livestock",
            "veterinary", "zoological", "genome", "biodiversity",
        ],
        "require_title_or_boost": True,
    },
    "creature": {
        "reject_title": [
            "animation", "animated", "facial", "3d", "graphics", "rendering",
            "videogame", "game", "deepfake",
        ],
        "boost": [
            "species", "wildlife", "organism", "fauna", "habitat",
            "biodiversity", "ecology", "mammal", "vertebrate",
        ],
        "require_title_or_boost": True,
    },
}
DOMAIN_RULES["animals"] = DOMAIN_RULES["animal"]
DOMAIN_RULES["creatures"] = DOMAIN_RULES["creature"]


def normalize_title_fingerprint(title: str) -> str:
    """跨平台標題正規化指紋（消除大小寫、標點、空白差異）"""
    clean = re.sub(r'[^a-zA-Z0-9]', '', title.lower()).strip()
    return clean[:50]


def extract_arxiv_id(url_or_id: str) -> str:
    text = url_or_id.strip()
    match = ARXIV_ID_RE.search(text)
    if match:
        return match.group(1)
    return text


def parse_words(user_input: str) -> list[str]:
    return [w.strip() for w in user_input.split() if w.strip()]


def keyword_forms(word: str) -> list[str]:
    w = word.lower()
    forms = {w}
    if not w.endswith("s"):
        forms.add(w + "s")
    if w.endswith("y") and len(w) > 3 and not w.endswith("ey"):
        forms.add(w[:-1] + "ies")
    for alias in KEYWORD_ALIASES.get(w, []):
        forms.add(alias.lower())
    return list(forms)


def contains_whole_word(text: str, word: str) -> bool:
    pattern = re.compile(r"\b" + re.escape(word.lower()) + r"\b", re.IGNORECASE)
    return bool(pattern.search(text))


def entry_matches_keywords(entry, words: list[str]) -> bool:
    title = entry.get("title", "")
    abstract = entry.get("summary", "")
    combined = f"{title} {abstract}"
    for word in words:
        forms = keyword_forms(word)
        if not any(contains_whole_word(combined, form) for form in forms):
            return False
    return True


def domain_adjustment(entry, words: list[str]) -> int:
    title = entry.get("title", "").lower()
    text = (title + " " + entry.get("summary", "")).lower()
    adjustment = 0
    for word in words:
        rule = DOMAIN_RULES.get(word.lower())
        if not rule:
            continue
        if any(bad in title for bad in rule.get("reject_title", [])):
            return -1000
        for good in rule.get("boost", []):
            if good in text:
                adjustment += 8
        if rule.get("require_title_or_boost"):
            has_title = any(contains_whole_word(title, f) for f in keyword_forms(word))
            has_boost = any(b in text for b in rule.get("boost", []))
            if not has_title and not has_boost:
                adjustment -= 500
    return adjustment


def calculate_recency_score(year_str: str) -> int:
    try:
        current_year = datetime.now().year
        year = int(re.search(r'\d{4}', str(year_str)).group(0))
        diff = current_year - year
        if diff <= 1:
            return 20
        elif diff <= 2:
            return 10
        elif diff <= 4:
            return 5
        return 0
    except Exception:
        return 5


# ===================== 1. Semantic Scholar =====================
def search_semantic_scholar(query: str, max_results=8) -> list[dict]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,authors,year,citationCount,url,externalIds,openAccessPdf,isOpenAccess"
    }
    headers = {"User-Agent": USER_AGENT}
    papers = []
    try:
        res = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            for p in data.get("data", []):
                title = p.get("title") or ""
                abstract = p.get("abstract") or ""
                if not title or not abstract:
                    continue
                authors = [a.get("name", "") for a in p.get("authors", []) if a.get("name")]
                year = str(p.get("year") or datetime.now().year)
                citations = p.get("citationCount") or 0
                paper_id = p.get("paperId") or f"s2_{title[:20]}"
                is_oa = p.get("isOpenAccess", False)
                pdf_url = p.get("openAccessPdf", {}).get("url") if p.get("openAccessPdf") else None
                link = pdf_url or p.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"
                papers.append({
                    "source": "Semantic Scholar (權威庫)",
                    "title": title,
                    "summary": abstract,
                    "link": link,
                    "id": f"s2_{paper_id[:16]}",
                    "fingerprint": normalize_title_fingerprint(title),
                    "year": year,
                    "authors": authors,
                    "citations": citations,
                    "is_open_access": bool(is_oa or pdf_url),
                    "venue_name": "",
                    "is_top_journal": False,
                })
    except Exception as e:
        print(f"Semantic Scholar 檢索跳過: {e}", file=sys.stderr)
    return papers


# ===================== 2. CrossRef =====================
def search_crossref(query: str, max_results=6) -> list[dict]:
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": max_results,
        "sort": "relevance",
    }
    headers = {"User-Agent": "PaperFilterBot/3.0 (mailto:paperfilter-bot@example.com)"}
    papers = []
    try:
        res = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            items = res.json().get("message", {}).get("items", [])
            for item in items:
                title_list = item.get("title", [])
                title = title_list[0] if title_list else ""
                raw_abstract = item.get("abstract", "")
                abstract = re.sub(r'<[^>]+>', '', raw_abstract).strip() if raw_abstract else ""
                container = item.get("container-title", [""])[0]
                if not abstract:
                    abstract = f"發表於國際頂級學術期刊: {container}。" if container else ""
                if not title:
                    continue
                doi = item.get("DOI", "")
                is_oa = False
                for license_info in item.get("license", []):
                    u = license_info.get("URL", "").lower()
                    if "creativecommon" in u or "open" in u:
                        is_oa = True
                        break
                link = f"https://doi.org/{doi}" if doi else item.get("URL", "#")
                authors = []
                for a in item.get("author", []):
                    given = a.get("given", "")
                    family = a.get("family", "")
                    authors.append(f"{given} {family}".strip())
                date_parts = item.get("published-print", {}).get("date-parts", []) or item.get("published-online", {}).get("date-parts", [])
                year = str(date_parts[0][0]) if date_parts and date_parts[0] else str(datetime.now().year)
                citations = item.get("is-referenced-by-count", 0)
                source_name = f"CrossRef · {container[:20]}" if container else "CrossRef (學術庫)"
                papers.append({
                    "source": source_name,
                    "title": title,
                    "summary": abstract or f"發表於 {year} 年的學術文獻，標題：{title}",
                    "link": link,
                    "id": f"doi_{doi.replace('/', '_')}" if doi else f"cr_{title[:15]}",
                    "fingerprint": normalize_title_fingerprint(title),
                    "year": year,
                    "authors": authors,
                    "citations": citations,
                    "is_open_access": is_oa,
                    "venue_name": container,
                    "is_top_journal": False,
                })
    except Exception as e:
        print(f"CrossRef 檢索異常: {e}", file=sys.stderr)
    return papers


# ===================== 2.5 OpenAlex =====================
def search_openalex(query: str, max_results=8) -> list[dict]:
    """OpenAlex：免費、無需 API key、學術權威元數據（含期刊/會議、引用數、領域）"""
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per_page": max_results,
        "select": "id,title,abstract_inverted_index,authorships,publication_year,cited_by_count,primary_location,type,open_access",
        "sort": "cited_by_count:desc",
    }
    headers = {"User-Agent": USER_AGENT, "mailto": "paperfilter-bot@example.com"}
    papers = []
    try:
        res = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            for w in data.get("results", []):
                title = (w.get("title") or "").strip()
                if not title:
                    continue
                # 還原摘要
                inv = w.get("abstract_inverted_index")
                abstract = ""
                if inv:
                    pos = []
                    for word, positions in inv.items():
                        for p in positions:
                            pos.append((p, word))
                    pos.sort()
                    abstract = " ".join(w for _, w in pos)
                if not abstract:
                    continue
                authors = []
                for a in w.get("authorships", [])[:10]:
                    name = a.get("author", {}).get("display_name", "")
                    if name:
                        authors.append(name)
                loc = w.get("primary_location") or {}
                src = loc.get("source") or {}
                venue_name = src.get("display_name", "")
                is_oa = bool(w.get("open_access", {}).get("is_oa"))
                link = loc.get("landing_page_url") or w.get("id") or ""
                if not link and venue_name:
                    link = f"https://api.openalex.org/works/{w.get('id','').split('/')[-1]}"
                oa_url = w.get("open_access", {}).get("oa_url")
                if oa_url:
                    link = oa_url
                year = str(w.get("publication_year") or datetime.now().year)
                citations = w.get("cited_by_count", 0) or 0
                work_type = w.get("type", "")
                papers.append({
                    "source": f"OpenAlex · {venue_name[:24]}" if venue_name else "OpenAlex (權威庫)",
                    "title": title,
                    "summary": abstract,
                    "link": link,
                    "id": f"oa_{w.get('id','').split('/')[-1]}",
                    "fingerprint": normalize_title_fingerprint(title),
                    "year": year,
                    "authors": authors,
                    "citations": citations,
                    "is_open_access": is_oa,
                    "venue_name": venue_name,
                    "work_type": work_type,
                    "is_top_journal": False,
                })
    except Exception as e:
        print(f"OpenAlex 檢索異常: {e}", file=sys.stderr)
    return papers


# ===================== 3. PubMed =====================
def search_pubmed(query: str, max_results=6) -> list[dict]:
    papers = []
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="pub_date")
        record = Entrez.read(handle)
        handle.close()
        id_list = record.get("IdList", [])
        if not id_list:
            return papers
        fetch_handle = Entrez.efetch(db="pubmed", id=id_list, retmode="xml")
        records = Entrez.read(fetch_handle)
        fetch_handle.close()
        for article in records.get('PubmedArticle', []):
            medline = article['MedlineCitation']
            title = medline['Article']['ArticleTitle']
            abstract_list = medline['Article'].get('Abstract', {}).get('AbstractText', ['無摘要'])
            abstract = "".join(str(x) for x in abstract_list)
            pmid = str(medline['PMID'])
            pub_date = medline['Article'].get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
            year = pub_date.get('Year', str(datetime.now().year))
            journal_title = medline['Article'].get('Journal', {}).get('Title', 'PubMed')
            author_list = []
            for a in medline['Article'].get('AuthorList', []):
                last = a.get('LastName', '')
                fore = a.get('ForeName', '')
                if last or fore:
                    author_list.append(f"{fore} {last}".strip())
            papers.append({
                "source": f"PubMed ({journal_title[:18]})",
                "title": title,
                "summary": abstract,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "id": f"pmid_{pmid}",
                "fingerprint": normalize_title_fingerprint(title),
                "year": str(year),
                "authors": author_list,
                "citations": 0,
                "is_open_access": True,
                "venue_name": journal_title,
                "is_top_journal": False,
            })
    except Exception as e:
        print(f"PubMed 搜尋異常: {e}", file=sys.stderr)
    return papers


# ===================== 4. arXiv =====================
def fetch_feed(query: str, max_results=6):
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        return feedparser.parse(res.content)
    except Exception:
        return feedparser.FeedParserDict(entries=[])


def search_arxiv_candidates(words: list[str], max_results=6) -> list[dict]:
    tiers = []
    if len(words) == 1:
        w = words[0]
        tiers.append(("title_abs", f"ti:{w} OR abs:{w}"))
    else:
        phrase = " ".join(words)
        tiers.append(("phrase", f'all:"{phrase}"'))
        tiers.append(("title_abs_and", "+AND+".join(f"(ti:{w} OR abs:{w})" for w in words)))
    papers = []
    for tier_name, query in tiers:
        feed = fetch_feed(query, max_results=max_results)
        for entry in feed.entries:
            if not entry_matches_keywords(entry, words):
                continue
            title = entry.title.strip().replace("\n", " ")
            summary_text = entry.summary.strip().replace("\n", " ")
            summary = summary_text[:250] + ("..." if len(summary_text) > 250 else "")
            link = entry.get("link", entry.get("id", ""))
            aid = extract_arxiv_id(link)
            pdf_link = f"https://arxiv.org/pdf/{aid}.pdf" if aid else link
            authors = [a.name for a in entry.get("authors", []) if hasattr(a, "name")]
            pub_year = entry.get("published", str(datetime.now().year))[:4]
            papers.append({
                "source": "arXiv (開源預印本)",
                "title": title,
                "summary": summary,
                "link": pdf_link,
                "id": aid,
                "fingerprint": normalize_title_fingerprint(title),
                "year": pub_year,
                "authors": authors,
                "citations": 0,
                "is_open_access": True,
                "is_top_journal": False,
            })
    return papers


# ===================== 5. 跨庫智慧去重 + 動態模式評分選拔 =====================
def fetch_paper_multi_source(
    user_input: str,
    seen_ids: set[str],
    user_bias: tuple = ({}, {}),
    followed_authors: list[str] = None,
    filter_mode: str = "smart",
    user_id: int = 0,
    generate_summary: bool = True
) -> tuple:
    pos_bias, neg_bias = user_bias
    followed_authors = followed_authors or []
    words = parse_words(user_input)
    if not words:
        return None, None, None, None, False, [], "", "2024", "Academic", False, ""

    # 並行搜尋 5 個資料源（提速）
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(search_semantic_scholar, user_input, 6): "s2",
            executor.submit(search_crossref, user_input, 6): "cr",
            executor.submit(search_pubmed, user_input, 5): "pubmed",
            executor.submit(search_arxiv_candidates, words, 5): "arxiv",
            executor.submit(search_openalex, user_input, 8): "oa",
        }
        s2_list, cr_list, pubmed_list, arxiv_list, oa_list = [], [], [], [], []
        for future in concurrent.futures.as_completed(futures, timeout=10):
            src = futures[future]
            try:
                result = future.result()
                if src == "s2":
                    s2_list = result
                elif src == "cr":
                    cr_list = result
                elif src == "pubmed":
                    pubmed_list = result
                elif src == "arxiv":
                    arxiv_list = result
                elif src == "oa":
                    oa_list = result
            except Exception:
                pass
    raw_list = s2_list + cr_list + pubmed_list + arxiv_list + oa_list

    if not raw_list:
        return None, None, None, None, False, [], "", "2024", "Academic", False, ""

    unique_candidates = []
    seen_fingerprints_in_batch = set()
    for p in raw_list:
        fp = p.get("fingerprint") or normalize_title_fingerprint(p["title"])
        if fp in seen_fingerprints_in_batch:
            continue
        seen_fingerprints_in_batch.add(fp)
        unique_candidates.append(p)

    all_candidates = []
    for p in unique_candidates:
        title = p["title"]
        summary = p["summary"]
        authors = p.get("authors", [])
        citations = p.get("citations", 0)
        is_oa = p.get("is_open_access", False)
        is_top = p.get("is_top_journal", False)
        venue_name = p.get("venue_name") or ""
        source_label = p.get("source", "")
        # 真實權威等級（取代虛假 is_top_journal）
        tier = None
        if academic_tiers:
            tier = academic_tiers.get_venue_tier(venue_name) or (
                None if not academic_tiers.is_preprint(source_label) else None
            )
        is_preprint = academic_tiers.is_preprint(source_label) if academic_tiers else ("arxiv" in source_label.lower())
        text_lower = (title + " " + summary).lower()

        match_score = 0
        for w in words:
            forms = keyword_forms(w)
            if any(contains_whole_word(title, f) for f in forms):
                match_score += 30
            elif any(contains_whole_word(summary, f) for f in forms):
                match_score += 12

        recency_score = calculate_recency_score(p.get("year", "2020"))

        # 真實可信度加權（基於期刊/會議等級）
        tier_bonus = {
            "TOP": 60, "CCF-A": 50, "CCF-B": 35, "CCF-C": 25,
            "Q1": 40,
        }.get(tier, 0)
        if is_preprint:
            tier_bonus = -10  # 預印本不懲罰太重，但權威性較低

        mode_score = 0
        if filter_mode == "top_tier":
            citation_weight = min(int(citations) // 3, 50)
            mode_score = citation_weight + tier_bonus
        elif filter_mode == "free_only":
            citation_weight = min(int(citations) // 10, 15)
            oa_bonus = 30 if is_oa else -20
            mode_score = citation_weight + oa_bonus
        else:
            citation_weight = min(int(citations) // 5, 30)
            oa_bonus = 10 if is_oa else 0
            mode_score = citation_weight + tier_bonus + oa_bonus

        pref_score = 0
        for w, weight in pos_bias.items():
            if w in text_lower:
                pref_score += weight * 2
        for w, weight in neg_bias.items():
            if w in text_lower:
                pref_score -= weight * 3

        domain_score = domain_adjustment({"title": title, "summary": summary}, words)

        author_bonus = 0
        if followed_authors:
            for auth in authors:
                for target_auth in followed_authors:
                    if target_auth.lower() in auth.lower():
                        author_bonus += 50

        total_score = match_score + recency_score + mode_score + pref_score + domain_score + author_bonus
        all_candidates.append({
            "score": total_score,
            "title": title,
            "summary": summary,
            "link": p["link"],
            "id": str(p["id"]),
            "fingerprint": p.get("fingerprint"),
            "source": p["source"],
            "venue_name": venue_name,
            "tier": tier,
            "is_preprint": is_preprint,
            "year": p["year"],
            "authors": authors,
            "citations": citations,
            "is_open_access": is_oa,
            "is_top_journal": bool(tier in ("TOP", "CCF-A", "CCF-B", "Q1")),
        })

    all_candidates.sort(key=lambda x: x["score"], reverse=True)
    unseen_candidates = [
        c for c in all_candidates
        if c["id"] not in seen_ids and (c.get("fingerprint") not in seen_ids)
    ]

    if unseen_candidates:
        selected = unseen_candidates[0]
        already_seen = False
    else:
        selected = all_candidates[0]
        already_seen = True

    fp = selected.get("fingerprint", "")
    cached = db.get_cached_ai(fp) if fp else None
    if generate_summary and cached and cached[0]:
        ai_summary = cached[0]
    elif generate_summary:
        ai_summary = generate_ai_summary(selected["summary"], user_id=user_id)
        if fp:
            db.set_cached_ai(fp, summary=ai_summary)
    else:
        ai_summary = ""

    return (
        selected["title"],
        ai_summary,
        selected["link"],
        selected["id"],
        already_seen,
        selected["authors"],
        selected["summary"],
        selected["year"],
        selected["source"],
        selected.get("is_open_access", False),
        selected.get("fingerprint", ""),
        selected.get("venue_name", ""),
        selected.get("tier"),
        selected.get("is_preprint", False),
        selected.get("citations", 0),
    )


# ===================== AI 摘要、深度導讀與分級調度 =====================
def _user_lang(user_id: int) -> str:
    if user_id:
        try:
            return db.get_user_lang(user_id) or "en"
        except Exception:
            pass
    return "en"


def _lang_instruction(user_id: int) -> str:
    lang = _user_lang(user_id)
    return {
        "zh_hant": "請以繁體中文",
        "zh_hans": "請以簡體中文",
        "en": "Please respond in English",
        "ja": "日本語で回答してください",
    }.get(lang, "Please respond in English")


def _invoke_ai(prompt: str, system_prompt: str = "你是專業學術論文導讀專家。", tier: str = "free", temperature: float = 0.3) -> str:
    """統一使用 GPT-4o-mini 進行 AI 呼叫（低成本、高速度）"""
    openai_key = os.getenv("OPENAI_API_KEY")

    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI gpt-4o-mini 調用失敗: {e}", file=sys.stderr)

    return ""


def generate_ai_summary(text: str, user_id: int = 0) -> str:
    lang = "en"
    if user_id:
        try:
            lang = db.get_user_lang(user_id) or "en"
        except Exception:
            lang = "en"
    lang_prompts = {
        "zh_hant": "請用繁體中文以 2 到 3 句話精準總結這篇論文的核心研究問題與關鍵突破成果。",
        "zh_hans": "请用简体中文以 2 到 3 句话精准总结这篇论文的核心研究问题与关键突破成果。",
        "en": "In 2-3 sentences, concisely summarize this paper's core research question and key breakthrough findings. Respond in English.",
        "ja": "この論文の核心的な研究問題と重要な成果を2〜3文で簡潔にまとめてください。日本語で回答してください。",
    }
    system_prompt = f"你是專業學術論文導讀助手。{lang_prompts.get(lang, lang_prompts['en'])}"
    res = _invoke_ai(
        prompt=text[:1800],
        system_prompt=system_prompt,
        tier="free",
        temperature=0.3
    )
    return res if res else (text[:250] + "..." if len(text) > 250 else text)


def generate_deep_analysis(title: str, text: str, fingerprint: str = None, user_id: int = 0) -> str:
    """Deep analysis from title + abstract only. Never claim to have read the full paper."""
    tier = db.get_user_tier(user_id).get("tier", "free") if user_id else "free"
    
    if fingerprint:
        cached = db.get_cached_ai(fingerprint)
        if cached and cached[1]:
            return cached[1]

    lang = "en"
    if user_id:
        try:
            lang = db.get_user_lang(user_id) or "en"
        except Exception:
            lang = "en"

    lang_instruction = {
        "zh_hant": "請以繁體中文",
        "zh_hans": "请以简体中文",
        "en": "Please respond in English",
        "ja": "日本語で回答してください",
    }.get(lang, "Please respond in English")

    prompt = f"""Please perform a deep structured analysis of the following academic paper based on the title and abstract below.

Analysis guidelines:
- Base your analysis ONLY on the provided title and abstract. You may supplement with general domain knowledge to explain context, but clearly separate the authors' claims from your own background knowledge.
- If specific numbers or metrics are mentioned in the abstract, cite them. If the abstract does not provide specific quantitative results, describe the qualitative findings instead.
- Do not invent numbers, metrics, sample sizes, p-values, accuracies, or benchmark scores that are not present in the title or abstract. Never fabricate citations.
- This analysis is for quick understanding only; readers should verify details against the original paper.

Title: {title}
Abstract & Key Content: {text}

{lang_instruction}, following this structure with specific details (keep Emoji and HTML bold tags <b>):

🎯 <b>【Research Motivation & Pain Points】</b>
(Detail the existing challenges, technical bottlenecks, or theoretical gaps this research aims to solve)

⚙️ <b>【Core Methods & Technical Innovation】</b>
(Break down the proposed system architecture, mathematical models, algorithms, or experimental design)

📊 <b>【Key Findings & Breakthrough Data】</b>
(Specific quantitative metrics, benchmark improvements, and major experimental conclusions — only if stated in the abstract)

⚠️ <b>【Limitations & Future Directions】</b>
(Limitations identified by authors or objectively existing, and promising research directions)
"""
    report = _invoke_ai(
        prompt=prompt,
        system_prompt="You are a senior reviewer at top international academic journals. Provide a thorough, structured analysis based on the provided title and abstract only. Use your domain knowledge to explain context and significance, but clearly distinguish between what the paper claims and your general knowledge. Do not invent numbers. Avoid vague statements.",
        tier=tier,
        temperature=0.2
    )

    if not report:
        report = "❌ 尚未設定 AI API Key，無法依據標題與摘要生成深度導讀。"
    elif fingerprint:
        db.set_cached_ai(fingerprint, deep_report=report)

    return report


def generate_bibtex_str(title: str, authors: list[str], year: str, link: str, source: str) -> str:
    clean_title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
    first_author = authors[0].split()[-1].lower() if authors else "researcher"
    short_title = re.sub(r'[^a-zA-Z0-9]', '', clean_title.split()[0] if clean_title.split() else "paper")
    cite_key = f"{first_author}{year}_{short_title}"
    author_field = " and ".join(authors) if authors else "Unknown Authors"
    bibtex = (
        f"@article{{{cite_key},\n"
        f"  title = {{{clean_title}}},\n"
        f"  author = {{{author_field}}},\n"
        f"  year = {{{year}}},\n"
        f"  journal = {{{source}}},\n"
        f"  url = {{{link}}}\n"
        f"}}"
    )
    return bibtex


# ===================== 【Pro 專屬】跨文獻 RAG 智慧問答 =====================
def chat_with_user_library(user_id: int, query: str, papers: list) -> str:
    """
    【Pro 核心功能】跨文獻 RAG 智慧問答
    針對用戶收藏的論文進行多維度交叉問答，並標註具體引用依據
    """
    if not papers:
        return "❌ 您的文獻庫中尚無論文。請先搜尋並點擊【☁️ 歸檔到雲端】收藏論文後再來提問！"
    
    tier = db.get_user_tier(user_id).get("tier", "free")
    lang = _lang_instruction(user_id)
    
    # 只使用呼叫端傳入的論文，最多 8 篇以控制成本
    selected = papers[:8]
    context_blocks = []
    for i, p in enumerate(selected, 1):
        auth_str = ", ".join(p.get("authors", [])[:3])
        context_blocks.append(
            f"[文獻 {i}] 《{p.get('title', '')}》\n"
            f"作者: {auth_str} ({p.get('year', '')}) | 來源: {p.get('source', '')}\n"
            f"摘要與關鍵細節: {p.get('summary', '')}\n"
        )
    papers_context = "\n---\n".join(context_blocks)
    
    prompt = f"""你是一名世界頂尖的學術研究顧問。用戶正在針對他文獻庫中傳入的 {len(selected)} 篇論文提出具體研究問題。

【用戶提問】：
{query}

【用戶的文獻庫內容】：
{papers_context}

【回答要求】：
1. 必須以 {lang} 客觀、嚴謹、具備深度學術洞察力回答。
2. 進行跨論文的橫向結構化對比（例如：方法論異同、實驗數據優劣、各自面臨的挑戰）。
3. 每提到具體數據或結論，必須在句尾精確標註引用出處，例如：[文獻 1] 或 (作者, 年份)。
4. 若文獻中未提及該資訊，請誠實說明並給出合理的研究方向推論。
5. 若用戶提問與文獻庫內容無關，請禮貌提醒：「此問題超出文獻庫範圍，建議使用 /chat 針對您收藏的論文提問。」

【智能引導】：
若用戶提問過於模糊（例如只寫「幫我分析」、「比較一下」），請：
- 先根據文獻庫內容，主動提供 2-3 個具體的分析方向供用戶選擇
- 例如：「您的問題較為廣泛，以下是建議的分析方向：\n① 方法論異同比較\n② 實驗結果排名\n③ 研究限制缺口\n請選擇一個方向，或具體描述您想了解的面向。」

【回應格式】：
- 開頭先用 1-2 句話總結核心發現
- 接著提供結構化對比（表格或條列式）
- 結尾標註「📚 以上分析基於您傳入的 {len(selected)} 篇文獻」
"""
    answer = _invoke_ai(
        prompt=prompt,
        system_prompt="你是嚴謹的學術論文評審專家與領域知識圖譜專家，擅長在多篇文獻之間建立對比矩陣與批判性論證。你的回答必須嚴格限定在用戶提供的文獻範圍內，不可編造不存在的論文或數據。",
        tier=tier,
        temperature=0.3
    )

    return answer if answer else "❌ AI 生成解答時發生異常，請確認 API Key 設定。"


# ===================== 文獻綜述、研究缺口、趨勢分析、匯出 =====================
def generate_literature_review(user_id: int, papers: list) -> str:
    """使用 Pro/Free 分級 AI 生成文獻綜述"""
    if not papers:
        return "❌ 沒有論文可供生成文獻綜述。"
    
    tier = db.get_user_tier(user_id).get("tier", "free")
    lang = _lang_instruction(user_id)
    papers_text = ""
    for i, p in enumerate(papers[:20], 1):
        authors_str = ", ".join(p.get("authors", [])[:3]) if p.get("authors") else "Unknown"
        papers_text += f"{i}. 《{p.get('title', '')}》\n   作者: {authors_str} ({p.get('year', '')})\n   摘要: {str(p.get('summary', ''))[:200]}\n\n"

    prompt = f"""以下是用戶收藏的 {len(papers)} 篇學術論文，請撰寫一份結構嚴謹、具備發表情境的學術文獻綜述草稿（{lang}）：
{papers_text}

This is a draft. Verify citations against originals.

請按以下 5 大段落輸出（保留 HTML 標籤 <b>）：
1. <b>【研究背景與主題概述】</b>（闡述該領域核心意義）
2. <b>【主流技術路徑與代表性工作】</b>（逐條深入剖析各文獻貢獻）
3. <b>【跨論文方法論橫向對比】</b>（比較優缺點、適用場景與複雜度）
4. <b>【學界共同共識與最新突破】</b>
5. <b>【現存研究缺口與未來研究倡議】</b>

請保持頂級期刊綜述風格，引用論文時使用（作者, 年份）格式。Do not invent papers or numbers that are not in the provided abstracts."""

    review = _invoke_ai(
        prompt=prompt,
        system_prompt="你是專業的學術文獻綜述撰寫專家，擅長整合多篇論文並生成結構嚴謹的縱向綜述。",
        tier=tier,
        temperature=0.3
    )

    if not review:
        review = "### 📚 文獻清單\n\n"
        for p in papers:
            authors_str = ", ".join(p.get("authors", [])[:3]) if p.get("authors") else "Unknown"
            review += f"- **{p.get('title', '')}** （{authors_str}, {p.get('year', '')}）\n"

    return review


def analyze_research_gaps(user_id: int, papers: list) -> str:
    """使用 Pro/Free 分級 AI 分析研究缺口"""
    if not papers:
        return "❌ 沒有論文可供分析研究缺口。"
    
    tier = db.get_user_tier(user_id).get("tier", "free")
    lang = _lang_instruction(user_id)
    papers_text = ""
    for i, p in enumerate(papers[:15], 1):
        papers_text += f"{i}. 《{p.get('title', '')}》 ({p.get('year', '')})\n   摘要: {str(p.get('summary', ''))[:200]}\n\n"

    prompt = f"""以下是 {len(papers)} 篇學術論文，請深度分析這些研究中尚未解決的關鍵研究缺口（{lang}）：
{papers_text}

請輸出：
1. <b>現有研究所覆蓋之理論與應用範疇</b>
2. <b>五大核心研究盲點與缺口</b>（每個附帶具體技術說明）
3. <b>最具創新潛力的 3-5 個未來研究課題建議</b>
4. <b>現有文獻在數據集、評測基準或方法論上的共同不足</b>
"""
    gaps = _invoke_ai(
        prompt=prompt,
        system_prompt="你是頂尖學術研究顧問，專門幫助博士生與研究員發掘高價值研究缺口並規劃未來論文方向。",
        tier=tier,
        temperature=0.3
    )

    return gaps if gaps else "❌ 缺口分析生成失敗。"


def analyze_research_trends(user_id: int, topic: str, years: int = 5) -> dict:
    """分析最近的研究趨勢"""
    cache_key = f"trend_{topic}_{years}"
    cached = db.get_trend_cache(cache_key)
    if cached:
        return cached

    tier = db.get_user_tier(user_id).get("tier", "free") if user_id else "free"
    lang = _lang_instruction(user_id)

    try:
        recent_papers = search_semantic_scholar(topic, max_results=10)
        recent_papers += search_arxiv_candidates(parse_words(topic), max_results=8)
    except Exception:
        recent_papers = []

    papers_summary = ""
    year_counter: dict[str, int] = {}
    for p in recent_papers[:15]:
        y = str(p.get("year", ""))
        if y:
            year_counter[y] = year_counter.get(y, 0) + 1
        papers_summary += f"- {p.get('title', '')} ({y})\n"

    trends: dict = {
        "topic": topic,
        "total_papers_found": len(recent_papers),
        "year_distribution": year_counter,
        "recent_publications": [p.get("title", "") for p in recent_papers[:5]],
        "ai_analysis": ""
    }

    if recent_papers:
        prompt = f"""以下是關於「{topic}」的近期學術論文：
{papers_summary}

請用 {lang} 深度分析這個領域的研究趨勢：
1. 主流研究方向與演進
2. 近年爆發的新興方法/技術
3. 預測未來 2-3 年的關鍵突破點

請精簡扼要，條列式呈現。"""
        ai_res = _invoke_ai(
            prompt=prompt,
            system_prompt="你是國際學術趨勢分析專家。",
            tier=tier,
            temperature=0.3
        )
        trends["ai_analysis"] = ai_res or f"近期共找到 {len(recent_papers)} 篇相關論文，發表年份分佈：{year_counter}"

    try:
        db.set_trend_cache(cache_key, topic, trends)
    except Exception:
        pass

    return trends


def export_papers(papers: list, format_type: str) -> str:
    """匯出論文清單（支援 RIS / BibTeX / CSV）"""
    if not papers:
        return "❌ 沒有論文可供匯出。"
    if format_type not in ["RIS", "BibTeX", "CSV"]:
        return f"❌ 不支援的格式：{format_type}，請使用 RIS、BibTeX 或 CSV。"

    output = ""
    if format_type == "BibTeX":
        entries = []
        for p in papers:
            bib = p.get("bibtex", "")
            if bib:
                entries.append(bib)
            else:
                entries.append(generate_bibtex_str(
                    title=p.get("title", "Unknown"),
                    authors=p.get("authors", []),
                    year=str(p.get("year", datetime.now().year)),
                    link=p.get("link", ""),
                    source=p.get("source", "Unknown Source")
                ))
        output = "\n\n".join(entries)
    elif format_type == "RIS":
        lines = []
        for p in papers:
            lines.append("TY  - JOUR")
            lines.append(f"TI  - {p.get('title', '')}")
            for author in p.get("authors", []):
                lines.append(f"AU  - {author}")
            lines.append(f"PY  - {p.get('year', '')}")
            lines.append(f"JO  - {p.get('source', '')}")
            lines.append(f"UR  - {p.get('link', '')}")
            ab = p.get("summary", "")
            if ab:
                lines.append(f"AB  - {ab[:500]}")
            lines.append("ER  - ")
            lines.append("")
        output = "\n".join(lines)
    elif format_type == "CSV":
        import csv
        import io
        sio = io.StringIO()
        writer = csv.writer(sio)
        writer.writerow(["Title", "Authors", "Year", "Source", "Link", "Abstract"])
        for p in papers:
            authors_str = "; ".join(p.get("authors", []))
            writer.writerow([
                p.get("title", ""),
                authors_str,
                p.get("year", ""),
                p.get("source", ""),
                p.get("link", ""),
                str(p.get("summary", ""))[:300]
            ])
        output = sio.getvalue()

    return output
