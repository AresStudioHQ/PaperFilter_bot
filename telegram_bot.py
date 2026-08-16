import os
import json
import random
import sys
import asyncio
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from database import db
from OAthur2 import drive_manager, SKIPPED_FOLDER_NAME, SKIPPED_KEY
from paper_search import fetch_paper_multi_source, extract_arxiv_id
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
CONFIG_FILE = "categories.json"

# 把它貼在原本 CONFIG_FILE = "categories.json" 的下方
def load_categories(user_id):
    category_names = db.get_user_categories(user_id)
    return {f"cat_{i}": name for i, name in enumerate(category_names)}


def require_token() -> str:
    if not TOKEN:
        print("錯誤：請在環境變數設定 TELEGRAM_TOKEN", file=sys.stderr)
        sys.exit(1)
    return TOKEN


# ===================== 2. 資料與檔案處理函式 ===================== 

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
        "• 輸入英文關鍵字，例如 <code>space</code>\n"
        "• 部分中文會自動翻譯，例如 <code>太空</code> → space\n"
        "• 明確搜尋：<code>搜尋 space</code> 或 <code>/search space</code>\n"
        "• 論文平臺以英文為主，建議優先英文關鍵字\n\n"
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

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer() # 消除按鈕載入中的轉圈圈狀態
    
    data = query.data  # 取得按鈕帶過來的資料，例如 "archive_生物生態"
    user_id = query.from_user.id
    
    # 判斷是否為歸檔按鈕
    if data.startswith("archive_"):
        folder_name = data.replace("archive_", "", 1)
        
        try:
            # 1. 這裡呼叫你的雲端建立資料夾與自動歸檔邏輯
            # 例如：drive_manager.create_folder_and_move(user_id, folder_name)
            
            # 2. 修改原本的訊息，顯示已經歸檔成功
            await query.edit_message_text(
                text=f"✅ 已成功為您在雲端建立資料夾並完成歸檔：<b>{folder_name}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"🔥 歸檔按鈕執行錯誤: {e}")
            await query.message.reply_text(
                f"⚠️ 歸檔失敗：{e}",
                parse_mode="HTML"
            )


async def drive_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return

    user_id = update.effective_user.id
    token = db.get_token(user_id)
    
    if token:
        status_text = "✅ 你的 Google Drive 雲端已成功連線！\n（點擊論文分類按鈕即可直接自動歸檔）"
    else:
        auth_url = drive_manager.get_auth_url(user_id)
        status_text = (
            "⚠️ 尚未綁定 Google Drive 雲端！\n\n"
            f"👉 <a href='{auth_url}'>點我獲取 Google 授權</a>\n"
            "授權後即可完成綁定。"
        )

    msg = (
        f"<b>☁️ Google Drive 狀態</b>\n\n"
        f"{status_text}\n\n"
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
    """執行論文搜尋並推送結果（支援跨平台動態去重與偏好）。"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    arxiv_query, display_label, _ = resolve_search_query(user_text)
    if arxiv_query is None:
        await update.message.reply_text(cn_hint(display_label), parse_mode="HTML")
        return

    translate_note = ""
    if arxiv_query.lower() != display_label.lower() and display_label != arxiv_query:
        translate_note = f"（<code>{display_label}</code> → <code>{arxiv_query}</code>）"

    await update.message.reply_text(
        f"🔍 正在為您搜尋【{display_label}】{translate_note} 的最新論文...",
        parse_mode="HTML",
    )

    # 從資料庫取得該用戶看過的論文與偏好
    seen_ids = db.get_seen_papers(user_id)
    user_bias = db.get_user_bias(user_id)

    try:
        title, summary, link, paper_id, already_seen = await asyncio.to_thread(
            fetch_paper_multi_source, arxiv_query, seen_ids, user_bias
        )
    except Exception as exc:
        print(f"搜尋例外: {exc}", file=sys.stderr)
        await update.message.reply_text("⚠️ 搜尋時發生錯誤，請稍後再試。若持續失敗請換個關鍵字。")
        return

    if not title:
        await update.message.reply_text(f"😅 找不到與【{display_label}】相關的論文，請換個關鍵字試試。")
        return

    # 立刻在資料庫記錄這篇已被該用戶看過（下次輸入同關鍵字就不會重複了！）
    if paper_id:
        db.add_seen_paper(user_id, paper_id)

    context.user_data["current_title"] = title
    context.user_data["current_summary"] = summary
    context.user_data["current_link"] = link

    categories = load_categories(user_id)
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
    if not update.effective_user or not update.message:
        return
        
    user_id = update.effective_user.id

    # --- 新增這段：自動檢查是否為新用戶，若是則初始化分類 ---
    current_cats = db.get_user_categories(user_id)
    if not current_cats:
        default_cats = ["人工智慧", "生物生態", "綜合科學", "人類基因"]
        for cat in default_cats:
            db.add_user_category(user_id, cat)

    auth_url = drive_manager.get_auth_url(user_id)
    
    welcome_text = (
        "👋 歡迎使用<b>論文管家</b>！\n\n"
        "若要將論文自動歸檔進你的 Google 雲端硬碟：\n"
        "1. 請點擊下方按鈕獲取授權\n"
        "2. 授權後即可完成綁定！\n\n"
        "或直接輸入關鍵字開始搜尋！"
    )
    
    # 使用 Telegram 互動式網址按鈕（保證直接跳出瀏覽器開啟）
    keyboard = []
    if auth_url and auth_url != "#":
        keyboard.append([InlineKeyboardButton("🔗 點我開啟 Google 授權頁面", url=auth_url)])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    await send_help(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return

    user_text = update.message.text.strip()
    user_id = update.effective_user.id
    is_drive_linked = bool(db.get_token(user_id))

    # 1. 判斷是否為 Google OAuth 授權碼
    if len(user_text) > 30 and " " not in user_text:
        if drive_manager.exchange_code(user_id, user_text):
            await update.message.reply_text("✅ Google Drive 授權成功！以後按按鈕即可直接歸檔進你的雲端。")
            return

    # 2. 說明書與資料夾清單
    if user_text.lower() in ("/help",) or user_text in ["說明書", "功能", "/folders", "我的資料夾"]:
        if user_text in ["/folders", "我的資料夾"]:
            categories = load_categories(user_id)
            folder_list = "\n".join([f"• {name}" for name in categories.values()])
            cloud_hint = "☁️ 雲端同步：已綁定" if is_drive_linked else "☁️ 雲端同步：未授權（請點 /start 綁定）"
            
            help_msg = (
                f"📁 <b>目前的資料夾清單</b>：\n{folder_list}\n\n"
                f"{cloud_hint}\n"
                f"略過歸檔至：<code>{SKIPPED_FOLDER_NAME}</code>\n\n"
                "🛠 <b>管理指令</b>：\n"
                "• 新增：<code>新增 名稱</code>\n"
                "• 改名：<code>改名 舊名稱to新名稱</code>\n"
                "• 移除：<code>移除 名稱</code>"
            )
            await update.message.reply_text(help_msg, parse_mode="HTML")
        else:
            await send_help(update, context)
        return

    # 3. 新增資料夾
    if user_text.startswith("新增") or (user_text.startswith("+") and not user_text.startswith("++")):
        new_name = user_text.replace("新增", "").replace("+", "", 1).strip()
        if new_name:
            categories = load_categories(user_id)
            new_id = f"cat_{len(categories) + 1}_{random.randint(100, 999)}"
            categories[new_id] = new_name
        db.add_user_category(user_id, new_name)
        await update.message.reply_text(f"✅ 成功新增資料夾：【<b>{new_name}</b>】！", parse_mode="HTML")
        return

    # 4. 改名資料夾
    if user_text.startswith("改名"):
        try:
            content = user_text.replace("改名", "", 1).strip()
            
            # 支援常見的分隔字串，直接用 if 判斷，百分之百不會誤判
            parts = None
            for sep in ["to", "->", "➡️", "換成"]:
                if sep in content:
                    parts = content.split(sep, 1)
                    break
            
            if parts and len(parts) == 2 and parts[0].strip() and parts[1].strip():
                old_name = parts[0].strip()
                new_name = parts[1].strip()
                
                raw_cats = db.get_user_categories(user_id)
                current_cats = list(raw_cats.values()) if isinstance(raw_cats, dict) else list(raw_cats)
                
                if old_name in current_cats:
                    db.rename_user_category(user_id, old_name, new_name)
                    
                    try:
                        sync_ok = drive_manager.rename_folder(user_id, old_name, new_name)
                    except Exception:
                        sync_ok = False
                        
                    cloud_msg = "\n☁️ Google Drive 資料夾已同步更名！" if sync_ok else ""
                    
                    await update.message.reply_text(
                        f"✅ 已將 <b>{old_name}</b> 成功改名為 <b>{new_name}</b> ！{cloud_msg}",
                        parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ 找不到名為 <b>{old_name}</b> 的資料夾。\n💡 提示：請先輸入 「我的資料夾」 確認目前正確的名稱！",
                        parse_mode="HTML"
                    )
            else:
                await update.message.reply_text(
                    "⚠️ 格式錯誤！正確範例：<code>改名 綜合科學to科學系</code>",
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"🔥 改名例外錯誤: {e}")
            await update.message.reply_text(
                f"⚠️ 改名發生錯誤：{e}",
                parse_mode="HTML"
            )
        return

  # 5. 移除資料夾
    if user_text.startswith("移除") or user_text.startswith("刪除資料夾"):
        try:
            target_name = user_text.replace("移除", "", 1).replace("刪除資料夾", "", 1).strip()
            
            raw_cats = db.get_user_categories(user_id)
            current_cats = list(raw_cats.values()) if isinstance(raw_cats, dict) else list(raw_cats)
            
            if target_name in current_cats:
                # 1. 執行資料庫刪除
                db.delete_user_category(user_id, target_name)
                
                # 2. 雲端同步（加上安全防護，就算雲端掛了也不影響回傳成功）
                sync_ok = False
                try:
                    sync_ok = drive_manager.mark_folder_deleted(user_id, target_name)
                except Exception as d_err:
                    print(f"雲端標記刪除失敗（可忽略）: {d_err}")
                
                cloud_msg = "\n☁️ 雲端資料夾已同步標記" if sync_ok else ""
                
                # 3. 絕對保證會執行的成功回傳
                await update.message.reply_text(
                    f"✅ 已成功將 <b>{target_name}</b> 從資料夾清單移除！{cloud_msg}",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text(
                    f"❌ 找不到名為 <b>{target_name}</b> 的資料夾。\n💡 提示：請先輸入 「我的資料夾」 確認現有名稱！",
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"🔥 移除例外錯誤: {e}")
            await update.message.reply_text(
                f"⚠️ 移除發生錯誤：{e}",
                parse_mode="HTML"
            )
        return
    
    # 6. 閒聊過濾
    if is_chitchat(user_text):
        await update.message.reply_text(get_chitchat_response(user_text), parse_mode="HTML")
        return

    # 7. 長句防呆
    if is_likely_chat_not_search(user_text):
        await update.message.reply_text(NOT_A_SEARCH_HINT, parse_mode="HTML")
        return

    # 8. 執行論文搜尋
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
    
    # 重新載入該用戶的分類字典（例如 {"cat_0": "人工智慧", "cat_1": "生物生態"}）
    categories = load_categories(user_id)

    # 1. 檢查論文是否過期
    if link == "#":
        await query.edit_message_text(text="⚠️ 論文資料已過期，請重新搜尋。")
        return

    # 2. 使用者點擊「沒興趣 / 略過」
    if choice == "skip":
        db.update_preference(user_id, title, is_interested=False)
        ok, msg = drive_manager.archive_paper(user_id, SKIPPED_FOLDER_NAME, title, summary, link)
        cloud_hint = "\n☁️ 已同步至 Google Drive【略過】資料夾" if ok else ""
        await query.edit_message_text(f"🗑 已略過並記錄偏好（未來將減少此類推薦）{cloud_hint}")

    # 3. 使用者點擊自訂分類按鈕（choice 會是 "cat_0", "cat_1" 等）
    elif choice in categories:
        folder_name = categories[choice]  # 取得真實的資料夾名稱，例如 "人工智慧"
        db.update_preference(user_id, title, is_interested=True)
        
        # 💡 這行就是核心：自動在 Google Drive 建立資料夾並歸檔
        ok, detail = drive_manager.archive_paper(user_id, folder_name, title, summary, link)
        
        if ok:
            await query.edit_message_text(f"✅ 已成功為您在雲端建立資料夾並完成歸檔：【<b>{folder_name}</b>】！", parse_mode="HTML")
        else:
            await query.edit_message_text(f"⚠️ 雲端歸檔失敗：{detail}\n👉 若尚未綁定雲端，請打 /start 點連結授權。", parse_mode="HTML")
            
    else:
        await query.edit_message_text(text="⚠️ 此分類按鈕已失效或不存在。")


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

# ===================== 4. 主程式啟動 (支援自動網頁授權回傳) =====================
from aiohttp import web

async def handle_oauth_callback(request):
    """ Google 授權完成後，自動跳轉到這裡處理並顯示全螢幕自適應精美字卡 """
    code = request.query.get("code")
    user_id_str = request.query.get("state")

    if code and user_id_str:
        user_id = int(user_id_str)
        if drive_manager.exchange_code(user_id, code):
            # 1. 透過 Telegram 發送訊息
            try:
                bot_token = require_token()
                from telegram import Bot
                bot = Bot(token=bot_token)
                await bot.send_message(
                    chat_id=user_id,
                    text="🎉 <b>Google Drive 授權成功！</b>\n\n現在你可以直接點擊任何論文分類按鈕，論文就會自動歸檔進你的雲端硬碟囉！",
                    parse_mode="HTML"
                )
            except Exception:
                pass

            # 2. 全螢幕垂直水平完美置中、大字體綠色成功卡片
            html_success = """
            <!DOCTYPE html>
            <html lang="zh-TW">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>授權成功 - 論文管家</title>
                <style>
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body {
                        min-height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
                        padding: 24px;
                    }
                    .card {
                        background: rgba(255, 255, 255, 0.95);
                        backdrop-filter: blur(10px);
                        width: 100%;
                        max-width: 520px;
                        padding: 48px 36px;
                        border-radius: 28px;
                        box-shadow: 0 20px 40px rgba(22, 101, 52, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
                        text-align: center;
                        border: 1px solid rgba(255, 255, 255, 0.8);
                    }
                    .icon {
                        font-size: 72px;
                        line-height: 1;
                        margin-bottom: 24px;
                        display: inline-block;
                    }
                    h1 {
                        font-size: 30px;
                        font-weight: 800;
                        color: #166534;
                        margin-bottom: 16px;
                        letter-spacing: -0.5px;
                    }
                    p {
                        font-size: 19px;
                        line-height: 1.6;
                        color: #374151;
                        margin-bottom: 32px;
                    }
                    .badge {
                        display: inline-block;
                        background: #dcfce7;
                        color: #15803d;
                        padding: 8px 18px;
                        border-radius: 999px;
                        font-size: 15px;
                        font-weight: 600;
                        margin-bottom: 24px;
                    }
                    .hint {
                        font-size: 16px;
                        color: #6b7280;
                        border-top: 1px dashed #e5e7eb;
                        padding-top: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="icon">🎉</div>
                    <div class="badge">已成功連線至 Google Drive</div>
                    <h1>授權成功！</h1>
                    <p>您的雲端硬碟已成功與 <b>論文管家</b> 綁定。<br>現在每次點擊分類，系統將自動為您極速歸檔！</p>
                    <div class="hint">👉 您現在可以關閉此分頁，回到 Telegram 開始使用了。</div>
                </div>
            </body>
            </html>
            """
            return web.Response(text=html_success, content_type="text/html")

    # 失敗時的置中紅色卡片
    html_failed = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>授權未完成</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                padding: 24px;
            }
            .card {
                background: white;
                width: 100%;
                max-width: 500px;
                padding: 44px 32px;
                border-radius: 24px;
                box-shadow: 0 20px 40px rgba(159, 18, 57, 0.08);
                text-align: center;
            }
            .icon { font-size: 64px; margin-bottom: 20px; }
            h1 { font-size: 26px; color: #9f1239; margin-bottom: 12px; }
            p { font-size: 17px; line-height: 1.6; color: #4b5563; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">⚠️</div>
            <h1>授權未完成</h1>
            <p>無法取得 Google 授權憑證。<br>請回到 Telegram 對話框重新點擊授權連結！</p>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html_failed, content_type="text/html", status=400)

async def handle_telegram_webhook(request, application):
    """ 接收 Telegram 的訊息更新 """
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response(text="OK")

def main():
    application = build_application()
    run_mode = os.getenv("RUN_MODE", "webhook").lower()

    if run_mode == "polling":
        print("以 polling 模式啟動（適合本機開發）")
        application.run_polling(drop_pending_updates=True)
        return

    # Webhook 伺服器設定
    port = int(os.environ.get("PORT", 10000))
    token = require_token()
    webhook_base = os.getenv("WEBHOOK_URL", "https://paperfilter-bot.onrender.com")

    # 初始化 Telegram Application
    async def start_web_app():
        await application.initialize()
        await application.start()
        await application.bot.set_webhook(url=f"{webhook_base.rstrip('/')}/{token}", drop_pending_updates=True)

        # 建立 aiohttp 網頁伺服器
        server = web.Application()
        server.router.add_post(f"/{token}", lambda req: handle_telegram_webhook(req, application))
        server.router.add_get("/oauth2callback", handle_oauth_callback)
        server.router.add_get("/", lambda req: web.Response(text="PaperFilterBot is Running! 🚀"))

        runner = web.AppRunner(server)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"🚀 伺服器已啟動，監聽 0.0.0.0:{port}，支援 Telegram 與 Google OAuth 回呼！")

        # 保持伺服器運行
        while True:
            await asyncio.sleep(3600)

    asyncio.run(start_web_app())

if __name__ == "__main__":
    main()