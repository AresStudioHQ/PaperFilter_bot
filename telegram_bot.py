import os
import json
import random
import sys
import asyncio
import html
from database import db
from OAthur2 import drive_manager, SKIPPED_FOLDER_NAME
from paper_search import fetch_paper_multi_source, extract_arxiv_id
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from telegram_bot.OAthur2 import get_drive, SKIPPED_FOLDER_NAME, SKIPPED_KEY
from telegram_bot.paper_search import fetch_paper_by_keyword, extract_arxiv_id
from message_router import (
    is_chitchat,
    get_chitchat_response,
    is_likely_chat_not_search,
    resolve_search_query,
    NOT_A_SEARCH_HINT,
    cn_hint,
)

# ===================== 1. 基礎設定 =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
SEEN_FILE = "seen_papers.txt"
CONFIG_FILE = "categories.json"


def require_token() -> str:
    if not TOKEN:
        print("錯誤：請在環境變數設定 TELEGRAM_TOKEN", file=sys.stderr)
        sys.exit(1)
    return TOKEN


# ===================== 2. 資料與檔案處理函式 =====================
def load_categories() -> dict[str, str]:
    if not os.path.exists(CONFIG_FILE):
        default = {
            "cat_1": "生物生態",
            "cat_2": "人工智慧",
            "cat_3": "金融市場",
            "cat_4": "綜合科學",
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_categories(categories: dict[str, str]):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=4)


def load_seen_papers() -> set[str]:
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return {extract_arxiv_id(line) for line in f if line.strip()}


def save_seen_paper(link: str):
    arxiv_id = extract_arxiv_id(link)
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(arxiv_id + "\n")


def save_to_folder_local(folder_name: str, title: str, link: str, summary: str = ""):
    """本機備份（雲端失敗時仍保留紀錄）。"""
    os.makedirs(folder_name, exist_ok=True)
    file_path = os.path.join(folder_name, "saved_papers.txt")
    with open(file_path, "a", encoding="utf-8") as f:
        block = f"標題: {title}\n連結: {link}\n"
        if summary:
            block += f"摘要: {summary}\n"
        block += "-" * 50 + "\n"
        f.write(block)


def build_category_keyboard(categories: dict[str, str]) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(name, callback_data=cid) for cid, name in categories.items()]
    ]
    keyboard.append([InlineKeyboardButton("❌ 沒興趣", callback_data="skip")])
    return InlineKeyboardMarkup(keyboard)


async def archive_paper(
    folder_key: str,
    folder_name: str,
    title: str,
    summary: str,
    link: str,
) -> str:
    """歸檔到雲端 + 本機備份，回傳給用戶的狀態訊息片段。"""
    drive = get_drive()
    save_to_folder_local(folder_name, title, link, summary)

    if not drive.enabled:
        return "（僅本機備份，雲端尚未設定）"

    ok, detail = drive.archive_paper(folder_key, folder_name, title, summary, link)
    if ok:
        return "☁️ 已同步至 Google Drive"
    return f"⚠️ 雲端同步失敗：{detail}（本機已備份）"


# ===================== 3. Telegram 指令與訊息處理 =====================
async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>🤖 專屬論文管家 - 操作指引</b>\n\n"
        "<b>🔍 1. 搜尋最新未讀論文</b>\n"
        "• 輸入英文關鍵字，例如 <code>fly</code>、<code>psychology</code>\n"
        "• 部分中文會自動翻譯，例如 <code>蒼蠅</code> → fly\n"
        "• 明確搜尋：<code>搜尋 fly</code> 或 <code>/search fly</code>\n"
        "• arXiv 以英文為主，建議優先英文關鍵字\n\n"
        "<b>💬 關於聊天</b>\n"
        "• 我是論文工具 Bot，不是 ChatGPT，不能自由閒聊\n"
        "• 打「你好」會有說明；問句或長句不會被當成搜尋\n\n"
        "<b>📁 2. 資料夾與分類管理</b>\n"
        "• 查看目前資料夾：<code>我的資料夾</code>\n"
        "• 新增資料夾：<code>新增 類別名稱</code>\n"
        "• 重新命名：<code>改名 舊名稱to新名稱</code>\n"
        "• 移除資料夾：<code>移除 類別名稱</code>\n"
        "（資料夾變更會同步至 Google Drive）\n\n"
        "<b>☁️ 3. 雲端歸檔</b>\n"
        "• 選擇資料夾 → 論文存入你的 Google Drive\n"
        "• 點「沒興趣」→ 存入「沒興趣 (略過)」資料夾，日後可找回\n"
        "• 檢查雲端狀態：<code>/drive</code>"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def drive_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    drive = get_drive()
    msg = (
        f"<b>☁️ Google Drive 狀態</b>\n\n"
        f"{drive.status_message}\n\n"
        f"略過論文資料夾名稱：<code>{SKIPPED_FOLDER_NAME}</code>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/search fly — 明確觸發論文搜尋。"""
    if not context.args:
        await update.message.reply_text(
            "請輸入關鍵字，例如：<code>/search fly</code>",
            parse_mode="HTML",
        )
        return
    query_text = " ".join(context.args)
    await do_paper_search(update, context, query_text)


async def do_paper_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str
):
    """執行論文搜尋並推送結果。"""
    arxiv_query, display_label, _ = resolve_search_query(user_text)

    if arxiv_query is None:
        await update.message.reply_text(cn_hint(display_label), parse_mode="HTML")
        return

    translate_note = ""
    if arxiv_query.lower() != display_label.lower() and display_label != arxiv_query:
        translate_note = f"（<code>{display_label}</code> → <code>{arxiv_query}</code>）"

    await update.message.reply_text(
        f"🔍 正在搜尋【{display_label}】{translate_note} 的最新論文...",
        parse_mode="HTML",
    )
    seen = load_seen_papers()
    try:
        title, summary, link, already_seen = await asyncio.to_thread(
            fetch_paper_by_keyword, arxiv_query, seen
        )
    except Exception as exc:
        print(f"搜尋例外: {exc}", file=sys.stderr)
        await update.message.reply_text(
            "⚠️ 搜尋時發生錯誤，請稍後再試。若持續失敗請換個關鍵字。"
        )
        return

    if not title:
        await update.message.reply_text(
            f"😅 arXiv 上找不到與【{display_label}】相關的論文，請換個關鍵字試試。"
        )
        return

    context.user_data["current_title"] = title
    context.user_data["current_summary"] = summary
    context.user_data["current_link"] = link

    categories = load_categories()
    seen_note = (
        "\n\n<i>（此領域新論文你已看過不少，這篇是最相關的已讀候選）</i>"
        if already_seen
        else ""
    )
    message_text = (
        f"📚 <b>{html.escape(title)}</b>\n\n{html.escape(summary)}\n\n"
        f"🔗 <a href='{html.escape(link, quote=True)}'>閱讀原文</a>\n\n"
        f"請選擇歸檔資料夾：{seen_note}"
    )
    await update.message.reply_text(
        message_text,
        reply_markup=build_category_keyboard(categories),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
        
    user_id = update.effective_user.id
    auth_url = drive_manager.get_auth_url(user_id)
    
    welcome_text = (
        "👋 歡迎使用<b>論文管家</b>！\n\n"
        "若要將論文自動歸檔進你的 Google 雲端硬碟：\n"
        f"👉 <a href='{auth_url}'>點我獲取 Google 授權碼</a>\n\n"
        "授權後請直接將<b>驗證碼複製貼在此對話框</b>發送給我！"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")
    await send_help(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return

    user_text = update.message.text.strip()
    user_id = update.effective_user.id

    # 1. 判斷是否為 Google OAuth 授權碼
    if len(user_text) > 30 and " " not in user_text:
        if drive_manager.exchange_code(user_id, user_text):
            await update.message.reply_text("✅ Google Drive 授權成功！以後按按鈕即可直接歸檔進你的雲端。")
            return

    if user_text.lower() in ("/help",) or user_text in [
        "說明書",
        "功能",
        "/folders",
        "我的資料夾",
    ]:
        if user_text in ["/folders", "我的資料夾"]:
            categories = load_categories()
            folder_list = "\n".join([f"• {name}" for name in categories.values()])
            cloud_hint = "☁️ 雲端同步：已啟用" if drive.enabled else "☁️ 雲端同步：未設定"
            help_msg = (
                f"📁 <b>目前的資料夾清單</b>：\n{folder_list}\n\n"
                f"{cloud_hint}\n"
                f"略過歸檔至：<code>{SKIPPED_FOLDER_NAME}</code>\n\n"
                "🛠️ <b>管理指令</b>：\n"
                "• 新增：<code>新增 名稱</code>\n"
                "• 改名：<code>改名 舊to新</code>\n"
                "• 移除：<code>移除 名稱</code>"
            )
            await update.message.reply_text(help_msg, parse_mode="HTML")
        else:
            await send_help(update, context)
        return

    if user_text.startswith("新增") or (
        user_text.startswith("+") and not user_text.startswith("++")
    ):
        new_name = user_text.replace("新增", "").replace("+", "", 1).strip()
        if new_name:
            categories = load_categories()
            new_id = f"cat_{len(categories) + 1}_{random.randint(100, 999)}"
            categories[new_id] = new_name
            save_categories(categories)

            cloud_msg = ""
            if drive.enabled:
                if drive.create_category_folder(new_id, new_name):
                    cloud_msg = "\n☁️ 已同步建立 Google Drive 資料夾"
                else:
                    cloud_msg = "\n⚠️ 雲端資料夾建立失敗"

            await update.message.reply_text(
                f"✅ 成功新增資料夾：【<b>{new_name}</b>】！{cloud_msg}",
                parse_mode="HTML",
            )
        return

    if user_text.startswith("改名"):
        try:
            content = user_text.replace("改名", "").strip()
            parts = content.split("to") if "to" in content else content.split("->")
            old_name, new_name = parts[0].strip(), parts[1].strip()

            categories = load_categories()
            target_key = next(
                (k for k, v in categories.items() if v == old_name), None
            )

            if target_key:
                categories[target_key] = new_name
                save_categories(categories)
                if os.path.exists(old_name):
                    os.rename(old_name, new_name)

                cloud_msg = ""
                if drive.enabled:
                    if drive.rename_category_folder(target_key, new_name):
                        cloud_msg = "\n☁️ 已同步更新 Google Drive 資料夾名稱"
                    else:
                        cloud_msg = "\n⚠️ 雲端資料夾更名失敗"

                await update.message.reply_text(
                    f"✅ 已將【<b>{old_name}</b>】改名為【<b>{new_name}</b>】！{cloud_msg}",
                    parse_mode="HTML",
                )
            else:
                await update.message.reply_text(f"❌ 找不到名為【{old_name}】的資料夾。")
        except Exception:
            await update.message.reply_text(
                "⚠️ 格式錯誤！範例：<code>改名 量子物理to統計學</code>",
                parse_mode="HTML",
            )
        return

    if user_text.startswith("移除") or user_text.startswith("刪除資料夾"):
        target_name = user_text.replace("移除", "").replace("刪除資料夾", "").strip()
        categories = load_categories()
        target_key = next(
            (k for k, v in categories.items() if v == target_name), None
        )

        if target_key:
            del categories[target_key]
            save_categories(categories)
            if os.path.exists(target_name):
                os.rename(target_name, f"{target_name} (已刪除選項)")

            cloud_msg = ""
            if drive.enabled:
                if drive.mark_category_deleted(target_key, target_name):
                    cloud_msg = (
                        f"\n☁️ 雲端資料夾已標記為【{target_name} (已刪除選項)】"
                    )
                else:
                    cloud_msg = "\n⚠️ 雲端資料夾標記失敗"

            await update.message.reply_text(
                f"✅ 已將【<b>{target_name}</b>】從選單移除。{cloud_msg}",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(f"❌ 找不到名為【{target_name}】的資料夾。")
        return

    # --- 閒聊 / 問句：不當搜尋 ---
    if is_chitchat(user_text):
        await update.message.reply_text(
            get_chitchat_response(user_text), parse_mode="HTML"
        )
        return

    if is_likely_chat_not_search(user_text):
        await update.message.reply_text(NOT_A_SEARCH_HINT, parse_mode="HTML")
        return

    # --- 論文搜尋 ---
    await do_paper_search(update, context, user_text)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not update.effective_user:
        return

    await query.answer()

    choice = query.data
    user_id = update.effective_user.id
    title = context.user_data.get("current_title", "未知標題")
    summary = context.user_data.get("current_summary", "")
    link = context.user_data.get("current_link", "#")
    categories = load_categories()

    # 1. 檢查論文是否過期
    if link == "#":
        await query.edit_message_text(text="⚠️ 論文資料已過期，請重新搜尋。")
        return

    # 2. 使用者點擊「沒興趣 / 略過」
    if choice == "skip":
        # 記錄負面偏好（越推越準）
        db.update_preference(user_id, title, is_interested=False)
        # 存入雲端的略過資料夾
        ok, msg = drive_manager.archive_paper(user_id, SKIPPED_FOLDER_NAME, title, summary, link)
        cloud_hint = "\n☁️ 已同步至 Google Drive【略過】資料夾" if ok else ""
        await query.edit_message_text(f"🗑 已略過並記錄偏好（未來將減少此類推薦）{cloud_hint}")

    # 3. 使用者點擊指定自訂資料夾
    elif choice in categories:
        folder_name = categories[choice]
        # 記錄正面偏好（越推越準）
        db.update_preference(user_id, title, is_interested=True)
        # 上傳到該使用者的 Google Drive 資料夾
        ok, detail = drive_manager.archive_paper(user_id, folder_name, title, summary, link)
        if ok:
            await query.edit_message_text(f"✅ 已成功歸檔至你的 Google Drive：【{folder_name}】！")
        else:
            await query.edit_message_text(f"⚠️ 雲端歸檔失敗：{detail}\n👉 若尚未綁定雲端，請打 /start 點連結授權。")
    else:
        await query.edit_message_text(text="⚠️ 此分類按鈕已不存在。")


def build_application():
    token = require_token()
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", send_help))
    application.add_handler(CommandHandler("drive", drive_status))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    return application


def bootstrap_drive():
    drive = get_drive()
    if drive.enabled:
        categories = load_categories()
        drive.sync_categories(categories)
        print("Google Drive 資料夾已同步")
    else:
        print(drive.status_message)


# ===================== 4. 主程式啟動 =====================
def main():
    bootstrap_drive()
    application = build_application()
    run_mode = os.getenv("RUN_MODE", "webhook").lower()

    if run_mode == "polling":
        print("以 polling 模式啟動（適合本機開發）")
        application.run_polling(drop_pending_updates=True)
        return

    webhook_base = os.getenv("WEBHOOK_URL", "https://paperfilter-bot.onrender.com")
    port = int(os.environ.get("PORT", 10000))
    token = require_token()

    print(f"以 webhook 模式啟動，監聽 0.0.0.0:{port}")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=f"{webhook_base.rstrip('/')}/{token}",
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
