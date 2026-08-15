"""判斷訊息是閒聊、指令還是論文搜尋。"""

import re

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")

_GREETING_REPLY = (
    "你好！我是<b>論文管家</b> 🤖\n\n"
    "我專門幫你找論文、摘要、歸檔到雲端，"
    "不是像 ChatGPT 那種自由聊天機器人。\n\n"
    "• 完整說明：<code>/help</code>"
)

CHITCHAT_RESPONSES: dict[str, str] = {
    "你好": _GREETING_REPLY,
    "嗨": _GREETING_REPLY,
    "哈囉": _GREETING_REPLY,
    "hello": _GREETING_REPLY,
    "hi": _GREETING_REPLY,
    "hey": _GREETING_REPLY,
    "謝謝": "不客氣！有需要再輸入關鍵字搜尋論文，或打 <code>/help</code> 看說明。",
    "谢谢": "不客氣！有需要再輸入關鍵字搜尋論文，或打 <code>/help</code> 看說明。",
    "感謝": "不客氣！有需要再輸入關鍵字搜尋論文，或打 <code>/help</code> 看說明。",
    "thanks": "You're welcome! Type a keyword to search papers, or <code>/help</code> for guide.",
    "thank you": "You're welcome! Type a keyword to search papers, or <code>/help</code> for guide.",
}

# 常見中文關鍵字 → arXiv 英文搜尋詞
CN_TO_EN: dict[str, str] = {
    "蒼蠅": "fly",
    "苍蝇": "fly",
    "果蠅": "drosophila",
    "心理學": "psychology",
    "心理学": "psychology",
    "心理": "psychology",
    "金融": "financial",
    "財經": "finance",
    "财经": "finance",
    "動物": "animal",
    "动物": "animal",
    "人工智慧": "artificial intelligence",
    "人工智能": "artificial intelligence",
    "機器學習": "machine learning",
    "机器学习": "machine learning",
    "太空": "space",
    "宇宙": "cosmology",
    "量子": "quantum",
    "生物": "biology",
    "生態": "ecology",
    "醫學": "medicine",
    "医学": "medicine",
    "神經": "neuroscience",
    "神经": "neuroscience",
    "電腦": "computer",
    "电脑": "computer",
    "網路": "network",
    "网络": "network",
}

SEARCH_PREFIXES = ("搜尋 ", "搜索 ", "search ")

NOT_A_SEARCH_HINT = (
    "我是<b>論文管家</b>，專門搜尋論文，不能像一般聊天機器人自由對話。\n\n"
    "<b>你可以：</b>\n"
    "• 輸入英文關鍵字，例如 <code>space</code>\n"
    "• 打 <code>/help</code> 看完整功能\n"
    "• 打 <code>我的資料夾</code> 管理分類"
)


def cn_hint(original: str) -> str:
    return (
        f"論文平臺以<b>英文</b>為主，「{original}」建議改用英文關鍵字。\n\n"
        "範例：\n"
        "• 太空 → <code>space</code> 或 <code>cosmology</code>\n"
        "• 心理學 → <code>psychology</code>\n"
        "• 金融 → <code>financial</code>\n\n"
        "也可輸入 <code>搜尋 financial</code>"
    )


def is_chitchat(text: str) -> bool:
    key = text.strip().lower()
    return key in {k.lower() for k in CHITCHAT_RESPONSES}


def get_chitchat_response(text: str) -> str:
    key = text.strip().lower()
    for k, v in CHITCHAT_RESPONSES.items():
        if k.lower() == key:
            return v
    return _GREETING_REPLY


def is_likely_chat_not_search(text: str) -> bool:
    """長句、問句等不像搜尋關鍵字。"""
    t = text.strip()
    if t.endswith("?") or t.endswith("？"):
        return True
    if len(t) > 25 and CJK_RE.search(t):
        return True
    chat_phrases = [
        "可以聊天",
        "你能做什麼",
        "你会做什么",
        "你是誰",
        "你是谁",
        "怎麼用",
        "怎么用",
    ]
    return any(p in t for p in chat_phrases)


def strip_search_prefix(text: str) -> tuple[str, bool]:
    t = text.strip()
    for prefix in SEARCH_PREFIXES:
        if t.lower().startswith(prefix.lower()):
            return t[len(prefix):].strip(), True
    return t, False


def resolve_search_query(text: str) -> tuple[str | None, str, bool]:
    """
    解析搜尋詞。
    回傳 (arxiv_query, display_label, had_explicit_prefix)
    arxiv_query 為 None 表示無法翻譯、應提示用戶。
    """
    raw, explicit = strip_search_prefix(text)
    if not raw:
        return None, text, explicit

    if raw in CN_TO_EN:
        en = CN_TO_EN[raw]
        return en, raw, explicit

    if not CJK_RE.search(raw):
        return raw, raw, explicit

    parts = raw.split()
    translated = [CN_TO_EN.get(p, p) for p in parts]
    query = " ".join(translated)

    if CJK_RE.search(query):
        return None, raw, explicit

    return query, raw, explicit
