import os
import json
import random
import urllib
import asyncio
from flask import Flask, request
from feedparser import feedparser  # 如果有用到
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# ==================== 1. 基本設定區 ====================
TOKEN = "你的_TELEGRAM_BOT_TOKEN"  # 請把這裡換成你真正的 Bot Token
PORT = int(os.environ.get("PORT", 10000))
SEEN_FILE = 'seen_papers.txt'
CONFIG_FILE = 'categories.json'

app = Flask(__name__)
bot = Bot(token=TOKEN)

# 建立 Telegram 應用程式容器
application = Application.builder().token(TOKEN).build()


# ==================== 2. 功能邏輯區 (請把你的功能放這裡) ====================

async def start(update: Update, context):
    """使用者輸入 /start 時的歡迎訊息"""
    await update.message.reply_text("你好！我是你的 24 小時雲端論文管家（Webhook 模式已啟動）。")

# 註冊 /start 指令
application.add_handler(CommandHandler("start", start))

# -------------------------------------------------------------------------
# 【提示】請把妳之前寫好的其他功能（例如搜尋論文、處理檔案、綁定網址等）
# 用下面這種方式加進來：
# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def load_categories():
    if not os.path.exists(CONFIG_FILE):
        default_categories = {
            'cat_1': '🧬 生物生態',
            'cat_2': '💻 人工智慧',
            'cat_3': '📈 金融市場',
            'cat_4': '🔬 綜合科學'
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_categories, f, ensure_ascii=False, indent=4)
        return default_categories
    
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

# 操作指引：採用你指定的直覺語法
async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>🤖 專屬論文管家 - 操作指引</b>\n\n"
        "<b>🔍 1. 搜尋最新未讀論文</b>\n"
        "• 直接輸入想找的關鍵字即可開始搜尋。\n"
        "• 💡 <b>建議</b>：因資料庫為國際英文介面，使用 <b>英文關鍵字</b>（例如：<code>quantum computing</code>）搜尋效果最好、文章最豐富！\n\n"
        "<b>📁 2. 資料夾與分類管理</b>\n"
        "• 查看目前資料夾：<code>/folders</code> 或 <code>我的資料夾</code>\n"
        "• 新增資料夾：<code>新增 「資料夾名稱」</code>（例如：<code>新增 量子物理</code>）\n"
        "• 重新命名資料夾：<code>改名 「舊名稱」to「新名稱」</code>（例如：<code>改名 量子物理to統計學</code>) (另外，雲端資料夾會同步更改）\n"
        "• 移除資料夾：<code>移除 「資料夾名稱」</code>（例如：<code>移除 量子物理</code>) (當選項移除時，雲端資料夾將自動備註 <code>(已刪除選項)</code>）"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    
    if user_text.lower() == '/help' or user_text == '說明書' or user_text == '功能':
        await send_help(update, context)
        return

    # 1. 新增資料夾：直接打 +量子物理
    if user_text.startswith('+'):
        new_name = user_text.replace('+', '').strip()
        if new_name:
            categories = load_categories()
            new_id = f'cat_{len(categories) + 1}_{random.randint(100,999)}'
            categories[new_id] = new_name
            save_categories(categories)
            await update.message.reply_text(f"✅ 成功新增資料夾選單：【<b>{new_name}</b>】！\n💡 提示：當你有論文選擇歸檔到此資料夾時，系統才會正式在雲端建立它。", parse_mode='HTML')
            return

    # 2. 重新命名資料夾：改名 量子物理to統計學 (自動同步雲端資料夾名稱)
    if user_text.startswith('改名'):
        try:
            content = user_text.replace('改名', '').strip()
            # 支援以 to 或 -> 分隔
            if 'to' in content:
                parts = content.split('to')
            elif '->' in content:
                parts = content.split('->')
            else:
                raise ValueError("格式錯誤")
                
            old_name = parts[0].strip()
            new_name = parts[1].strip()
            
            categories = load_categories()
            target_key = None
            for k, v in categories.items():
                if v == old_name:
                    target_key = k
                    break
            
            if target_key:
                categories[target_key] = new_name
                save_categories(categories)
                
                # 同步更改雲端/電腦上的實體資料夾名稱
                if os.path.exists(old_name):
                    os.rename(old_name, new_name)
                    
                await update.message.reply_text(f"✅ 已成功將資料夾【<b>{old_name}</b>】重新命名為【<b>{new_name}</b>】，雲端資料夾與所有舊檔案皆同步更新且完美保留！", parse_mode='HTML')
            else:
                await update.message.reply_text(f"❌ 找不到名為【{old_name}】的資料夾，請輸入 <code>我的資料夾</code> 確認名稱。", parse_mode='HTML')
        except Exception:
            await update.message.reply_text("⚠️ 格式錯誤！正確格式範例：\n<code>改名 量子物理to統計學</code>", parse_mode='HTML')
        return

    # 3. 移除資料夾：移除資料夾 量子物理 (按鈕拔掉、雲端加上 (已刪除選項) 備註)
    if user_text.startswith('移除資料夾'):
        target_name = user_text.replace('移除資料夾', '').strip()
        categories = load_categories()
        target_key = None
        for k, v in categories.items():
            if v == target_name:
                target_key = k
                break
        
        if target_key:
            del categories[target_key]
            save_categories(categories)
            
            if os.path.exists(target_name):
                new_folder_name = f"{target_name} (已刪除選項)"
                os.rename(target_name, new_folder_name)
            
            await update.message.reply_text(f"✅ 已將【<b>{target_name}</b>】從按鈕選單移除。\n💡 雲端實體資料夾已自動備註為 <code>{target_name} (已刪除選項)</code>，內含檔案安全保留！", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ 找不到名為【{target_name}】的資料夾。")
        return

    # 4. 檢視資料夾：/folders 或 我的資料夾
    if user_text == '我的資料夾' or user_text == '/folders':
        categories = load_categories()
        folder_list = "\n".join([f"• {name}" for name in categories.values()])
        help_msg = (
            f"📁 <b>目前的資料夾清單</b>：\n{folder_list}\n\n"
            f"🛠️ <b>管理指令快速對照</b>：\n"
            f"• 新增：<code>+新資料夾名稱</code> (例：<code>+量子物理</code>)\n"
            f"• 改名：<code>改名 舊名稱to新名稱</code> (例：<code>改名 量子物理to統計學</code>)\n"
            f"• 移除：<code>移除資料夾 資料夾名稱</code> (例：<code>移除資料夾 量子物理</code>)\n"
            f"• 查看說明：輸入 <code>/help</code>"
        )
        await update.message.reply_text(help_msg, parse_mode='HTML')
        return

    # 一般搜尋論文流程
    await update.message.reply_text(f"🔍 正在全網資料庫中為你搜尋與【{user_text}】相關的最新論文...\n<i>(提示：若結果較少，建議嘗試用英文關鍵字搜尋效果更好)</i>", parse_mode='HTML')
    
    title, summary, link = fetch_unseen_paper_by_keyword(user_text)
    
    if not title:
        await update.message.reply_text(f"😅 找不到與【{user_text}】相關的新論文，或者符合條件的文章你都已經看過了！\n💡 建議可以換成英文關鍵字再試一次。", parse_mode='HTML')
        return
    
    context.user_data['current_title'] = title
    context.user_data['current_link'] = link
    
    categories = load_categories()
    keyboard = []
    row = []
    for cat_id, cat_name in categories.items():
        row.append(InlineKeyboardButton(cat_name, callback_data=cat_id))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ 略過 (不感興趣)", callback_data='skip')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        f"📚 <b>搜尋結果：{user_text}</b>\n\n"
        f"<b>標題</b>: {title}\n\n"
        f"<b>摘要預覽</b>: {summary}\n\n"
        f"🔗 <a href='{link}'>點此閱讀原文</a>\n\n"
        f"請選擇要歸檔的資料夾："
    )
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='HTML', disable_web_page_preview=True)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    title = context.user_data.get('current_title', '未知標題')
    link = context.user_data.get('current_link', '#')
    categories = load_categories()
    
    if choice == 'skip':
        if link != '#':
            save_seen_paper(link)
        await query.edit_message_text(text="❌ 此篇論文已略過，並已加入已讀清單。")
    elif choice in categories:
        folder_name = categories[choice]
        if link != '#':
            save_to_folder(folder_name, title, link)
            save_seen_paper(link)
        await query.edit_message_text(text=f"✅ 已成功將論文歸檔至：【{folder_name}】資料夾！(雲端資料夾已同步建立/更新)")
    else:
        await query.edit_message_text(text="⚠️ 此分類按鈕已不存在或已被移除。")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()    
    application.add_handler(CommandHandler("help", send_help))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_click))
    
# application.add_handler(CommandHandler("search",你的搜尋函式))
# application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 你的訊息處理函式))
# -------------------------------------------------------------------------


# ==================== 3. Webhook 核心接收與轉發區 ====================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """接收 Telegram 伺服器推播過來的更新訊息"""
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot)
    
    # 將事件安全地丟入 Telegram 應用程式佇列中執行
    asyncio.run_coroutine_threadsafe(
        application.process_update(update), 
        application.bot_data.get('loop', asyncio.get_event_loop())
    )
    return "ok"

@app.route("/")
def index():
    """用來讓 Render 伺服器自我檢測的健康檢查首頁"""
    return "Paper Bot is running successfully!"


# ==================== 4. 伺服器啟動與初始化 ====================

if __name__ == "__main__":
    # 初始化 Telegram 應用程式的事件迴圈
    loop = asyncio.get_event_loop()
    application.bot_data['loop'] = loop
    loop.run_until_complete(application.initialize())
    
    # 啟動 Flask 伺服器，監聽 Render 指定的 Port
    app.run(host="0.0.0.0", port=PORT)