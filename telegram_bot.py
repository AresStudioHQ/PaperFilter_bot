import os
import json
import asyncio
import urllib.parse
import random
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import feedparser

# ========================== 1. 基礎設定 ==========================
TOKEN = "8933939727:AAGqGDok3XMo1Ppm1ZvduAD80554N51ILUQ"
SEEN_FILE = 'seen_papers.txt'
CONFIG_FILE = 'categories.json'

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ========================== 2. 資料與檔案處理函式 ==========================
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
        f.write(f"標題: {title}\n連結: {link}\n{'-'*50}\n")

def fetch_unseen_paper_by_keyword(user_input):
    seen = load_seen_papers()
    encoded_query = urllib.parse.quote(user_input)
    url = f'http://export.arxiv.org/api/query?search_query=all:{encoded_query}&max_results=50&sortBy=submittedDate&sortOrder=descending'
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            unseen_entries = [e for e in feed.entries if e.link not in seen]
            if unseen_entries:
                entry = random.choice(unseen_entries)
                title = entry.title.strip().replace('\n', ' ')
                summary = entry.summary.strip().replace('\n', ' ')[:250] + "..."
                link = entry.link
                return title, summary, link
    except Exception as e:
        print(f"解析失敗: {e}")
    return None, None, None

# ========================== 3. Telegram 指令與訊息處理 ==========================
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
    await update.message.reply_text("歡迎使用論文管家！")
    await send_help(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if user_text.lower() == '/help' or user_text in ['說明書', '功能', '/folders', '我的資料夾']:
        if user_text in ['/folders', '我的資料夾']:
            categories = load_categories()
            folder_list = "\n".join([f"• {name}" for name in categories.values()])
            help_msg = f"📁 <b>目前的資料夾清單</b>：\n{folder_list}\n\n🛠️ <b>管理指令</b>：\n• 新增：<code>新增 名稱</code>\n• 改名：<code>改名 舊to新</code>\n• 移除：<code>移除 名稱</code>"
            await update.message.reply_text(help_msg, parse_mode='HTML')
        else:
            await send_help(update, context)
        return

    # 新增資料夾
    if user_text.startswith('新增'):
        new_name = user_text.replace('新增', '').strip()
        if new_name:
            categories = load_categories()
            new_id = f'cat_{len(categories) + 1}_{random.randint(100,999)}'
            categories[new_id] = new_name
            save_categories(categories)
            await update.message.reply_text(f"✅ 成功新增資料夾：【<b>{new_name}</b>】！", parse_mode='HTML')
        return

    # 重新命名資料夾
    if user_text.startswith('改名'):
        try:
            content = user_text.replace('改名', '').strip()
            parts = content.split('to') if 'to' in content else content.split('->')
            old_name, new_name = parts[0].strip(), parts[1].strip()
            
            categories = load_categories()
            target_key = next((k for k, v in categories.items() if v == old_name), None)
            
            if target_key:
                categories[target_key] = new_name
                save_categories(categories)
                if os.path.exists(old_name):
                    os.rename(old_name, new_name)
                await update.message.reply_text(f"✅ 已將【<b>{old_name}</b>】改名為【<b>{new_name}</b>】！", parse_mode='HTML')
            else:
                await update.message.reply_text(f"❌ 找不到名為【{old_name}】的資料夾。")
        except Exception:
            await update.message.reply_text("⚠️ 格式錯誤！範例：<code>改名 量子物理to統計學</code>", parse_mode='HTML')
        return

    # 移除資料夾
    if user_text.startswith('移除'):
        target_name = user_text.replace('移除', '').strip()
        categories = load_categories()
        target_key = next((k for k, v in categories.items() if v == target_name), None)
        
        if target_key:
            del categories[target_key]
            save_categories(categories)
            if os.path.exists(target_name):
                os.rename(target_name, f"{target_name} (已刪除選項)")
            await update.message.reply_text(f"✅ 已將【<b>{target_name}</b>】從選單移除。", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ 找不到名為【{target_name}】的資料夾。")
        return

    # 一般論文關鍵字搜尋
    await update.message.reply_text(f"🔍 正在搜尋【{user_text}】的最新論文...", parse_mode='HTML')
    title, summary, link = fetch_unseen_paper_by_keyword(user_text)
    
    if not title:
        await update.message.reply_text(f"😅 找不到與【{user_text}】相關的新論文，或都已經看過了！")
        return
    
    context.user_data['current_title'] = title
    context.user_data['current_link'] = link
    
    categories = load_categories()
    keyboard = [[InlineKeyboardButton(name, callback_data=cid) for cid, name in categories.items()]]
    keyboard.append([InlineKeyboardButton("❌ 略過", callback_data='skip')])
    
    message_text = f"📚 <b>{title}</b>\n\n{summary}\n\n🔗 <a href='{link}'>閱讀原文</a>\n\n請選擇歸檔資料夾："
    await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    title = context.user_data.get('current_title', '未知標題')
    link = context.user_data.get('current_link', '#')
    categories = load_categories()
    
    if choice == 'skip':
        if link != '#':
            save_seen_paper(link)
        await query.edit_message_text(text="❌ 此篇論文已略過。")
    elif choice in categories:
        folder_name = categories[choice]
        if link != '#':
            save_to_folder(folder_name, title, link)
            save_seen_paper(link)
        await query.edit_message_text(text=f"✅ 已成功歸檔至：【{folder_name}】！")
    else:
        await query.edit_message_text(text="⚠️ 此分類按鈕已不存在。")

# 註冊 Handler
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_callback))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ========================== 4. Webhook 路由 ==========================
# 1. 先定義好所有的路由與函式
@app.route("/webhook", methods=["POST"])
async def webhook():
    await application.initialize()
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Telegram Bot is running!"

# 2. 永遠把這行放在整個檔案的最底部！
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)