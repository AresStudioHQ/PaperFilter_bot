"""arXiv 論文搜尋：標題優先 + 領域過濾 + 防誤配"""

import re
import sys
import urllib.parse
import os
import feedparser
import requests

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
        print(f"arXiv 請求失敗 ({search_query}): {exc}", file=sys.stderr)
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

Entrez.email = os.getenv("ENTREZ_EMAIL", "paperfilter-bot@example.com")
openai.api_key = os.getenv("OPENAI_API_KEY")

# 1. PubMed 搜尋 (生物、昆蟲、醫學)
def search_pubmed(query: str, max_results=5) -> list[dict]:
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

        for article in records['PubmedArticle']:
            title = article['MedlineCitation']['Article']['ArticleTitle']
            abstract_list = article['MedlineCitation']['Article'].get('Abstract', {}).get('AbstractText', ['無摘要'])
            abstract = "".join(str(x) for x in abstract_list)
            pmid = article['MedlineCitation']['PMID']
            papers.append({
                "source": "PubMed",
                "title": title,
                "summary": abstract,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "id": str(pmid)
            })
    except Exception as e:
        print(f"PubMed 搜尋失敗: {e}", file=sys.stderr)
    return papers

# 2. AI 摘要導讀
def generate_ai_summary(text: str) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        return text[:250] + "..." if len(text) > 250 else text
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是學術論文導讀助手。請用繁體中文以 2 句話總結這篇論文的核心研究與成果。"},
                {"role": "user", "content": text[:1500]}
            ],
            timeout=8
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return text[:250] + "..."

# 3. 升級版論文搜尋（整合多來源 + 動態偏好排序）
def fetch_paper_multi_source(user_input: str, seen_raw: set[str], user_bias: tuple = ({}, {})) -> tuple:
    pos_bias, neg_bias = user_bias
    words = parse_words(user_input)
    if not words:
        return None, None, None, False

    candidates = []

    # (A) arXiv 搜尋
    for tier_name, query in build_tiered_queries(words):
        feed = fetch_feed(query, max_results=10)
        for entry in feed.entries:
            if not entry_matches_keywords(entry, words):
                continue
            base_score = score_entry(entry, words)
            t, s, l = entry_to_result(entry)
            
            # 動態偏好評分
            pref_score = 0
            for w, weight in pos_bias.items():
                if w in t.lower(): pref_score += weight * 2
            for w, weight in neg_bias.items():
                if w in t.lower(): pref_score -= weight * 3

            candidates.append({
                "score": base_score + pref_score,
                "title": t,
                "summary": s,
                "link": l,
                "id": extract_arxiv_id(l)
            })

    # (B) 若包含生物、昆蟲等關鍵字，同步搜 PubMed
    if any(w.lower() in BIOLOGY_KEYWORDS for w in words):
        pubmed_results = search_pubmed(user_input, max_results=5)
        for p in pubmed_results:
            candidates.append({
                "score": 25, 
                "title": p["title"],
                "summary": p["summary"],
                "link": p["link"],
                "id": p["id"]
            })

    if not candidates:
        return None, None, None, False

    candidates.sort(key=lambda x: x["score"], reverse=True)

    seen_ids = {extract_arxiv_id(s) for s in seen_raw}
    unseen = [c for c in candidates if c["id"] not in seen_ids]
    selected = unseen[0] if unseen else candidates[0]
    already_seen = selected["id"] in seen_ids

    # 產生 AI 摘要
    ai_summary = generate_ai_summary(selected["summary"])

    return selected["title"], ai_summary, selected["link"], already_seen