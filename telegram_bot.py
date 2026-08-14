import os
import json
import asyncio
import urllib.parse
import random
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===================== 1. 基礎設定 =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
SEEN_FILE = 'seen_papers.txt'
CONFIG_FILE = 'categories.json'

# ===================== 2. 資料與檔案處理函式 =====================
def load_categories():
    if not os.path.exists(CONFIG_FILE):
        default = {'cat_1': '生物生態', 'cat_2': '人工智慧', 'cat_3': '金融市場', 'cat_4': '綜合科學'}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_categories(categories):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=4)

def load_seen_papers():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def save_seen_paper(link):
    with open(SEEN_FILE, 'a', encoding='utf-8') as f:
        f.write(link + '\n')

def save_to_folder(folder_name, title, link):
    os.makedirs(folder_name, exist_ok=True)
    file_path = os.path.join(folder_name, "saved_papers.txt")
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(f"標題: {title}\n連結: {link}\n" + "-"*50 + "\n")

# ===================== 3. Telegram 指令與訊息處理 =====================
async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>🤖 專屬論文管家 - 操作指引</b>\n\n"
        "<b>🔍 1. 搜尋最新未讀論文</b>\n"
        "• 直接輸入想找的關鍵字即可開始搜尋（建議使用英文）。\n\n"
        "<b>📁 2. 資料夾與分類管理</b>\n"
        "• 查看目前資料夾：<code>我的資料夾</code> 或 <code>/folders</code>\n"
        "• 新增資料夾：<code>新增 類別名稱</code>\n"
        "• 重新命名：<code>改名 舊名稱to新名稱</code>\n"
        "• 移除資料夾：<code>移除 名稱</code>"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好！論文過濾系統已成功啟動！")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    
    if user_text.lower() == '/help' or user_text in ['說明書', '功能', '/folders', '我的資料夾']:
        if user_text in ['/folders', '我的資料夾']:
            categories = load_categories()
            folder_list = "\n".join([f"• {name}" for name in categories.values()])
            help_msg = f"📁 <b>目前的資料夾清單</b>：\n{folder_list}\n\n⚙️ <b>管理指令</b>：\n• 新增：<code>新增 類別名稱</code>\n• 改名：<code>改名 舊to新</code>\n• 刪除：<code>移除 名稱</code>"
            await update.message.reply_text(help_msg, parse_mode='HTML')
        else:
            await send_help(update, context)
        return

    # 搜尋處理與其他邏輯可以在此擴充
    await update.message.reply_text(f"收到你的搜尋關鍵字：{user_text}，系統正在處理中...")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # 按鈕回調邏輯

# ===================== 4. 主程式與 Webhook 啟動 =====================
def main():
    # 建立 Application
    application = ApplicationBuilder().token(TOKEN).build()

    # 註冊 Handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", send_help))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 取得 Render 動態 Port
    PORT = int(os.environ.get("PORT", 10000))

    # 使用官方內建的 Webhook 功能
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://paperfilter-bot.onrender.com/{TOKEN}",
        drop_pending_updates=True,
    )



if __name__ == "__main__":
    main()