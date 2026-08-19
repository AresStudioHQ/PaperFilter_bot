"""arXiv 論文搜尋：標題優先 + 領域過濾 + 防誤配"""

import re
import sys
import urllib.parse
import os
import feedparser
import requests; import feedparser

ARXIV_API = "https://export.arxiv.org/api/query"
USER_AGENT = "PaperFilterBot/1.0 (academic-paper-filter; mailto:paperfilter-bot@example.com)"
ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
REQUEST_TIMEOUT = 12

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

# 易混淆關鍵字：排除動畫/3D 等誤配（animal ≠ animation）
DOMAIN_RULES: dict[str, dict] = {
    "animal": {
        "reject_title": [
            "animation",
            "animated",
            "facial",
            "talking head",
            "talking face",
            "3d",
            "mesh",
            "rendering",
            "avatar",
            "blendshape",
            "graphics",
            "videogame",
            "game engine",
            "motion capture",
            "mocap",
            "neural radiance",
            "diffusion model",
            "generative model",
            "computer vision",
            "deepfake",
        ],
        "boost": [
            "species",
            "wildlife",
            "zoology",
            "mammal",
            "insect",
            "behavior",
            "behaviour",
            "ecology",
            "organism",
            "drosophila",
            "vertebrate",
            "fauna",
            "birds",
            "fish",
            "mouse",
            "mice",
            "rats",
            "livestock",
            "veterinary",
            "zoological",
            "genome",
            "biodiversity",
        ],
        "require_title_or_boost": True,
    },
    "creature": {
        "reject_title": [
            "animation",
            "animated",
            "facial",
            "3d",
            "graphics",
            "rendering",
            "videogame",
            "game",
            "deepfake",
        ],
        "boost": [
            "species",
            "wildlife",
            "organism",
            "fauna",
            "habitat",
            "biodiversity",
            "ecology",
            "mammal",
            "vertebrate",
        ],
        "require_title_or_boost": True,
    },
    "creatures": {
        "reject_title": [
            "animation",
            "animated",
            "facial",
            "3d",
            "graphics",
            "rendering",
            "videogame",
            "game",
        ],
        "boost": [
            "species",
            "wildlife",
            "organism",
            "fauna",
            "habitat",
            "biodiversity",
            "ecology",
        ],
        "require_title_or_boost": True,
    },
}

DOMAIN_RULES["animals"] = DOMAIN_RULES["animal"]

BIOLOGY_KEYWORDS = frozenset(
    {
        "animal",
        "animals",
        "creature",
        "creatures",
        "biology",
        "ecology",
        "zoology",
        "wildlife",
        "insect",
        "mammal",
        "fly",
        "drosophila",
    }
)


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
            has_title = any(
                contains_whole_word(title, f) for f in keyword_forms(word)
            )
            has_boost = any(b in text for b in rule.get("boost", []))
            if not has_title and not has_boost:
                adjustment -= 500

    return adjustment


def score_entry(entry, words: list[str]) -> int:
    title = entry.get("title", "")
    abstract = entry.get("summary", "")
    score = 0

    for word in words:
        forms = keyword_forms(word)
        title_hit = any(contains_whole_word(title, f) for f in forms)
        abstract_hit = any(contains_whole_word(abstract, f) for f in forms)

        if title_hit:
            score += 30
        elif abstract_hit:
            score += 6

    return score + domain_adjustment(entry, words)


def build_tiered_queries(words: list[str]) -> list[tuple[str, str]]:
    tiers: list[tuple[str, str]] = []

    if len(words) == 1:
        w = words[0]
        wl = w.lower()

        if wl in BIOLOGY_KEYWORDS:
            tiers.append(
                (
                    "bio_title",
                    f"(ti:{w} OR abs:{w}) AND (cat:q-bio.* OR cat:physics.bio-ph)",
                )
            )

        tiers.append(("title_only", f"ti:{w}"))
        tiers.append(("title_abs", f"ti:{w} OR abs:{w}"))
    else:
        phrase = " ".join(words)
        tiers.append(("phrase", f'all:"{phrase}"'))
        tiers.append(
            ("title_abs_and", "+AND+".join(f"(ti:{w} OR abs:{w})" for w in words))
        )

    return tiers


def fetch_feed(search_query: str, max_results: int = 40) -> feedparser.FeedParserDict:
    params = {
        "search_query": search_query,
        "max_results": str(max_results),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return feedparser.parse(response.content)
    except Exception as exc:
        print(f"arXiv 請求失敗，查詢: {search_query} 錯誤: {exc}", file=sys.stderr)
        return feedparser.parse("")


def entry_to_result(entry) -> tuple[str, str, str]:
    title = entry.title.strip().replace("\n", " ")
    summary_text = entry.summary.strip().replace("\n", " ")
    summary = summary_text[:250] + ("..." if len(summary_text) > 250 else "")
    link = entry.get("link", entry.get("id", ""))
    return title, summary, link


# ===================== 以下為新增的多來源與 AI 升級區 =====================
from Bio import Entrez
import openai

# ===================== 多來源搜尋 (最新年份) + 現代 OpenAI 導讀 =====================
import os
import sys
from Bio import Entrez
from openai import OpenAI

Entrez.email = os.getenv("ENTREZ_EMAIL", "paperfilter-bot@example.com")

# 1. 現代 OpenAI 摘要函式 (支援 OpenAI v1.0+)
def generate_ai_summary(text: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return text[:250] + "..." if len(text) > 250 else text

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是專業學術論文導讀助手。請用繁體中文以 2 到 3 句話精準總結這篇論文的核心研究與成果。"},
                {"role": "user", "content": text[:1500]}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI 呼叫失敗，改用截斷原文: {e}", file=sys.stderr)
        return text[:250] + "..."

# 2. PubMed 最新生物醫學論文搜尋
from datetime import datetime

# 1. 統一計算「年份新鮮度加分」
def calculate_recency_score(year_str: str) -> int:
    try:
        current_year = datetime.now().year
        year = int(re.search(r'\d{4}', str(year_str)).group(0))
        diff = current_year - year
        if diff <= 1:   # 2024~2026 年最新論文
            return 20
        elif diff <= 2: # 2023 年
            return 10
        elif diff <= 4: # 2021~2022 年
            return 5
        return 0
    except Exception:
        return 5 # 若抓不到年份給予基礎分

# 2. 搜尋 PubMed (生物/醫學/自然科學)
def search_pubmed(query: str, max_results=8) -> list[dict]:
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
            
            # 解析年份
            pub_date = medline['Article'].get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
            year = pub_date.get('Year', str(datetime.now().year))

            papers.append({
                "source": "PubMed",
                "title": title,
                "summary": abstract,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "id": f"pmid_{pmid}",
                "year": year
            })
    except Exception as e:
        print(f"PubMed 搜尋異常: {e}", file=sys.stderr)
    return papers

# 3. 搜尋 arXiv (資工/AI/物理/數學/計量金融)
def search_arxiv_candidates(words: list[str], max_results=8) -> list[dict]:
    papers = []
    # 使用 submittedDate（依提交日期排序，保證抓到最新）
    for tier_name, query in build_tiered_queries(words):
        feed = fetch_feed(query, max_results=max_results)
        for entry in feed.entries:
            if not entry_matches_keywords(entry, words):
                continue
            t, s, l = entry_to_result(entry)
            pub_year = entry.get("published", str(datetime.now().year))[:4]
            aid = extract_arxiv_id(l)
            papers.append({
                "source": "arXiv",
                "title": t,
                "summary": s,
                "link": l,
                "id": aid,
                "year": pub_year,
                "raw_entry": entry
            })
    return papers

# 4. 跨平台評分與最強論文選拔引擎 (具備嚴格去重機制)

def fetch_paper_multi_source(user_input: str, seen_ids: set[str], user_bias: tuple = ({}, {})) -> tuple:
    pos_bias, neg_bias = user_bias
    words = parse_words(user_input)
    if not words:
        return None, None, None, None, False

    all_candidates = []

    # 🚀 同時向兩大平台發起檢索
    pubmed_list = search_pubmed(user_input, max_results=10)
    arxiv_list = search_arxiv_candidates(words, max_results=10)
    raw_list = pubmed_list + arxiv_list

    if not raw_list:
        return None, None, None, None, False

    for p in raw_list:
        title = p["title"]
        summary = p["summary"]
        text_lower = (title + " " + summary).lower()

        # (1) 關鍵字精準度評分
        match_score = 0
        for w in words:
            forms = keyword_forms(w)
            if any(contains_whole_word(title, f) for f in forms):
                match_score += 25
            elif any(contains_whole_word(summary, f) for f in forms):
                match_score += 10

        # (2) 年份新鮮度加分
        recency_score = calculate_recency_score(p.get("year", "2020"))

        # (3) 個人偏好動態加減分
        pref_score = 0
        for w, weight in pos_bias.items():
            if w in text_lower:
                pref_score += weight * 2
        for w, weight in neg_bias.items():
            if w in text_lower:
                pref_score -= weight * 3

        # (4) 領域防誤配過濾
        domain_score = domain_adjustment({"title": title, "summary": summary}, words)

        total_score = match_score + recency_score + pref_score + domain_score

        all_candidates.append({
            "score": total_score,
            "title": title,
            "summary": summary,
            "link": p["link"],
            "id": str(p["id"]),
            "source": p["source"],
            "year": p["year"]
        })

    # 依分數排序
    all_candidates.sort(key=lambda x: x["score"], reverse=True)

    # 🔒 嚴格過濾看過的論文
    unseen_candidates = [c for c in all_candidates if c["id"] not in seen_ids]
    
    if unseen_candidates:
        selected = unseen_candidates[0]
        already_seen = False
    else:
        # 如果全部都看過了，才重複推薦分數最高的
        selected = all_candidates[0]
        already_seen = True

    # 調用 GPT-4o-mini 生成地道繁中 2 句摘要
    ai_summary = generate_ai_summary(selected["summary"])

    return selected["title"], ai_summary, selected["link"], selected["id"], already_seen

fetch_paper_by_keyword = fetch_paper_multi_source