import os
import sys
import json
import threading
import telebot
from telebot import types
from flask import Flask, request, abort
from dotenv import load_dotenv

load_dotenv()

import paper_search
import classifier
from OAuthur2 import drive_manager
from database import db
from i18n import get_text, detect_user_lang, MESSAGES

# ===================== Bot 初始化 =====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 10000))

if not TELEGRAM_TOKEN:
    print("❌ 缺少 TELEGRAM_TOKEN！", file=sys.stderr)
    sys.exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ===================== 工具函數 =====================

def _get_lang(user_id: int, tg_lang_code: str = None) -> str:
    saved = db.get_user_lang(user_id)
    if saved:
        return saved
    return detect_user_lang(tg_lang_code)

def _t(user_id: int, key: str, tg_lang_code: str = None, **kwargs) -> str:
    lang = _get_lang(user_id, tg_lang_code)
    return get_text(lang, key, **kwargs)

def fetch_user_papers(user_id: int) -> list:
    """從資料庫取得使用者收藏的論文"""
    return db.get_user_library(user_id)

def _build_folder_keyboard(user_id: int, paper_id: str, lang: str) -> types.InlineKeyboardMarkup:
    """建立歸檔資料夾選擇鍵盤"""
    custom_cats = db.get_user_categories(user_id)
    default_cats = MESSAGES.get(lang, MESSAGES["en"]).get("default_categories", [
        "Artificial Intelligence", "Bio & Life Sciences", "General Science", "Human Genetics"
    ])
    categories = custom_cats if custom_cats else default_cats

    markup = types.InlineKeyboardMarkup(row_width=2)
    for cat in categories[:8]:
        markup.add(types.InlineKeyboardButton(
            f"📁 {cat}",
            callback_data=f"archive|{paper_id[:40]}|{cat[:30]}"
        ))
    markup.add(types.InlineKeyboardButton("⏭ 略過不歸檔", callback_data=f"archive|{paper_id[:40]}|略過"))
    return markup

def _send_paper_card(chat_id: int, user_id: int, title: str, ai_summary: str,
                     link: str, paper_id: str, already_seen: bool,
                     authors: list, raw_summary: str, year: str,
                     source: str, is_open_access: bool, fingerprint: str,
                     lang: str):
    """發送論文卡片訊息"""
    authors_str = ", ".join(authors[:3]) if authors else "Unknown"
    if len(authors) > 3:
        authors_str += f" 等 {len(authors)} 位"

    seen_badge = "👁 [已看過]" if already_seen else ""
    oa_badge = "🟢 OA" if is_open_access else ""

    text = (
        f"📄 <b>{title}</b> {seen_badge}\n\n"
        f"👥 {authors_str} | 📅 {year} | 🗂 {source} {oa_badge}\n\n"
        f"🧠 <b>AI 導讀：</b>\n{ai_summary}\n\n"
        f"🔗 <a href__='{link}'>{_t(user_id, 'read_paper')}</a>"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "btn_deep"), callback_data=f"deep|{fingerprint[:40]}"),
        types.InlineKeyboardButton(_t(user_id, "btn_seen"), callback_data=f"seen|{paper_id[:40]}"),
    )
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "btn_skip"), callback_data=f"skip|{paper_id[:40]}"),
    )
    if is_open_access:
        markup.add(types.InlineKeyboardButton(_t(user_id, "btn_oa"), url=link))
    else:
        markup.add(types.InlineKeyboardButton(_t(user_id, "btn_doi"), url=link))

    # 歸檔按鈕
    markup.add(types.InlineKeyboardButton("☁️ 歸檔到 Google Drive", callback_data=f"choose_folder|{paper_id[:40]}"))

    bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)


# ===================== 指令處理 =====================

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "研究者"
    lang = _get_lang(user_id, message.from_user.language_code)
    welcome_text = _t(user_id, "welcome", tg_lang_code=message.from_user.language_code, name=name)
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['help'])
def handle_help(message):
    user_id = message.from_user.id
    bot.reply_to(message, _t(user_id, "help", tg_lang_code=message.from_user.language_code))


@bot.message_handler(commands=['mode'])
def handle_mode(message):
    user_id = message.from_user.id
    current_mode = db.get_filter_mode(user_id)
    lang = _get_lang(user_id, message.from_user.language_code)

    mode_names = {
        "top_tier": _t(user_id, "mode_top"),
        "smart": _t(user_id, "mode_smart"),
        "free_only": _t(user_id, "mode_free"),
    }
    current_display = mode_names.get(current_mode, current_mode)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "mode_top"), callback_data="set_mode|top_tier"),
        types.InlineKeyboardButton(_t(user_id, "mode_smart"), callback_data="set_mode|smart"),
        types.InlineKeyboardButton(_t(user_id, "mode_free"), callback_data="set_mode|free_only"),
    )
    bot.reply_to(message, _t(user_id, "mode_title", current=current_display), reply_markup=markup)


@bot.message_handler(commands=['lang'])
def handle_lang(message):
    user_id = message.from_user.id
    lang = _get_lang(user_id, message.from_user.language_code)
    lang_names = {"en": "English", "zh_hant": "繁體中文", "zh_hans": "简体中文", "ja": "日本語"}
    current_display = lang_names.get(lang, lang)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇺🇸 English", callback_data="set_lang|en"),
        types.InlineKeyboardButton("🇹🇼 繁體中文", callback_data="set_lang|zh_hant"),
        types.InlineKeyboardButton("🇨🇳 简体中文", callback_data="set_lang|zh_hans"),
        types.InlineKeyboardButton("🇯🇵 日本語", callback_data="set_lang|ja"),
    )
    bot.reply_to(message, _t(user_id, "lang_switch_title", current=current_display), reply_markup=markup)


@bot.message_handler(commands=['follow'])
def handle_follow(message):
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "請輸入學者名稱，例如：<code>/follow Yann LeCun</code>")
        return
    author_name = parts[1].strip()
    db.add_followed_author(user_id, author_name)
    bot.reply_to(message, _t(user_id, "follow_success", name=author_name))


@bot.message_handler(commands=['unfollow'])
def handle_unfollow(message):
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "請輸入要取消追蹤的學者名稱。")
        return
    author_name = parts[1].strip()
    success = db.remove_followed_author(user_id, author_name)
    if success:
        bot.reply_to(message, _t(user_id, "unfollow_success", name=author_name))
    else:
        bot.reply_to(message, _t(user_id, "unfollow_failed", name=author_name))


@bot.message_handler(commands=['following'])
def handle_following(message):
    user_id = message.from_user.id
    authors = db.get_followed_authors(user_id)
    if not authors:
        bot.reply_to(message, _t(user_id, "no_following"))
    else:
        authors_list = "\n".join(f"• <code>{a}</code>" for a in authors)
        bot.reply_to(message, _t(user_id, "following_list", list=authors_list))


@bot.message_handler(commands=['drive'])
def handle_drive(message):
    user_id = message.from_user.id
    token = db.get_token(user_id)
    if token:
        bot.reply_to(message, "✅ 您的 Google Drive 已連結！可以直接歸檔論文。")
    else:
        auth_url = drive_manager.get_auth_url(user_id)
        if auth_url:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔗 授權 Google Drive", url=auth_url))
            bot.reply_to(message, "請點擊下方按鈕授權 Google Drive 存取：", reply_markup=markup)
        else:
            bot.reply_to(message, "❌ Google OAuth 設定未完成，請聯繫管理員配置 GOOGLE_CLIENT_SECRETS_JSON。")


@bot.message_handler(commands=['search'])
def handle_search_command(message):
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "請輸入關鍵字，例如：<code>/search CRISPR</code>")
        return
    query = parts[1].strip()
    _do_search(message, user_id, query)


@bot.message_handler(commands=['deep'])
def handle_deep_command(message):
    user_id = message.from_user.id
    bot.reply_to(message, "請先搜尋論文，再點擊論文卡片下方的 [🔍 深度導讀] 按鈕。")


@bot.message_handler(commands=['review'])
def handle_review(message):
    user_id = message.from_user.id
    allowed, err_msg = db.check_quota(user_id, "litreview")
    if not allowed:
        bot.reply_to(message, f"⚠️ {err_msg}")
        return
    papers = fetch_user_papers(user_id)
    if not papers:
        bot.reply_to(message, "您尚未收藏任何論文。請先搜尋並歸檔論文後再使用。")
        return
    bot.reply_to(message, f"🧠 正在為您的 {len(papers)} 篇論文生成文獻綜述，請稍候...")
    review = paper_search.generate_literature_review(user_id, papers)
    db.increment_usage(user_id, "litreview")
    # Telegram 訊息限制 4096 字元
    if len(review) > 4000:
        for i in range(0, len(review), 4000):
            bot.send_message(message.chat.id, review[i:i+4000])
    else:
        bot.send_message(message.chat.id, review)


@bot.message_handler(commands=['gap'])
def handle_gap(message):
    user_id = message.from_user.id
    allowed, err_msg = db.check_quota(user_id, "gap_analysis")
    if not allowed:
        bot.reply_to(message, f"⚠️ {err_msg}")
        return
    papers = fetch_user_papers(user_id)
    if not papers:
        bot.reply_to(message, "您尚未收藏任何論文。請先搜尋並歸檔論文後再使用。")
        return
    bot.reply_to(message, f"🔍 正在分析 {len(papers)} 篇論文的研究缺口，請稍候...")
    gaps = paper_search.analyze_research_gaps(user_id, papers)
    db.increment_usage(user_id, "gap_analysis")
    if len(gaps) > 4000:
        for i in range(0, len(gaps), 4000):
            bot.send_message(message.chat.id, gaps[i:i+4000])
    else:
        bot.send_message(message.chat.id, gaps)


@bot.message_handler(commands=['trend'])
def handle_trend(message):
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else "machine learning"
    bot.reply_to(message, f"📈 正在分析「{topic}」的研究趨勢，請稍候...")
    trends = paper_search.analyze_research_trends(user_id, topic)
    year_dist = trends.get("year_distribution", {})
    year_str = "  ".join(f"{y}年:{c}篇" for y, c in sorted(year_dist.items(), reverse=True)[:5])
    ai_analysis = trends.get("ai_analysis", "")
    result = (
        f"📊 <b>「{topic}」研究趨勢分析</b>\n\n"
        f"📚 找到相關論文：{trends.get('total_papers_found', 0)} 篇\n"
        f"📅 發表年份分佈：{year_str}\n\n"
    )
    if ai_analysis:
        result += f"🤖 <b>AI 趨勢解析：</b>\n{ai_analysis}"
    bot.send_message(message.chat.id, result)


@bot.message_handler(commands=['export'])
def handle_export(message):
    user_id = message.from_user.id
    allowed, err_msg = db.check_quota(user_id, "export")
    if not allowed:
        bot.reply_to(message, f"⚠️ {err_msg}")
        return
    papers = fetch_user_papers(user_id)
    if not papers:
        bot.reply_to(message, "您尚未收藏任何論文。")
        return
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("📄 BibTeX", callback_data="export_fmt|BibTeX"),
        types.InlineKeyboardButton("📋 RIS", callback_data="export_fmt|RIS"),
        types.InlineKeyboardButton("📊 CSV", callback_data="export_fmt|CSV"),
    )
    bot.reply_to(message, f"您共有 {len(papers)} 篇論文，請選擇匯出格式：", reply_markup=markup)


# ===================== 文字訊息處理 =====================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()
    lang = _get_lang(user_id, message.from_user.language_code)

    # 新增資料夾
    if text.startswith("新增 ") or text.startswith("Add ") or text.startswith("追加 "):
        folder_name = text.split(" ", 1)[1].strip() if " " in text else ""
        if folder_name:
            db.add_user_category(user_id, folder_name)
            bot.reply_to(message, _t(user_id, "folder_added", name=folder_name))
        return

    # 改名資料夾
    if (" -> " in text or " → " in text) and (text.startswith("改名 ") or text.startswith("Rename ")):
        sep = " -> " if " -> " in text else " → "
        parts_raw = text.split(" ", 1)
        if len(parts_raw) > 1:
            rename_part = parts_raw[1]
            if sep in rename_part:
                old_name, new_name = rename_part.split(sep, 1)
                old_name = old_name.strip()
                new_name = new_name.strip()
                db.rename_user_category(user_id, old_name, new_name)
                drive_manager.rename_folder(user_id, old_name, new_name)
                bot.reply_to(message, _t(user_id, "folder_renamed", old=old_name, new=new_name))
        return

    # 刪除資料夾
    if text.startswith("刪除 ") or text.startswith("Delete ") or text.startswith("削除 "):
        folder_name = text.split(" ", 1)[1].strip() if " " in text else ""
        cats = db.get_user_categories(user_id)
        if folder_name in cats:
            db.delete_user_category(user_id, folder_name)
            drive_manager.mark_folder_deleted(user_id, folder_name)
            bot.reply_to(message, _t(user_id, "folder_deleted", name=folder_name))
        else:
            bot.reply_to(message, _t(user_id, "folder_not_found", name=folder_name))
        return

    # 查詢資料夾
    if text in ("我的資料夾", "My folders", "マイフォルダ", "我的文件夹"):
        cats = db.get_user_categories(user_id)
        default_cats = MESSAGES.get(lang, MESSAGES["en"]).get("default_categories", [])
        all_cats = cats if cats else default_cats
        if all_cats:
            cats_list = "\n".join(f"• {c}" for c in all_cats)
            bot.reply_to(message, _t(user_id, "my_folders", list=cats_list))
        else:
            bot.reply_to(message, _t(user_id, "no_custom_folders"))
        return

    # 閒聊判斷
    if classifier.is_chitchat(text):
        bot.reply_to(message, classifier.get_chitchat_response(text))
        return

    if classifier.is_likely_chat_not_search(text):
        bot.reply_to(message, classifier.NOT_A_SEARCH_HINT)
        return

    # 解析搜尋關鍵字
    query, raw, explicit = classifier.resolve_search_query(text)

    if query is None:
        if classifier.CJK_RE.search(raw):
            bot.reply_to(message, classifier.cn_hint(raw))
        else:
            bot.reply_to(message, classifier.NOT_A_SEARCH_HINT)
        return

    _do_search(message, user_id, query)


def _do_search(message, user_id: int, query: str):
    """執行論文搜尋並發送結果"""
    lang = _get_lang(user_id, message.from_user.language_code)

    # 配額檢查
    allowed, err_msg = db.check_quota(user_id, "search")
    if not allowed:
        bot.reply_to(message, f"⚠️ {err_msg}")
        return

    loading_msg = bot.reply_to(message, _t(user_id, "search_intro", query=query))

    try:
        seen_ids = db.get_seen_papers(user_id)
        bias = db.get_user_bias(user_id)
        user_bias = (bias.get("positive", {}), bias.get("negative", {}))
        followed_authors = db.get_followed_authors(user_id)
        filter_mode = db.get_filter_mode(user_id)

        result = paper_search.fetch_paper_multi_source(
            user_input=query,
            seen_ids=seen_ids,
            user_bias=user_bias,
            followed_authors=followed_authors,
            filter_mode=filter_mode
        )

        title, ai_summary, link, paper_id, already_seen, authors, raw_summary, year, source, is_open_access, fingerprint = result

        if not title:
            bot.edit_message_text(
                _t(user_id, "not_found", query=query),
                chat_id=loading_msg.chat.id,
                message_id=loading_msg.message_id
            )
            return

        db.increment_usage(user_id, "search")

        try:
            bot.delete_message(loading_msg.chat.id, loading_msg.message_id)
        except Exception:
            pass

        _send_paper_card(
            chat_id=message.chat.id,
            user_id=user_id,
            title=title,
            ai_summary=ai_summary,
            link=link,
            paper_id=paper_id,
            already_seen=already_seen,
            authors=authors,
            raw_summary=raw_summary,
            year=year,
            source=source,
            is_open_access=is_open_access,
            fingerprint=fingerprint,
            lang=lang
        )

    except Exception as e:
        print(f"搜尋錯誤: {e}", file=sys.stderr)
        try:
            bot.edit_message_text(
                _t(user_id, "search_error"),
                chat_id=loading_msg.chat.id,
                message_id=loading_msg.message_id
            )
        except Exception:
            bot.reply_to(message, _t(user_id, "search_error"))


# ===================== Callback 處理 =====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data

    try:
        # 設定語言
        if data.startswith("set_lang|"):
            lang_code = data.split("|", 1)[1]
            db.set_user_lang(user_id, lang_code)
            lang_names = {"en": "English", "zh_hant": "繁體中文", "zh_hans": "简体中文", "ja": "日本語"}
            bot.answer_callback_query(call.id, f"✅ 語言已切換為 {lang_names.get(lang_code, lang_code)}")
            bot.edit_message_text(
                _t(user_id, "lang_switched"),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            return

        # 設定模式
        if data.startswith("set_mode|"):
            mode = data.split("|", 1)[1]
            db.set_filter_mode(user_id, mode)
            mode_names = {
                "top_tier": _t(user_id, "mode_top"),
                "smart": _t(user_id, "mode_smart"),
                "free_only": _t(user_id, "mode_free"),
            }
            mode_display = mode_names.get(mode, mode)
            bot.answer_callback_query(call.id, f"✅ 已切換為 {mode_display}")
            bot.edit_message_text(
                _t(user_id, "mode_switched", mode=mode_display),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            return

        # 深度導讀
        if data.startswith("deep|"):
            fingerprint = data.split("|", 1)[1]
            allowed, err_msg = db.check_quota(user_id, "deep")
            if not allowed:
                bot.answer_callback_query(call.id, f"⚠️ {err_msg}", show_alert=True)
                return

            bot.answer_callback_query(call.id, _t(user_id, "deep_processing"))
            bot.send_message(call.message.chat.id, _t(user_id, "deep_processing"))

            # 從快取或論文庫取得資訊
            cached = db.get_cached_ai(fingerprint) if fingerprint else None
            if cached and cached[1]:
                deep_report = cached[1]
                bibtex_str = cached[2] or ""
            else:
                # 從論文庫搜尋
                papers = db.get_user_library(user_id)
                paper = next((p for p in papers if p.get("fingerprint") == fingerprint), None)
                if not paper:
                    bot.send_message(call.message.chat.id, "❌ 找不到論文資料，請重新搜尋。")
                    return
                deep_report = paper_search.generate_deep_analysis(
                    title=paper.get("title", ""),
                    text=paper.get("summary", ""),
                    fingerprint=fingerprint
                )
                bibtex_str = paper.get("bibtex", "") or paper_search.generate_bibtex_str(
                    title=paper.get("title", ""),
                    authors=paper.get("authors", []),
                    year=paper.get("year", ""),
                    link=paper.get("link", ""),
                    source=paper.get("source", "")
                )

            db.increment_usage(user_id, "deep")

            # 發送深度報告
            report_msg = f"{_t(user_id, 'deep_header')}\n\n{deep_report}"
            if len(report_msg) > 4000:
                for i in range(0, len(report_msg), 4000):
                    bot.send_message(call.message.chat.id, report_msg[i:i+4000])
            else:
                bot.send_message(call.message.chat.id, report_msg)

            # 發送 BibTeX
            if bibtex_str:
                bot.send_message(
                    call.message.chat.id,
                    f"{_t(user_id, 'bibtex_header')}\n<pre>{bibtex_str}</pre>"
                )
            return

        # 標記已看
        if data.startswith("seen|"):
            paper_id = data.split("|", 1)[1]
            db.add_seen_paper(user_id, paper_id)
            # 更新偏好 (正向)
            papers = db.get_user_library(user_id)
            paper = next((p for p in papers if p.get("id") == paper_id or p.get("fingerprint") == paper_id), None)
            if paper:
                keywords = paper_search.parse_words(paper.get("title", ""))[:5]
                db.update_user_bias(user_id, keywords, is_positive=True)
                title_display = paper.get("title", paper_id)
            else:
                title_display = paper_id
            bot.answer_callback_query(call.id, "👁 已標記為已讀")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, _t(user_id, "mark_seen", title=title_display[:100]))
            return

        # 略過
        if data.startswith("skip|"):
            paper_id = data.split("|", 1)[1]
            db.add_seen_paper(user_id, paper_id)
            papers = db.get_user_library(user_id)
            paper = next((p for p in papers if p.get("id") == paper_id or p.get("fingerprint") == paper_id), None)
            if paper:
                keywords = paper_search.parse_words(paper.get("title", ""))[:5]
                db.update_user_bias(user_id, keywords, is_positive=False)
                title_display = paper.get("title", paper_id)
            else:
                title_display = paper_id
            bot.answer_callback_query(call.id, "❌ 已略過")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, _t(user_id, "mark_skip", title=title_display[:100]))
            return

        # 選擇歸檔資料夾
        if data.startswith("choose_folder|"):
            paper_id = data.split("|", 1)[1]
            lang = _get_lang(user_id, call.from_user.language_code)
            markup = _build_folder_keyboard(user_id, paper_id, lang)
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "📁 請選擇要歸檔的資料夾：", reply_markup=markup)
            return

        # 執行歸檔
        if data.startswith("archive|"):
            parts = data.split("|")
            if len(parts) < 3:
                bot.answer_callback_query(call.id, _t(user_id, "invalid_button"), show_alert=True)
                return

            paper_id = parts[1]
            folder_name = parts[2]

            if folder_name == "略過":
                bot.answer_callback_query(call.id, "⏭ 已略過歸檔")
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                return

            # 找論文資料
            papers = db.get_user_library(user_id)
            paper = next((p for p in papers if str(p.get("id", ""))[:40] == paper_id or str(p.get("fingerprint", ""))[:40] == paper_id), None)

            if not paper:
                bot.answer_callback_query(call.id, "❌ 找不到論文資料", show_alert=True)
                return

            bot.answer_callback_query(call.id, f"☁️ 歸檔中...")

            # 生成 BibTeX
            bibtex_str = paper.get("bibtex", "") or paper_search.generate_bibtex_str(
                title=paper.get("title", ""),
                authors=paper.get("authors", []),
                year=paper.get("year", ""),
                link=paper.get("link", ""),
                source=paper.get("source", "")
            )

            # 同步 BibTeX 到資料庫
            if bibtex_str and not paper.get("bibtex"):
                paper["bibtex"] = bibtex_str
                db.add_paper_to_library(user_id, paper)

            success, result = drive_manager.archive_paper(
                user_id=user_id,
                folder_name=folder_name,
                title=paper.get("title", ""),
                summary=paper.get("summary", ""),
                link=paper.get("link", ""),
                bibtex=bibtex_str
            )

            if success:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                bot.send_message(
                    call.message.chat.id,
                    _t(user_id, "archive_success", folder=folder_name, title=paper.get("title", "")[:80])
                )
            else:
                if "尚未完成 Google 授權" in result:
                    auth_url = drive_manager.get_auth_url(user_id)
                    if auth_url:
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton("🔗 授權 Google Drive", url=auth_url))
                        bot.send_message(call.message.chat.id, "請先授權 Google Drive：", reply_markup=markup)
                    else:
                        bot.send_message(call.message.chat.id, "❌ Google OAuth 未設定。")
                else:
                    bot.send_message(call.message.chat.id, _t(user_id, "archive_failed", detail=result))
            return

        # 匯出格式選擇
        if data.startswith("export_fmt|"):
            fmt = data.split("|", 1)[1]
            papers = fetch_user_papers(user_id)
            if not papers:
                bot.answer_callback_query(call.id, "沒有論文可匯出", show_alert=True)
                return

            bot.answer_callback_query(call.id, f"📄 正在生成 {fmt} 格式...")
            export_content = paper_search.export_papers(papers, fmt)
            db.increment_usage(user_id, "export")

            if len(export_content) > 4000:
                # 分段發送
                bot.send_message(call.message.chat.id, f"📄 <b>{fmt} 匯出結果</b>（共 {len(papers)} 篇）：")
                for i in range(0, len(export_content), 3800):
                    bot.send_message(call.message.chat.id, f"<pre>{export_content[i:i+3800]}</pre>")
            else:
                bot.send_message(call.message.chat.id, f"📄 <b>{fmt} 匯出結果</b>：\n\n<pre>{export_content}</pre>")
            return

        bot.answer_callback_query(call.id, _t(user_id, "invalid_button"))

    except Exception as e:
        print(f"Callback 錯誤: {e}", file=sys.stderr)
        try:
            bot.answer_callback_query(call.id, "⚠️ 發生錯誤，請稍後再試。")
        except Exception:
            pass


# ===================== OAuth2 回呼 =====================

@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")
    state = request.args.get("state")  # user_id
    error = request.args.get("error")

    if error:
        return f"<h3>授權失敗：{error}</h3>", 400
    if not code or not state:
        return "<h3>缺少必要參數</h3>", 400

    try:
        user_id = int(state)
    except ValueError:
        return "<h3>無效的 state 參數</h3>", 400

    success = drive_manager.exchange_code(user_id, code)
    if success:
        try:
            bot.send_message(user_id, "✅ Google Drive 授權成功！現在可以歸檔論文了。")
        except Exception:
            pass
        return "<h3>✅ Google Drive 授權成功！請回到 Telegram 繼續使用。</h3>"
    else:
        return "<h3>❌ 授權失敗，請重試。</h3>", 500


# ===================== Webhook / Polling 啟動 =====================

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    abort(403)


@app.route("/")
def index():
    return "PaperFilterBot is running! 🤖", 200


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    if WEBHOOK_URL:
        # Webhook 模式（雲端部署）
        webhook_url = f"{WEBHOOK_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
        bot.remove_webhook()
        import time
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook 模式啟動：{webhook_url}", file=sys.stderr)
        app.run(host="0.0.0.0", port=PORT)
    else:
        # Polling 模式（本機測試）
        print("✅ Polling 模式啟動（本機測試）...", file=sys.stderr)
        bot.remove_webhook()
        bot.infinity_polling(timeout=20, long_polling_timeout=15)