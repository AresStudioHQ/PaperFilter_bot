import os
import json
import asyncio
import urllib.parse
import random
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import feedparser

TOKEN = "8933939727:AAGqGDok3XMo1Ppm1ZvduAD80554N51ILUQ"
SEEN_FILE = 'seen_papers.txt'
CONFIG_FILE = 'categories.json'

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ========================== 工具函式 ==========================
def load_categories():
    if not os.path.exists(CONFIG_FILE):
        default = {'cat_1': '生物生態', 'cat_2': '人工智慧', 'cat_3': '金融市場', 'cat_4': '綜合科學'}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_categories(categories):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(categories, f, ensure_ascii=False, indent=4)

def load_seen_papers():
    if not os.path.exists(SEEN_FILE): return set()
    with open(SEEN_FILE, 'r', encoding='utf-8') as f: return set(line.strip() for line in f)

def save_seen_paper(link):
    with open(SEEN_FILE, 'a', encoding='utf-8') as f: f.write(link + '\n')

def save_to_folder(folder_name, title, link):
    os.makedirs(folder_name, exist_ok=True)
    with open(os.path.join(folder_name, "saved_papers.txt"), 'a', encoding='utf-8') as f:
        f.write(f"標題: {title}\n連結: {link}\n{'-'*50}\n")

def fetch_unseen_paper_by_keyword(user_input):
    seen = load_seen_papers()
    url = f'http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(user_input)}&max_results=50&sortBy=submittedDate&sortOrder=descending'
    try:
        feed = feedparser.parse(url)
        unseen = [e for e in feed.entries if e.link not in seen]
        if unseen:
            e = random.choice(unseen)
            return e.title.strip().replace('\n', ' '), e.summary.strip().replace('\n', ' ')[:250] + "...", e.link
    except: pass
    return None, None, None

# ========================== 核心邏輯 ==========================

async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "<b>🤖 專屬論文管家 - 操作指引</b>\n\n• 輸入關鍵字：搜尋論文\n• 新增：<code>新增 名稱</code>\n• 改名：<code>改名 舊to新</code>\n• 移除：<code>移除 名稱</code>"
    await update.message.reply_text(help_text, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("歡迎！請輸入關鍵字或使用選單功能。")
    await send_help(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if user_text in ['/help', '說明書', '功能']:
        await send_help(update, context)
        
    # 1. 新增資料夾：直接打 +量子物理
        if user_text.startswith('新增'):
            new_name = user_text.replace('新增', '').strip()
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
        if user_text.startswith('移除'):
            target_name = user_text.replace('移除', '').strip()
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
                f"• 新增：<code>新增 資料夾名稱</code> (例：<code>新增 量子物理</code>)\n"
                f"• 改名：<code>改名 舊名稱to新名稱</code> (例：<code>改名 量子物理to統計學</code>)\n"
                f"• 移除：<code>移除 資料夾名稱</code> (例：<code>移除 量子物理</code>)\n"
                f"• 查看說明：輸入 <code>/help</code>"
            )
            await update.message.reply_text(help_msg, parse_mode='HTML')
            return
        
    # 搜尋論文
    await update.message.reply_text(f"🔍 正在搜尋【{user_text}】...")
    title, summary, link = fetch_unseen_paper_by_keyword(user_text)
    if not title:
        await update.message.reply_text("😅 找不到新論文。")
        return
    
    context.user_data['current_title'], context.user_data['current_link'] = title, link
    cats = load_categories()
    keyboard = [[InlineKeyboardButton(name, callback_data=cid) for cid, name in cats.items()]]
    keyboard.append([InlineKeyboardButton("❌ 略過", callback_data='skip')])
    await update.message.reply_text(f"📚 {title}\n\n🔗 <a href='{link}'>閱讀原文</a>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

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

# 註冊
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_callback))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    await application.initialize()
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))