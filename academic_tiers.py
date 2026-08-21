"""學術期刊 / 會議 權威分級資料庫 (CCF / 中科院分區 / 領域頂會)

設計原則：
- 只有「真正頂級」的期刊與會議才標記為頂級，避免虛假權威
- 資料來源：CCF-A/B/C 推薦目錄、中科院分區（Q1/Q2）、領域頂會共識
- 使用者可信任標記；未收錄的期刊一律標記為「一般期刊」，不誇大
"""

# 頂級期刊 / 會議 → 等級
# 等級代碼：
#   "CCF-A"  計算機領域 CCF-A 類頂會/頂刊
#   "CCF-B"  CCF-B 類
#   "CCF-C"  CCF-C 類
#   "Q1"     中科院/SCImago Q1 頂級期刊
#   "TOP"    自然科學/醫學公認頂刊 (Nature/Science/Cell 系列)
#   "PRESTIGIOUS" 領域內高聲望期刊（非 CCF 但公認優良）
VENUE_TIERS: dict[str, str] = {}

def _add(venue: str, tier: str):
    VENUE_TIERS[venue.strip().lower()] = tier

# ===================== 頂級綜合/科學期刊 =====================
for v in [
    "Nature", "Science", "Cell", "Nature Medicine", "Nature Biotechnology",
    "Nature Methods", "Nature Genetics", "Nature Neuroscience", "Nature Physics",
    "Nature Chemistry", "Nature Materials", "Nature Communications", "Science Advances",
    "Proceedings of the National Academy of Sciences", "PNAS",
    "The Lancet", "The New England Journal of Medicine", "NEJM",
    "JAMA", "Journal of the American Chemical Society", "JACS",
    "Chemical Reviews", "Chemical Society Reviews", "Angewandte Chemie",
    "Physical Review Letters", "PRL", "Reviews of Modern Physics",
]:
    _add(v, "TOP")

# ===================== 計算機 / AI / ML 頂會 (CCF-A) =====================
for v in [
    "NeurIPS", "NIPS", "ICML", "ICLR", "AAAI", "CVPR", "ICCV", "ECCV",
    "SIGGRAPH", "KDD", "SIGKDD", "ACL", "EMNLP", "NAACL", "SIGIR", "WWW",
    "SIGMOD", "VLDB", "ICDE", "SIGCOMM", "INFOCOM", "OSDI", "SOSP",
    "USENIX Security", "IEEE Symposium on Security and Privacy", "CCS",
    "CRYPTO", "EUROCRYPT", "S&P", "ISCA", "MICRO", "HPCA", "ASPLOS",
    "PLDI", "POPL", "OOPSLA", "ICSE", "FSE", "AAAI", "IJCAI",
]:
    _add(v, "CCF-A")

# ===================== 計算機 頂刊 (CCF-A/B) =====================
for v in [
    "IEEE Transactions on Pattern Analysis and Machine Intelligence", "TPAMI",
    "Journal of Machine Learning Research", "JMLR",
    "IEEE Transactions on Software Engineering", "TSE",
    "ACM Computing Surveys", "CSUR", "IEEE Transactions on Computers",
    "IEEE Transactions on Knowledge and Data Engineering", "TKDE",
    "IEEE Transactions on Image Processing", "TIP",
    "IEEE Transactions on Neural Networks and Learning Systems", "TNNLS",
    "ACM Transactions on Graphics", "TOG", "IEEE Transactions on Information Theory",
    "IEEE Transactions on Medical Imaging", "TMI",
]:
    _add(v, "CCF-A")

for v in [
    "ACM Transactions on Computer Systems", "TOCS",
    "IEEE Transactions on Parallel and Distributed Systems", "TPDS",
    "IEEE Transactions on Multimedia", "TMM", "Software: Practice and Experience",
    "Computer Communications", "IEEE Transactions on Cybernetics",
    "IEEE Transactions on Systems, Man, and Cybernetics", "IEEE Access",
    "Neural Networks", "Pattern Recognition", "Computers & Security",
]:
    _add(v, "CCF-B")

# ===================== 生命科學 / 醫學 (Q1) =====================
for v in [
    "Cell Metabolism", "Molecular Cell", "Developmental Cell", "Cancer Cell",
    "Immunity", "Neuron", "Cell Stem Cell", "Gastroenterology", "Hepatology",
    "Blood", "Circulation", "European Heart Journal", "Journal of Clinical Investigation",
    "Autophagy", "Nucleic Acids Research", "Genome Biology", "PLoS Biology",
    "Cell Reports", "eLife", "Cell Systems", "Molecular Systems Biology",
    "American Journal of Human Genetics", "Genome Research", "Bioinformatics",
    "Trends in Neurosciences", "Trends in Genetics", "Trends in Biotechnology",
    "Annual Review of Biochemistry", "Annual Review of Immunology",
    "Diabetes Care", "Journal of Clinical Oncology", "Lancet Oncology",
    "Gut", "Brain", "Alzheimer's & Dementia", "Cell Host & Microbe",
    "Nature Immunology", "Nature Neuroscience", "Molecular Psychiatry",
]:
    _add(v, "Q1")

# ===================== 物理 / 數學 / 材料 (Q1) =====================
for v in [
    "Nature Physics", "Nature Materials", "Nature Nanotechnology",
    "Advanced Materials", "Nano Letters", "ACS Nano", "Materials Today",
    "Physical Review X", "Nature Communications", "Science Advances",
    "Journal of the American Chemical Society", "Angewandte Chemie International Edition",
    "Energy & Environmental Science", "Advanced Energy Materials",
    "Inventiones Mathematicae", "Annals of Mathematics", "Acta Mathematica",
]:
    _add(v, "Q1")

# ===================== 經濟 / 社科 / 心理 (Q1) =====================
for v in [
    "American Economic Review", "Quarterly Journal of Economics", "Econometrica",
    "Journal of Political Economy", "Review of Economic Studies",
    "Journal of Finance", "Journal of Financial Economics",
    "Annual Review of Psychology", "Psychological Bulletin", "Psychological Review",
    "Journal of Personality and Social Psychology", "American Psychologist",
    "Nature Human Behaviour", "Cognition", "Trends in Cognitive Sciences",
    "American Journal of Sociology", "American Sociological Review",
]:
    _add(v, "Q1")

# ===================== 通用預印本平台 =====================
PREPRINT_SOURCES = {
    "arxiv": "arXiv",
    "biorxiv": "bioRxiv",
    "medrxiv": "medRxiv",
    "ssrn": "SSRN",
    "chemrxiv": "ChemRxiv",
    "preprints": "Preprints",
}


def normalize_venue(name: str) -> str:
    if not name:
        return ""
    return name.strip().lower()


def get_venue_tier(venue_name: str) -> str | None:
    """回傳期刊/會議等級，未收錄則回傳 None（不誇大為頂級）"""
    if not venue_name:
        return None
    key = normalize_venue(venue_name)
    # 直接匹配
    if key in VENUE_TIERS:
        return VENUE_TIERS[key]
    # 包含匹配（處理 "Proceedings of the ... " 前綴）
    for known, tier in VENUE_TIERS.items():
        if known in key or key in known:
            return tier
    return None


def is_preprint(source_label: str) -> bool:
    if not source_label:
        return False
    s = source_label.lower()
    return any(p in s for p in ("arxiv", "biorxiv", "medrxiv", "preprint", "ssrn", "chemrxiv"))


def credibility_badge(venue_name: str, source_label: str) -> tuple[str, str]:
    """
    回傳 (徽章emoji, 等級文字)
    例如 ("🏆", "CCF-A") 或 ("📄", "Peer-reviewed") 或 ("🔴", "Preprint")
    """
    if is_preprint(source_label) or is_preprint(venue_name or ""):
        return "🔴", "Preprint (未經 peer review)"
    tier = get_venue_tier(venue_name)
    if tier == "TOP":
        return "🏆", "頂級期刊 (Nature/Science/Cell 級)"
    if tier == "CCF-A":
        return "🥇", "CCF-A / 領域頂會頂刊"
    if tier == "CCF-B":
        return "🥈", "CCF-B / 優良期刊"
    if tier == "CCF-C":
        return "🥉", "CCF-C / 認可期刊"
    if tier == "Q1":
        return "📈", "Q1 / 高影響力期刊"
    # 有期刊名但不在清單 → 誠實標記
    if venue_name:
        return "📄", "Peer-reviewed (一般期刊)"
    return "📄", "Peer-reviewed"
