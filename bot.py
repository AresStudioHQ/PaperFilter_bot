import os
import sys
import json
import threading
import time
import re
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, abort
from dotenv import load_dotenv

load_dotenv()

# 引用搜尋與資料庫引擎
import search_engine
from database import db

# 學術權威分級
try:
    import academic_tiers
    academic_tiers_imported = True
except ImportError:
    academic_tiers = None
    academic_tiers_imported = False

# 引用 Google Drive 模組 (安全容錯)
try:
    from gdrive_sync import drive_manager
except ImportError:
    class DummyDriveManager:
        def get_auth_url(self, user_id): return None
        def exchange_code(self, user_id, code): return False
        def archive_paper(self, **kwargs): return False, "Google Drive 模組未載入"
        def rename_folder(self, *args): pass
        def mark_folder_deleted(self, *args): pass
    drive_manager = DummyDriveManager()

# 暫存搜尋結果論文資料（供歸檔時使用）
_pending_papers = {}

# 追蹤用戶首次使用功能
_user_first_use = set()
# 追蹤用戶對話模式（{user_id: True}）
_chat_mode_users = {}

# ===================== 1. 完整 4 國語系文字辭典 =====================
MESSAGES = {
    "zh_hant": {
        "welcome": (
            "👋 嗨 <b>{name}</b>，歡迎使用 <b>PaperFilterBot 科研大總部</b>！\n\n"
            "🔬 <b>核心科研特權</b>：\n"
            "• 4 大官方學術庫交叉檢索 (arXiv / PubMed / Semantic Scholar / CrossRef)\n"
            "• 💡 4 維 AI 深度導讀（研究動機、核心方法、關鍵結論、技術限制）\n"
            "• 💬 跨論文 RAG 智慧問答（<code>/chat [問題]</code>）\n"
            "• ☁️ Google Drive 雙軌自動歸檔 + <code>references.bib</code> 即時生成\n\n"
            "👇 請選擇下方快捷功能，或直接在聊天室發送<b>論文關鍵字</b>進行檢索："
        ),
        "help": (
            "📖 <b>PaperFilterBot 全指令導覽</b>\n\n"
            "🔍 <b>論文檢索</b>：直接在聊天室發送關鍵字（例如：LLM Agent）\n"
            "💬 <b>/chat</b> - 切換跨文獻問答模式（進入後直接輸入問題）\n"
            "📚 <b>/my</b> - 查看我的文獻庫、分類資料夾與 Drive 狀態\n"
            "🔗 <b>/bind</b> - 取得 6 位數同步代碼，綁定網頁科研大總部\n"
            "💎 <b>/pro</b> - 查看方案比較與升級資訊\n"
            "📂 <b>/following</b> - 管理追蹤學者與關鍵字\n"
            "➕ <b>/follow [學者]</b> - 追蹤頂級學者最新著作\n"
            "➖ <b>/unfollow [學者]</b> - 取消追蹤學者\n"
            "📑 <b>/review [主題]</b> - AI 一鍵生成多篇論文文獻綜述\n"
            "🔍 <b>/gap</b> - 自動分析目前收藏文獻的研究盲點與缺口\n"
            "📈 <b>/trend [領域]</b> - 分析領域近年發表年份與 AI 趨勢\n"
            "📋 <b>/export</b> - 匯出收藏文獻為 BibTeX / RIS / CSV\n"
            "⚙️ <b>/mode</b> - 切換論文過濾模式（頂刊 / 智慧 / OA 免費）\n"
            "🌐 <b>/lang</b> - 切換多國語言\n"
            "📊 <b>/reports</b> - 產生個人文獻綜述歷史報告\n"
            "☁️ <b>/drive</b> - 連結或檢查 Google Drive 雲端同步狀態\n"
            "💻 <b>/web</b> - 取得網頁端科研大總部網址\n\n"
            "💡 提示：直接輸入關鍵字即可搜尋論文！"
        ),
        "btn_search": "🔍 檢索論文",
        "btn_web": "💻 開啟科研大總部",
        "btn_bind": "🔗 綁定同步碼",
        "btn_pro": "💎 Pro 專區",
        "btn_lang": "🌐 切換語言",
        "btn_deep": "💡 深度導讀",
        "btn_seen": "👀 看過了",
        "btn_skip": "👎 沒興趣",
        "btn_archive": "☁️ 歸檔到雲端",
        "btn_oa": "🟢 免費全文 (OA)",
        "btn_doi": "🔗 官方 DOI 頁面",
        "btn_hot_transformer": "🔍 熱門：Transformer",
        "btn_hot_crispr": "🧬 熱門：CRISPR",
        "btn_bind_web": "🔗 綁定網頁端",
        "btn_view_pro": "👑 查看 Pro 特權",
        "btn_full_help": "📖 完整指令幫助",
        "read_paper": "查看原始文獻",
        "searching": "🔍 正在跨庫檢索「{query}」，請稍候...",
        "not_found": "❌ 找不到與「{query}」相關的文獻，建議更換關鍵字。",
        "search_error": "⚠️ 檢索過程發生暫時性網路錯誤，請稍候重試。",
        "lang_switch_title": "🌐 請選擇您偏好的介面語言（目前：{current}）：",
        "lang_switched": "✅ 介面語言已更新成功！",
        "mode_title": "⚙️ 請選擇文獻過濾模式（目前：{current}）：",
        "mode_top": "🏆 頂級期刊/頂會 (Top-Tier)",
        "mode_smart": "⚡ 智慧精選 (Smart Balanced)",
        "mode_free": "🟢 僅免費全文 (Open Access)",
        "mode_switched": "✅ 已切換為模式：{mode}",
        "deep_processing": "🧠 AI 正在研讀全文並萃取 4 維結構化要點，請稍候...",
        "deep_header": "💡 <b>AI 4 維深度導讀報告</b>",
        "bibtex_header": "📋 <b>BibTeX 引用文獻條目</b>",
        "mark_seen": "👁 已標記為已讀並調整個人推薦偏好：{title}",
        "mark_skip": "⏭ 已略過並降低同類權重：{title}",
        "archive_success": "✅ 已成功將《{title}》歸檔至 Google Drive 資料夾【{folder}】！",
        "archive_failed": "❌ 歸檔失敗：{detail}",
        "folder_added": "📁 已成功新增資料夾：【{name}】",
        "folder_renamed": "📁 資料夾已改名：【{old}】➡️【{new}】",
        "folder_deleted": "🗑 已刪除資料夾：【{name}】",
        "folder_not_found": "❌ 找不到指定資料夾：【{name}】",
        "my_folders": "📁 <b>您的自訂歸檔資料夾：</b>\n\n{list}",
        "no_custom_folders": "📂 目前尚無自訂資料夾，可直接輸入「新增 資料夾名稱」建立。",
        "follow_success": "✅ 已成功追蹤學者：<b>{name}</b>",
        "unfollow_success": "✅ 已取消追蹤學者：<b>{name}</b>",
        "unfollow_failed": "❌ 取消追蹤失敗，您可能未曾追蹤過此學者。",
        "no_following": "您目前尚未追蹤任何學者，可使用 <code>/follow 學者姓名</code> 進行追蹤。",
        "following_list": "👥 <b>您追蹤的學者名單：</b>\n\n{list}",
        "default_categories": ["Artificial Intelligence", "Bio & Life Sciences", "General Science", "Human Genetics"],
        "tier_free": "免費版",
        "tier_basic": "Basic 方案",
        "tier_standard": "Standard 方案",
        "tier_premium": "Premium 方案",
        "tier_ultra": "Ultra 方案",
        "tier_price": "{price}/月",
        "tier_search_daily": "{count} 次搜尋/日",
        "tier_deep_daily": "{count} 次深度導讀/日",
        "tier_chat": "跨文獻問答",
        "tier_review": "文獻綜述",
        "tier_gap": "研究缺口",
        "tier_drive": "Google Drive 歸檔",
        "tier_drive_limit": "{count} 篇/月",
        "tier_drive_unlimited": "無限",
        "tier_follow": "追蹤學者",
        "tier_folder": "自訂資料夾",
        "tier_export": "匯出功能",
        "tier_report": "AI 分析報告",
        "tier_report_none": "無",
        "tier_report_monthly": "每月 1 份",
        "tier_report_weekly": "每週 1 份",
        "tier_report_daily": "每日 1 份",
        "tier_ads": "網頁端廣告",
        "tier_ads_none": "無廣告",
        "tier_ads_show": "有廣告",
        "tier_unlock": "解鎖",
        "tier_locked": "需升級",
        "tier_current": "目前方案",
        "tier_upgrade": "升級方案",
        "upgrade_title": "🔒 此功能需要升級方案",
        "upgrade_current_tier": "您目前的方案",
        "upgrade_compare": "方案比較",
        "upgrade_btn": "查看升級方案",
        "upgrade_drive_limited": "本月 Drive 額度已用完，下個月自動同步",
        "tier_plan_comparison": "📊 方案比較",
        "tier_basic_price": "Basic",
        "tier_standard_price": "Standard",
        "tier_premium_price": "Premium",
        "tier_ultra_price": "Ultra",
        "chat_exit": "✅ 已退出<b>跨文獻問答模式</b>。\n\n輸入 /chat 可重新進入。",
        "chat_enter": "💬 <b>已進入跨文獻問答模式</b>\n\n📚 您的文獻庫：{count} 篇論文\n\n現在可以直接輸入問題，例如：\n• 這些論文在方法論上有何異同？\n• 哪一篇最適合用在邊緣運算？\n• 這些研究有什麼共同限制？\n\n輸入 /chat 退出此模式。",
        "chat_first_use": "👋 <b>首次使用跨文獻問答</b>\n\n此功能會從您文獻庫中找到相關論文，進行<b>跨篇交叉分析</b>。\n\n💡 建議提問方向：\n• 比較類：「這些論文在[方法/結果]上有何差異？」\n• 推薦類：「哪一篇最適合[我的場景]？」\n• 缺口類：「這些研究有哪些共同限制？」\n\n⏳ 首次分析可能需要 10-20 秒，請稍候...",
        "chat_empty_library": "📂 您目前文獻庫中沒有論文。請先搜尋並歸檔幾篇論文後再來提問！",
        "chat_loading": "🧠 <b>AI 正在跨 {count} 篇文獻進行深入關聯檢索與分析，請稍候...</b>",
        "chat_header": "💬 <b>跨論文解答報告</b>\n❓ <i>問題：{query}</i>\n\n",
        "chat_disclaimer": "\n\n---\n📚 <i>以上分析僅基於您文獻庫中的論文，不代表全域學術觀點。如需更多功能，升級 Pro 方案可享無限次問答。</i>",
        "reports_empty": "📝 您目前尚無生成的文獻綜述報告。可使用 <code>/review 主題</code> 立即生成！",
        "reports_list_header": "📑 <b>您生成的學術綜述報告清單（共 {count} 份）：</b>\n\n",
        "reports_list_footer": "\n可在網頁端科研大總部查看全文與匯出 Markdown/PDF！",
        "follow_missing_args": "請輸入學者名稱，例如：<code>/follow Yann LeCun</code>",
        "unfollow_missing_args": "請輸入要取消追蹤的學者名稱。",
        "drive_connected": "✅ 您的 Google Drive 已成功連結！可以直接歸檔論文與同步 references.bib。",
        "drive_auth_prompt": "請點擊下方按鈕授權 Google Drive 存取：",
        "drive_auth_button": "🔗 授權 Google Drive",
        "drive_oauth_not_configured": "❌ Google OAuth 設定未完成，請確認 .env 設定。",
        "drive_auth_success": "✅ Google Drive 授權成功！現在可以隨時將論文歸檔至雲端。",
        "search_missing_args": "請輸入關鍵字，例如：<code>/search CRISPR</code>",
        "review_empty": "您尚未收藏任何論文。請先搜尋並歸檔論文後再使用。",
        "review_loading": "🧠 正在為您的 {count} 篇論文生成高階學術文獻綜述，請稍候...",
        "gap_empty": "您尚未收藏任何論文。請先搜尋並歸檔論文後再使用。",
        "gap_loading": "🔍 正在深入分析 {count} 篇論文的研究缺口與盲點，請稍候...",
        "trend_loading": "📈 正在分析「{topic}」的國際學術趨勢，請稍候...",
        "trend_year_format": "{year}年:{count}篇",
        "trend_result_header": "📊 <b>「{topic}」研究趨勢分析</b>\n\n📚 找到相關論文：{count} 篇\n📅 發表年份分佈：{year_str}\n\n",
        "trend_ai_analysis": "🤖 <b>AI 趨勢解析：</b>\n{analysis}",
        "export_empty": "您尚未收藏任何論文。",
        "export_prompt": "📚 您共有 {count} 篇論文，請選擇匯出方式：",
        "export_all_button": "📦 全部匯出 ({count} 篇)",
        "export_select_button": "☑️ 勾選匯出",
        "export_format_prompt": "請選擇匯出格式：",
        "export_select_prompt": "☑️ <b>請點選要匯出的論文</b>（已選：{count} 篇）\n\n",
        "export_confirm_button": "✅ 確認匯出",
        "export_cancel_button": "❌ 取消",
        "export_selected_count": "已選 {count} 篇",
        "export_no_selection": "請先選擇至少一篇論文",
        "export_cancelled": "❌ 已取消匯出。",
        "export_cancel_callback": "已取消",
        "export_no_papers": "沒有論文可匯出",
        "export_generating": "📄 正在生成 {fmt} 格式...",
        "export_result_caption": "📄 <b>{fmt} 匯出結果</b>\n📚 共 {count} 篇論文\n\n可直接匯入 Zotero / EndNote / Mendeley",
        "export_selected_format": "已選 {count} 篇論文，請選擇匯出格式：",
        "archive_choose_folder": "📁 請選擇要歸檔的資料夾：",
        "archive_skip_button": "🔙 返回",
        "archive_invalid_button": "❌ 按鈕無效",
        "archive_skip_archive": "⏭ 已略過歸檔",
        "archive_archiving": "☁️ 歸檔中...",
        "archive_drive_auth_prompt": "請先授權 Google Drive：",
        "archive_drive_auth_button": "🔗 授權 Google Drive",
        "archive_drive_not_configured": "❌ Google OAuth 未設定。",
        "my_title": "📚 <b>您的個人科研文獻庫總覽</b>\n\n",
        "my_tier_label": "👤 會員等級：{tier}",
        "my_drive_status_label": "☁️ Google Drive 狀態：{status}",
        "my_drive_connected": "🟢 已連結",
        "my_drive_disconnected": "⚪ 未連結（可用 /drive 授權）",
        "my_paper_count": "📑 收藏論文數量：共 <b>{count}</b> 篇",
        "my_folders_label": "📁 自訂資料夾：{folders}",
        "my_default_folders": "預設分類",
        "my_recent_papers": "<b>🕒 最近收藏文獻（最新 3 篇）：</b>\n{list}",
        "my_recent_hint": "\n💡 提示：使用 <code>/chat 您的研究問題</code> 可跨文獻向 AI 提問；使用 <code>/export</code> 可批次匯出引用格式。",
        "my_empty_library": "您目前尚未收藏任何論文。\n搜尋論文後點擊卡片下方的【☁️ 歸檔到雲端】即可將論文加入文獻庫！",
        "my_export_button": "📄 匯出文獻庫",
        "my_drive_button": "☁️ Drive 授權",
        "bind_title": "🔗 <b>網頁科研大總部同步帳號綁定</b>\n\n",
        "bind_code": "您的專屬 6 位數同步碼為：<code>{code}</code>\n\n",
        "bind_instructions": "💻 請在瀏覽器打開 PaperFilterBot 科研大總部，點擊右上角<b>【綁定 Telegram】</b>輸入此代碼。\n綁定後，您在 Telegram 的所有標記（看過/略過/歸檔/筆記）將與網頁端全功能儀表板雙向同步！",
        "help_bind_button": "🔗 綁定網頁端",
        "help_pro_button": "👑 查看 Pro 特權",
        "unknown_command": "❌ 沒有此指令：{cmd}\n請輸入 /help 查看所有可用指令。",
        "paper_et_al": "等 {count} 位",
        "paper_seen_badge": "👁 [已看過]",
        "paper_ai_summary": "🧠 <b>AI 導讀：</b>\n{text}",
        "card_citations": "引用",
        "card_disclaimer": "AI 摘要僅供快速理解，正式引用請核對原文。",
        "deep_disclaimer": "此深度導讀由 AI 根據論文摘要生成，僅供快速理解，正式引用請務必核對原文。",
        "mode_switched_confirm": "✅ 已切換為 {mode}",
        "lang_switched_confirm": "✅ 語言已切換為 {lang}",
        "mark_seen_callback": "👁 已標記為已讀",
        "mark_skip_callback": "❌ 已略過",
        "pro_text": (
            "📊 <b>PaperFilterBot 方案比較</b>\n\n"
            "👤 您目前方案：{tier}\n\n"
            "🆓 <b>Free 免費版</b>\n"
            "• 搜尋：10 次/日\n"
            "• 深度導讀：1 次/日\n"
            "• Drive：5 篇/月\n"
            "• 廣告：有\n\n"
            "🔧 <b>Basic</b>\n"
            "• 搜尋：30 次/日\n"
            "• 深度導讀：5 次/日\n"
            "• /chat 跨文獻問答：10 次/月\n"
            "• Drive：30 篇/月\n"
            "• 無廣告\n\n"
            "⭐ <b>Standard</b>\n"
            "• 搜尋：100 次/日\n"
            "• 深度導讀：15 次/日\n"
            "• /review 文獻綜述 + /gap 研究缺口\n"
            "• Drive：100 篇/月\n"
            "• 每月 AI 分析報告\n\n"
            "💎 <b>Premium</b>\n"
            "• 搜尋：200 次/日\n"
            "• 深度導讀：30 次/日\n"
            "• 所有功能大幅增加\n"
            "• Drive：無限\n"
            "• 每週 AI 分析報告\n\n"
            "👑 <b>Ultra</b>\n"
            "• 搜尋：500 次/日\n"
            "• 深度導讀：50 次/日\n"
            "• 所有功能無限\n"
            "• 每日 AI 分析報告\n\n"
            "💡 可在科研大總部一鍵升級！"
        ),
    },
    "zh_hans": {
        "welcome": (
            "👋 嗨 <b>{name}</b>，欢迎使用 <b>PaperFilterBot 科研大总部</b>！\n\n"
            "🔬 <b>核心科研特权</b>：\n"
            "• 4 大官方学术库交叉检索 (arXiv / PubMed / Semantic Scholar / CrossRef)\n"
            "• 💡 4 维 AI 深度导读（研究动机、核心方法、关键结论、技术限制）\n"
            "• 💬 跨论文 RAG 智能问答（<code>/chat [问题]</code>）\n"
            "• ☁️ Google Drive 双轨自动归档 + <code>references.bib</code> 实时生成\n\n"
            "👇 请选择下方快捷功能，或直接在聊天室发送<b>论文关键词</b>进行检索："
        ),
        "help": (
            "📖 <b>PaperFilterBot 全指令导览</b>\n\n"
            "🔍 <b>论文检索</b>：直接在聊天室发送关键词（例如：LLM Agent）\n"
            "💬 <b>/chat</b> - 切换跨文献问答模式（进入后直接输入问题）\n"
            "📚 <b>/my</b> - 查看我的文献库、分类文件夹与 Drive 状态\n"
            "🔗 <b>/bind</b> - 获取 6 位数同步代码，绑定网页科研大总部\n"
            "💎 <b>/pro</b> - 查看方案比较与升级信息\n"
            "📂 <b>/following</b> - 管理追踪学者与关键词\n"
            "➕ <b>/follow [学者]</b> - 追踪顶级学者最新著作\n"
            "➖ <b>/unfollow [学者]</b> - 取消追踪学者\n"
            "📑 <b>/review [主题]</b> - AI 一键生成多篇论文文献综述\n"
            "🔍 <b>/gap</b> - 自动分析目前收藏文献的研究盲点与缺口\n"
            "📈 <b>/trend [领域]</b> - 分析领域近年发表年份与 AI 趋势\n"
            "📋 <b>/export</b> - 导出收藏文献为 BibTeX / RIS / CSV\n"
            "⚙️ <b>/mode</b> - 切换论文过滤模式（顶刊 / 智能 / OA 免费）\n"
            "🌐 <b>/lang</b> - 切换多国语言\n"
            "📊 <b>/reports</b> - 生成个人文献综述历史报告\n"
            "☁️ <b>/drive</b> - 链接或检查 Google Drive 云端同步状态\n"
            "💻 <b>/web</b> - 获取网页端科研大总部网址\n\n"
            "💡 提示：直接输入关键词即可搜寻论文！"
        ),
        "btn_search": "🔍 检索论文",
        "btn_web": "💻 开启科研大总部",
        "btn_bind": "🔗 绑定同步码",
        "btn_pro": "💎 Pro 专区",
        "btn_lang": "🌐 切换语言",
        "btn_deep": "💡 深度导读",
        "btn_seen": "👀 看过了",
        "btn_skip": "👎 没兴趣",
        "btn_archive": "☁️ 归档到云端",
        "btn_oa": "🟢 免费全文 (OA)",
        "btn_doi": "🔗 官方 DOI 页面",
        "btn_hot_transformer": "🔍 热门：Transformer",
        "btn_hot_crispr": "🧬 热门：CRISPR",
        "btn_bind_web": "🔗 绑定网页端",
        "btn_view_pro": "👑 查看 Pro 特权",
        "btn_full_help": "📖 完整指令帮助",
        "read_paper": "查看原始文献",
        "searching": "🔍 正在跨库检索「{query}」，请稍候...",
        "not_found": "❌ 找不到与「{query}」相关的文献，建议更换关键词。",
        "search_error": "⚠️ 检索过程发生暂时性网络错误，请稍候重试。",
        "lang_switch_title": "🌐 请选择您偏好的界面语言（当前：{current}）：",
        "lang_switched": "✅ 界面语言已更新成功！",
        "mode_title": "⚙️ 请选择文献过滤模式（当前：{current}）：",
        "mode_top": "🏆 顶级期刊/顶会 (Top-Tier)",
        "mode_smart": "⚡ 智能精选 (Smart Balanced)",
        "mode_free": "🟢 仅免费全文 (Open Access)",
        "mode_switched": "✅ 已切换为模式：{mode}",
        "deep_processing": "🧠 AI 正在研读全文并萃取 4 维结构化要点，请稍候...",
        "deep_header": "💡 <b>AI 4 维深度导读报告</b>",
        "bibtex_header": "📋 <b>BibTeX 引用文献条目</b>",
        "mark_seen": "👁 已标记为已读并调整个人推荐偏好：{title}",
        "mark_skip": "⏭ 已略过并降低同类权重：{title}",
        "archive_success": "✅ 已成功将《{title}》归档至 Google Drive 文件夹【{folder}】！",
        "archive_failed": "❌ 归档失败：{detail}",
        "folder_added": "📁 已成功新增文件夹：【{name}】",
        "folder_renamed": "📁 文件夹已改名：【{old}】➡️【{new}】",
        "folder_deleted": "🗑 已删除文件夹：【{name}】",
        "folder_not_found": "❌ 找不到指定文件夹：【{name}】",
        "my_folders": "📁 <b>您的自定义归档文件夹：</b>\n\n{list}",
        "no_custom_folders": "📂 目前尚无自定义文件夹，可直接输入「新增 文件夹名称」建立。",
        "follow_success": "✅ 已成功追踪学者：<b>{name}</b>",
        "unfollow_success": "✅ 已取消追踪学者：<b>{name}</b>",
        "unfollow_failed": "❌ 取消追踪失败，您可能未曾追踪过此学者。",
        "no_following": "您目前尚未追踪任何学者，可使用 <code>/follow 学者姓名</code> 进行追踪。",
        "following_list": "👥 <b>您追踪的学者名单：</b>\n\n{list}",
        "default_categories": ["Artificial Intelligence", "Bio & Life Sciences", "General Science", "Human Genetics"],
        "tier_free": "免费版",
        "tier_basic": "Basic 方案",
        "tier_standard": "Standard 方案",
        "tier_premium": "Premium 方案",
        "tier_ultra": "Ultra 方案",
        "tier_price": "{price}/月",
        "tier_search_daily": "{count} 次搜索/日",
        "tier_deep_daily": "{count} 次深度导读/日",
        "tier_chat": "跨文献问答",
        "tier_review": "文献综述",
        "tier_gap": "研究缺口",
        "tier_drive": "Google Drive 归档",
        "tier_drive_limit": "{count} 篇/月",
        "tier_drive_unlimited": "无限",
        "tier_follow": "追踪学者",
        "tier_folder": "自订文件夹",
        "tier_export": "导出功能",
        "tier_report": "AI 分析报告",
        "tier_report_none": "无",
        "tier_report_monthly": "每月 1 份",
        "tier_report_weekly": "每周 1 份",
        "tier_report_daily": "每日 1 份",
        "tier_ads": "网页端广告",
        "tier_ads_none": "无广告",
        "tier_ads_show": "有广告",
        "tier_unlock": "解锁",
        "tier_locked": "需升级",
        "tier_current": "当前方案",
        "tier_upgrade": "升级方案",
        "upgrade_title": "🔒 此功能需要升级方案",
        "upgrade_current_tier": "您当前的方案",
        "upgrade_compare": "方案比较",
        "upgrade_btn": "查看升级方案",
        "upgrade_drive_limited": "本月 Drive 额度已用完，下个月自动同步",
        "tier_plan_comparison": "📊 方案比较",
        "tier_basic_price": "Basic",
        "tier_standard_price": "Standard",
        "tier_premium_price": "Premium",
        "tier_ultra_price": "Ultra",
        "chat_exit": "✅ 已退出<b>跨文献问答模式</b>。\n\n输入 /chat 可重新进入。",
        "chat_enter": "💬 <b>已进入跨文献问答模式</b>\n\n📚 您的文献库：{count} 篇论文\n\n现在可以直接输入问题，例如：\n• 这些论文在方法论上有何异同？\n• 哪一篇最适合用在边缘运算？\n• 这些研究有什么共同限制？\n\n输入 /chat 退出此模式。",
        "chat_first_use": "👋 <b>首次使用跨文献问答</b>\n\n此功能会从您文献库中找到相关论文，进行<b>跨篇交叉分析</b>。\n\n💡 建议提问方向：\n• 比较类：「这些论文在[方法/结果]上有何差异？」\n• 推荐类：「哪一篇最适合[我的场景]？」\n• 缺口类：「这些研究有哪些共同限制？」\n\n⏳ 首次分析可能需要 10-20 秒，请稍候...",
        "chat_empty_library": "📂 您目前文献库中没有论文。请先搜索并归档几篇论文后再来提问！",
        "chat_loading": "🧠 <b>AI 正在跨 {count} 篇文献进行深入关联检索与分析，请稍候...</b>",
        "chat_header": "💬 <b>跨论文解答报告</b>\n❓ <i>问题：{query}</i>\n\n",
        "chat_disclaimer": "\n\n---\n📚 <i>以上分析仅基于您文献库中的论文，不代表全域学术观点。如需更多功能，升级 Pro 方案可享无限次问答。</i>",
        "reports_empty": "📝 您目前尚无生成的文献综述报告。可使用 <code>/review 主题</code> 立即生成！",
        "reports_list_header": "📑 <b>您生成的学术综述报告清单（共 {count} 份）：</b>\n\n",
        "reports_list_footer": "\n可在网页端科研大总部查看全文与导出 Markdown/PDF！",
        "follow_missing_args": "请输入学者名称，例如：<code>/follow Yann LeCun</code>",
        "unfollow_missing_args": "请输入要取消追踪的学者名称。",
        "drive_connected": "✅ 您的 Google Drive 已成功链接！可以直接归档论文与同步 references.bib。",
        "drive_auth_prompt": "请点击下方按钮授权 Google Drive 访问：",
        "drive_auth_button": "🔗 授权 Google Drive",
        "drive_oauth_not_configured": "❌ Google OAuth 设定未完成，请确认 .env 设定。",
        "drive_auth_success": "✅ Google Drive 授权成功！现在可以随时将论文归档至云端。",
        "search_missing_args": "请输入关键词，例如：<code>/search CRISPR</code>",
        "review_empty": "您尚未收藏任何论文。请先搜索并归档论文后再使用。",
        "review_loading": "🧠 正在为您的 {count} 篇论文生成高阶学术文献综述，请稍候...",
        "gap_empty": "您尚未收藏任何论文。请先搜索并归档论文后再使用。",
        "gap_loading": "🔍 正在深入分析 {count} 篇论文的研究缺口与盲点，请稍候...",
        "trend_loading": "📈 正在分析「{topic}」的国际学术趋势，请稍候...",
        "trend_year_format": "{year}年:{count}篇",
        "trend_result_header": "📊 <b>「{topic}」研究趋势分析</b>\n\n📚 找到相关论文：{count} 篇\n📅 发表年份分布：{year_str}\n\n",
        "trend_ai_analysis": "🤖 <b>AI 趋势解析：</b>\n{analysis}",
        "export_empty": "您尚未收藏任何论文。",
        "export_prompt": "📚 您共有 {count} 篇论文，请选择导出方式：",
        "export_all_button": "📦 全部导出 ({count} 篇)",
        "export_select_button": "☑️ 勾选导出",
        "export_format_prompt": "请选择导出格式：",
        "export_select_prompt": "☑️ <b>请点击要导出的论文</b>（已选：{count} 篇）\n\n",
        "export_confirm_button": "✅ 确认导出",
        "export_cancel_button": "❌ 取消",
        "export_selected_count": "已选 {count} 篇",
        "export_no_selection": "请先选择至少一篇论文",
        "export_cancelled": "❌ 已取消导出。",
        "export_cancel_callback": "已取消",
        "export_no_papers": "没有论文可导出",
        "export_generating": "📄 正在生成 {fmt} 格式...",
        "export_result_caption": "📄 <b>{fmt} 导出结果</b>\n📚 共 {count} 篇论文\n\n可直接导入 Zotero / EndNote / Mendeley",
        "export_selected_format": "已选 {count} 篇论文，请选择导出格式：",
        "archive_choose_folder": "📁 请选择要归档的文件夹：",
        "archive_skip_button": "🔙 返回",
        "archive_invalid_button": "❌ 按钮无效",
        "archive_skip_archive": "⏭ 已跳过归档",
        "archive_archiving": "☁️ 归档中...",
        "archive_drive_auth_prompt": "请先授权 Google Drive：",
        "archive_drive_auth_button": "🔗 授权 Google Drive",
        "archive_drive_not_configured": "❌ Google OAuth 未设定。",
        "my_title": "📚 <b>您的个人科研文献库总览</b>\n\n",
        "my_tier_label": "👤 会员等级：{tier}",
        "my_drive_status_label": "☁️ Google Drive 状态：{status}",
        "my_drive_connected": "🟢 已链接",
        "my_drive_disconnected": "⚪ 未链接（可用 /drive 授权）",
        "my_paper_count": "📑 收藏论文数量：共 <b>{count}</b> 篇",
        "my_folders_label": "📁 自定义文件夹：{folders}",
        "my_default_folders": "预设分类",
        "my_recent_papers": "<b>🕒 最近收藏文献（最新 3 篇）：</b>\n{list}",
        "my_recent_hint": "\n💡 提示：使用 <code>/chat 您的研究问题</code> 可跨文献向 AI 提问；使用 <code>/export</code> 可批次导出引用格式。",
        "my_empty_library": "您目前尚未收藏任何论文。\n搜索论文后点击卡片下方的【☁️ 归档到云端】即可将论文加入文献库！",
        "my_export_button": "📄 导出文献库",
        "my_drive_button": "☁️ Drive 授权",
        "bind_title": "🔗 <b>网页科研大总部同步帐号绑定</b>\n\n",
        "bind_code": "您的专属 6 位数同步码为：<code>{code}</code>\n\n",
        "bind_instructions": "💻 请在浏览器打开 PaperFilterBot 科研大总部，点击右上角<b>【绑定 Telegram】</b>输入此代码。\n绑定后，您在 Telegram 的所有标记（看过/跳过/归档/笔记）将与网页端全功能仪表板双向同步！",
        "help_bind_button": "🔗 绑定网页端",
        "help_pro_button": "👑 查看 Pro 特权",
        "unknown_command": "❌ 没有此指令：{cmd}\n请输入 /help 查看所有可用指令。",
        "paper_et_al": "等 {count} 位",
        "paper_seen_badge": "👁 [已看过]",
        "paper_ai_summary": "🧠 <b>AI 导读：</b>\n{text}",
        "card_citations": "引用",
        "card_disclaimer": "AI 摘要仅供快速理解，正式引用请核对原文。",
        "deep_disclaimer": "此深度导读由 AI 根据论文摘要生成，仅供快速理解，正式引用请务必核对原文。",
        "mode_switched_confirm": "✅ 已切换为 {mode}",
        "lang_switched_confirm": "✅ 语言已切换为 {lang}",
        "mark_seen_callback": "👁 已标记为已读",
        "mark_skip_callback": "❌ 已跳过",
        "pro_text": (
            "📊 <b>PaperFilterBot 方案比较</b>\n\n"
            "👤 您目前方案：{tier}\n\n"
            "🆓 <b>Free 免费版</b>\n"
            "• 搜索：10 次/日\n"
            "• 深度导读：1 次/日\n"
            "• Drive：5 篇/月\n"
            "• 广告：有\n\n"
            "🔧 <b>Basic</b>\n"
            "• 搜索：30 次/日\n"
            "• 深度导读：5 次/日\n"
            "• /chat 跨文献问答：10 次/月\n"
            "• Drive：30 篇/月\n"
            "• 无广告\n\n"
            "⭐ <b>Standard</b>\n"
            "• 搜索：100 次/日\n"
            "• 深度导读：15 次/日\n"
            "• /review 文献综述 + /gap 研究缺口\n"
            "• Drive：100 篇/月\n"
            "• 每月 AI 分析报告\n\n"
            "💎 <b>Premium</b>\n"
            "• 搜索：200 次/日\n"
            "• 深度导读：30 次/日\n"
            "• 所有功能大幅增加\n"
            "• Drive：无限\n"
            "• 每周 AI 分析报告\n\n"
            "👑 <b>Ultra</b>\n"
            "• 搜索：500 次/日\n"
            "• 深度导读：50 次/日\n"
            "• 所有功能无限\n"
            "• 每日 AI 分析报告\n\n"
            "💡 可在科研大总部一键升级！"
        ),
    },
    "en": {
        "welcome": (
            "👋 Hi <b>{name}</b>, welcome to <b>PaperFilterBot HQ</b>!\n\n"
            "🔬 <b>Core Features</b>:\n"
            "• Cross-search 4 scholarly repositories (arXiv, PubMed, Semantic Scholar, CrossRef)\n"
            "• 💡 4-dimension AI Deep Reading (Motivation, Method, Finding, Limits)\n"
            "• 💬 Multi-paper RAG Q&A (<code>/chat [Question]</code>)\n"
            "• ☁️ Google Drive dual archiving & automatic <code>references.bib</code> sync\n\n"
            "👇 Choose a shortcut below or send <b>keywords</b> directly to search:"
        ),
        "help": (
            "📖 <b>PaperFilterBot Command Suite</b>\n\n"
            "🔍 <b>Search</b>: Send keywords directly (e.g. LLM Agent)\n"
            "💬 <b>/chat</b> - Toggle cross-paper Q&A mode (type questions directly)\n"
            "📚 <b>/my</b> - View your library, custom folders & Drive sync\n"
            "🔗 <b>/bind</b> - Generate 6-digit sync code for Web HQ\n"
            "💎 <b>/pro</b> - View plan comparison & upgrade info\n"
            "📂 <b>/following</b> - Manage followed authors & topics\n"
            "➕ <b>/follow [Author]</b> - Track researcher publications\n"
            "➖ <b>/unfollow [Author]</b> - Untrack researcher\n"
            "📑 <b>/review [Topic]</b> - AI Literature Synthesis Review Draft\n"
            "🔍 <b>/gap</b> - Discover research gaps across your library\n"
            "📈 <b>/trend [Field]</b> - Publication year trends & AI analysis\n"
            "📋 <b>/export</b> - Export library to BibTeX / RIS / CSV\n"
            "⚙️ <b>/mode</b> - Toggle filter criteria (Top-Tier / Smart / OA Only)\n"
            "🌐 <b>/lang</b> - Switch interface language\n"
            "📊 <b>/reports</b> - View synthesis report history\n"
            "☁️ <b>/drive</b> - Check Google Drive sync link\n"
            "💻 <b>/web</b> - Open Web Research HQ\n\n"
            "💡 Tip: Just type keywords to search papers!"
        ),
        "btn_search": "🔍 Search Papers",
        "btn_web": "💻 Web Research HQ",
        "btn_bind": "🔗 Sync to Web",
        "btn_pro": "💎 Pro Suite",
        "btn_lang": "🌐 Language",
        "btn_deep": "💡 Deep Reading",
        "btn_seen": "👀 Seen",
        "btn_skip": "👎 Not Interested",
        "btn_archive": "☁️ Cloud Archive",
        "btn_oa": "🟢 Open Access",
        "btn_doi": "🔗 Official DOI",
        "btn_hot_transformer": "🔍 Hot: Transformer",
        "btn_hot_crispr": "🧬 Hot: CRISPR",
        "btn_bind_web": "🔗 Bind to Web HQ",
        "btn_view_pro": "👑 View Pro Features",
        "btn_full_help": "📖 Full Command Guide",
        "read_paper": "Read Full Paper",
        "searching": "🔍 Searching for '{query}' across repositories...",
        "not_found": "❌ No matched papers found for '{query}'.",
        "search_error": "⚠️ Temporary network error, please retry later.",
        "lang_switch_title": "🌐 Select your interface language (Current: {current}):",
        "lang_switched": "✅ Language updated successfully!",
        "mode_title": "⚙️ Select literature filter mode (Current: {current}):",
        "mode_top": "🏆 Top-Tier Venues",
        "mode_smart": "⚡ Smart Balanced",
        "mode_free": "🟢 Open Access Only",
        "mode_switched": "✅ Filter mode set to: {mode}",
        "deep_processing": "🧠 AI is analyzing full text for 4-dimension highlights...",
        "deep_header": "💡 <b>AI Deep Reading Analysis</b>",
        "bibtex_header": "📋 <b>BibTeX Entry</b>",
        "mark_seen": "👁 Marked as read & tuned positive bias: {title}",
        "mark_skip": "⏭ Skipped & reduced category weight: {title}",
        "archive_success": "✅ Saved '{title}' to Google Drive folder [{folder}]!",
        "archive_failed": "❌ Archive failed: {detail}",
        "folder_added": "📁 Added folder: [{name}]",
        "folder_renamed": "📁 Renamed folder: [{old}] ➡️ [{new}]",
        "folder_deleted": "🗑 Deleted folder: [{name}]",
        "folder_not_found": "❌ Folder not found: [{name}]",
        "my_folders": "📁 <b>Your custom archive folders:</b>\n\n{list}",
        "no_custom_folders": "📂 No custom folders yet. Type 'Add FolderName' to create one.",
        "follow_success": "✅ Now tracking author: <b>{name}</b>",
        "unfollow_success": "✅ Unfollowed author: <b>{name}</b>",
        "unfollow_failed": "❌ Untrack failed: Author not found.",
        "no_following": "You are not tracking any authors yet. Use <code>/follow AuthorName</code>.",
        "following_list": "👥 <b>Followed Authors:</b>\n\n{list}",
        "default_categories": ["Artificial Intelligence", "Bio & Life Sciences", "General Science", "Human Genetics"],
        "tier_free": "Free",
        "tier_basic": "Basic Plan",
        "tier_standard": "Standard Plan",
        "tier_premium": "Premium Plan",
        "tier_ultra": "Ultra Plan",
        "tier_price": "{price}/mo",
        "tier_search_daily": "{count} searches/day",
        "tier_deep_daily": "{count} deep reads/day",
        "tier_chat": "Cross-paper Q&A",
        "tier_review": "Literature Review",
        "tier_gap": "Research Gap",
        "tier_drive": "Google Drive Archive",
        "tier_drive_limit": "{count} papers/mo",
        "tier_drive_unlimited": "Unlimited",
        "tier_follow": "Follow Scholars",
        "tier_folder": "Custom Folders",
        "tier_export": "Export",
        "tier_report": "AI Analysis Report",
        "tier_report_none": "None",
        "tier_report_monthly": "1/month",
        "tier_report_weekly": "1/week",
        "tier_report_daily": "1/day",
        "tier_ads": "Web Ads",
        "tier_ads_none": "Ad-Free",
        "tier_ads_show": "With Ads",
        "tier_unlock": "Unlocked",
        "tier_locked": "Requires Upgrade",
        "tier_current": "Current Plan",
        "tier_upgrade": "Upgrade",
        "upgrade_title": "🔒 This feature requires a plan upgrade",
        "upgrade_current_tier": "Your current plan",
        "upgrade_compare": "Plan Comparison",
        "upgrade_btn": "View Upgrade Plans",
        "upgrade_drive_limited": "Monthly Drive quota used up. Resets next month.",
        "tier_plan_comparison": "📊 Plan Comparison",
        "tier_basic_price": "Basic",
        "tier_standard_price": "Standard",
        "tier_premium_price": "Premium",
        "tier_ultra_price": "Ultra",
        "chat_exit": "✅ Exited <b>Cross-Paper Q&A mode</b>.\n\nType /chat to re-enter.",
        "chat_enter": "💬 <b>Entered Cross-Paper Q&A mode</b>\n\n📚 Your library: {count} papers\n\nYou can now type questions directly, e.g.:\n• How do these papers differ in methodology?\n• Which one is best for edge computing?\n• What are the common limitations?\n\nType /chat to exit this mode.",
        "chat_first_use": "👋 <b>First time using Cross-Paper Q&A</b>\n\nThis feature finds relevant papers from your library and performs <b>cross-paper analysis</b>.\n\n💡 Suggested questions:\n• Compare: \"How do these papers differ in [method/results]?\"\n• Recommend: \"Which is best for [my scenario]?\"\n• Gap: \"What are the common limitations?\"\n\n⏳ First analysis may take 10-20 seconds...",
        "chat_empty_library": "📂 Your library has no papers. Search and archive some papers first!",
        "chat_loading": "🧠 <b>AI is analyzing {count} papers for cross-references...</b>",
        "chat_header": "💬 <b>Cross-Paper Answer Report</b>\n❓ <i>Question: {query}</i>\n\n",
        "chat_disclaimer": "\n\n---\n📚 <i>Analysis based only on your library papers. Upgrade to Pro for unlimited Q&A.</i>",
        "reports_empty": "📝 No reports yet. Use <code>/review [Topic]</code> to generate one!",
        "reports_list_header": "📑 <b>Your Literature Reports ({count} total):</b>\n\n",
        "reports_list_footer": "\nView full text & export Markdown/PDF at Web Research HQ!",
        "follow_missing_args": "Enter author name, e.g.: <code>/follow Yann LeCun</code>",
        "unfollow_missing_args": "Enter the author name to unfollow.",
        "drive_connected": "✅ Google Drive connected! You can archive papers & sync references.bib.",
        "drive_auth_prompt": "Click the button below to authorize Google Drive access:",
        "drive_auth_button": "🔗 Authorize Google Drive",
        "drive_oauth_not_configured": "❌ Google OAuth not configured. Check your .env settings.",
        "drive_auth_success": "✅ Google Drive authorized! You can now archive papers to the cloud.",
        "search_missing_args": "Enter keywords, e.g.: <code>/search CRISPR</code>",
        "review_empty": "No papers in your library. Search and archive some first!",
        "review_loading": "🧠 Generating literature review for your {count} papers...",
        "gap_empty": "No papers in your library. Search and archive some first!",
        "gap_loading": "🔍 Analyzing research gaps across {count} papers...",
        "trend_loading": "📈 Analyzing trends in \"{topic}\"...",
        "trend_year_format": "{year}: {count} papers",
        "trend_result_header": "📊 <b>\"{topic}\" Trend Analysis</b>\n\n📚 Papers found: {count}\n📅 Year distribution: {year_str}\n\n",
        "trend_ai_analysis": "🤖 <b>AI Trend Analysis:</b>\n{analysis}",
        "export_empty": "No papers in your library.",
        "export_prompt": "📚 You have {count} papers. Choose export method:",
        "export_all_button": "📦 Export All ({count} papers)",
        "export_select_button": "☑️ Select & Export",
        "export_format_prompt": "Choose export format:",
        "export_select_prompt": "☑️ <b>Select papers to export</b> (Selected: {count})\n\n",
        "export_confirm_button": "✅ Confirm Export",
        "export_cancel_button": "❌ Cancel",
        "export_selected_count": "Selected: {count}",
        "export_no_selection": "Please select at least one paper",
        "export_cancelled": "❌ Export cancelled.",
        "export_cancel_callback": "Cancelled",
        "export_no_papers": "No papers to export",
        "export_generating": "📄 Generating {fmt} format...",
        "export_result_caption": "📄 <b>{fmt} Export</b>\n📚 {count} papers\n\nImport directly to Zotero / EndNote / Mendeley",
        "export_selected_format": "Selected {count} papers. Choose format:",
        "archive_choose_folder": "📁 Choose archive folder:",
        "archive_skip_button": "🔙 Back",
        "archive_invalid_button": "❌ Invalid button",
        "archive_skip_archive": "⏭ Archive skipped",
        "archive_archiving": "☁️ Archiving...",
        "archive_drive_auth_prompt": "Please authorize Google Drive first:",
        "archive_drive_auth_button": "🔗 Authorize Google Drive",
        "archive_drive_not_configured": "❌ Google OAuth not configured.",
        "my_title": "📚 <b>Your Research Library Overview</b>\n\n",
        "my_tier_label": "👤 Plan: {tier}",
        "my_drive_status_label": "☁️ Google Drive: {status}",
        "my_drive_connected": "🟢 Connected",
        "my_drive_disconnected": "⚪ Not connected (use /drive to authorize)",
        "my_paper_count": "📑 Papers saved: <b>{count}</b>",
        "my_folders_label": "📁 Custom folders: {folders}",
        "my_default_folders": "Default categories",
        "my_recent_papers": "<b>🕒 Recent Papers (last 3):</b>\n{list}",
        "my_recent_hint": "\n💡 Tip: Use <code>/chat [Question]</code> for cross-paper Q&A; <code>/export</code> for batch export.",
        "my_empty_library": "No papers yet. Search and click [☁️ Cloud Archive] to add papers!",
        "my_export_button": "📄 Export Library",
        "my_drive_button": "☁️ Drive Auth",
        "bind_title": "🔗 <b>Web Research HQ Account Binding</b>\n\n",
        "bind_code": "Your 6-digit sync code: <code>{code}</code>\n\n",
        "bind_instructions": "💻 Open PaperFilterBot Web HQ and click <b>【Bind Telegram】</b> to enter this code.\nAll your marks (seen/skip/archive/notes) will sync bidirectionally!",
        "help_bind_button": "🔗 Bind to Web",
        "help_pro_button": "👑 View Pro Features",
        "unknown_command": "❌ Unknown command: {cmd}\nType /help to see all commands.",
        "paper_et_al": "et al. ({count} authors)",
        "paper_seen_badge": "👁 [Seen]",
        "paper_ai_summary": "🧠 <b>AI Summary:</b>\n{text}",
        "card_citations": "citations",
        "card_disclaimer": "AI summary for quick reference only. Please verify against the original paper before citing.",
        "deep_disclaimer": "This deep reading was generated by AI based on the paper abstract for quick reference only. Please verify against the original paper before citing.",
        "mode_switched_confirm": "✅ Switched to {mode}",
        "lang_switched_confirm": "✅ Language set to {lang}",
        "mark_seen_callback": "👁 Marked as read",
        "mark_skip_callback": "❌ Skipped",
        "pro_text": (
            "📊 <b>PaperFilterBot Plan Comparison</b>\n\n"
            "👤 Your current plan: {tier}\n\n"
            "🆓 <b>Free</b>\n"
            "• Search: 10/day\n"
            "• Deep Reading: 1/day\n"
            "• Drive: 5 papers/mo\n"
            "• Ads: Yes\n\n"
            "🔧 <b>Basic</b>\n"
            "• Search: 30/day\n"
            "• Deep Reading: 5/day\n"
            "• /chat Cross-paper Q&A: 10/mo\n"
            "• Drive: 30 papers/mo\n"
            "• Ad-Free\n\n"
            "⭐ <b>Standard</b>\n"
            "• Search: 100/day\n"
            "• Deep Reading: 15/day\n"
            "• /review Literature Review + /gap Research Gap\n"
            "• Drive: 100 papers/mo\n"
            "• Monthly AI Report\n\n"
            "💎 <b>Premium</b>\n"
            "• Search: 200/day\n"
            "• Deep Reading: 30/day\n"
            "• All features boosted\n"
            "• Drive: Unlimited\n"
            "• Weekly AI Report\n\n"
            "👑 <b>Ultra</b>\n"
            "• Search: 500/day\n"
            "• Deep Reading: 50/day\n"
            "• All features unlimited\n"
            "• Daily AI Report\n\n"
            "💡 Upgrade now at Web Research HQ!"
        ),
    },
    "ja": {
        "welcome": (
            "👋 こんにちは <b>{name}</b>、<b>PaperFilterBot 研究総本部</b>へようこそ！\n\n"
            "🔬 <b>主な機能</b>：\n"
            "• 4大学術リポジトリ横断検索 (arXiv / PubMed / Semantic Scholar / CrossRef)\n"
            "• 💡 4次元AI詳細解説（動機・手法・結論・限界）\n"
            "• 💬 論文横断RAG質問（<code>/chat [質問]</code>）\n"
            "• ☁️ Google Drive自動保存 & <code>references.bib</code> 同期\n\n"
            "👇 以下のメニューを選択するか、<b>キーワード</b>を直接送信して検索してください："
        ),
        "help": (
            "📖 <b>PaperFilterBot コマンド一覧</b>\n\n"
            "🔍 <b>論文検索</b>：キーワードを直接送信（例：LLM Agent）\n"
            "💬 <b>/chat</b> - 論文横断Q&Aモード切替（直接質問入力）\n"
            "📚 <b>/my</b> - 文献ライブラリ・フォルダ・Drive連携状態を確認\n"
            "🔗 <b>/bind</b> - Web総本部連携用の6桁コードを発行\n"
            "💎 <b>/pro</b> - プラン比較とアップグレード情報\n"
            "📂 <b>/following</b> - フォロー中のキーワードとフォルダ管理\n"
            "➕ <b>/follow [著者名]</b> - 研究者の最新論文を追跡\n"
            "➖ <b>/unfollow [著者名]</b> - 追跡解除\n"
            "📑 <b>/review [テーマ]</b> - AI文献レビュー草案を作成\n"
            "🔍 <b>/gap</b> - 収集済み文献から研究ギャップを自動抽出\n"
            "📈 <b>/trend [分野]</b> - 分野別トレンド＆年別推移分析\n"
            "📋 <b>/export</b> - BibTeX / RIS / CSVで文献エクスポート\n"
            "⚙️ <b>/mode</b> - 要約モードの切り替え\n"
            "🌐 <b>/lang</b> - 言語設定の変更\n"
            "📊 <b>/reports</b> - 読書レポートと閲覧履歴\n"
            "☁️ <b>/drive</b> - Google Drive連携確認\n"
            "💻 <b>/web</b> - Web研究総本部のURLを取得\n\n"
            "💡 ヒント：キーワードを入力するだけで論文を検索できます！"
        ),
        "btn_search": "🔍 論文検索",
        "btn_web": "💻 Web総本部を開く",
        "btn_bind": "🔗 連携コード発行",
        "btn_pro": "💎 Pro機能",
        "btn_lang": "🌐 言語変更",
        "btn_deep": "💡 詳細解説",
        "btn_seen": "👀 閲覧済み",
        "btn_skip": "👎 興味なし",
        "btn_archive": "☁️ ドライブ保存",
        "btn_oa": "🟢 オープンアクセス",
        "btn_doi": "🔗 公式DOIページ",
        "btn_hot_transformer": "🔍 人気：Transformer",
        "btn_hot_crispr": "🧬 人気：CRISPR",
        "btn_bind_web": "🔗 Web本部と連携",
        "btn_view_pro": "👑 Pro機能を見る",
        "btn_full_help": "📖 コマンド一覧",
        "read_paper": "原著論文を読む",
        "searching": "🔍 「{query}」を検索中...",
        "not_found": "❌ 一致する論文が見つかりませんでした。",
        "search_error": "⚠️ ネットワークエラーが発生しました。",
        "lang_switch_title": "🌐 言語設定を選択してください (現在: {current}):",
        "lang_switched": "✅ 言語設定を更新しました！",
        "mode_title": "⚙️ フィルターモードの選択 (現在: {current}):",
        "mode_top": "🏆 トップ学会/論文誌 (Top-Tier)",
        "mode_smart": "⚡ スマート推奨 (Smart)",
        "mode_free": "🟢 オープンアクセスのみ",
        "mode_switched": "✅ フィルターモードを {mode} に変更しました",
        "deep_processing": "🧠 AIが論文全文から4次元重要ポイントを抽出中...",
        "deep_header": "💡 <b>AI 4次元詳細解説レポート</b>",
        "bibtex_header": "📋 <b>BibTeX 引用エントリ</b>",
        "mark_seen": "👁 閲覧済みに設定し、好みを学習しました: {title}",
        "mark_skip": "⏭ スキップし、関連重みを下げました: {title}",
        "archive_success": "✅ 『{title}』をGoogle Driveフォルダ【{folder}】に保存しました！",
        "archive_failed": "❌ 保存失敗: {detail}",
        "folder_added": "📁 フォルダを追加しました: 【{name}】",
        "folder_renamed": "📁 フォルダ名を変更しました: 【{old}】➡️【{new}】",
        "folder_deleted": "🗑 フォルダを削除しました: 【{name}】",
        "folder_not_found": "❌ 指定のフォルダが見つかりません: 【{name}】",
        "my_folders": "📁 <b>カスタムフォルダ一覧：</b>\n\n{list}",
        "no_custom_folders": "📂 フォルダがありません。「追加 フォルダ名」で作成できます。",
        "follow_success": "✅ 著者をフォローしました: <b>{name}</b>",
        "unfollow_success": "✅ 著者のフォローを解除しました: <b>{name}</b>",
        "unfollow_failed": "❌ フォロー解除失敗：著者が存在しません。",
        "no_following": "現在フォロー中の著者はいません。<code>/follow 著者名</code> で追加できます。",
        "following_list": "👥 <b>フォロー中著者一覧：</b>\n\n{list}",
        "default_categories": ["Artificial Intelligence", "Bio & Life Sciences", "General Science", "Human Genetics"],
        "tier_free": "無料版",
        "tier_basic": "Basic プラン",
        "tier_standard": "Standard プラン",
        "tier_premium": "Premium プラン",
        "tier_ultra": "Ultra プラン",
        "tier_price": "月額 {price}",
        "tier_search_daily": "{count} 回/日 検索",
        "tier_deep_daily": "{count} 回/日 詳細解説",
        "tier_chat": "論文横断Q&A",
        "tier_review": "文献レビュー",
        "tier_gap": "研究ギャップ",
        "tier_drive": "Google Drive 保存",
        "tier_drive_limit": "{count} 本/月",
        "tier_drive_unlimited": "無制限",
        "tier_follow": "学者フォロー",
        "tier_folder": "カスタムフォルダ",
        "tier_export": "エクスポート",
        "tier_report": "AI 分析レポート",
        "tier_report_none": "なし",
        "tier_report_monthly": "月1回",
        "tier_report_weekly": "週1回",
        "tier_report_daily": "日1回",
        "tier_ads": "ウェブ広告",
        "tier_ads_none": "広告なし",
        "tier_ads_show": "広告あり",
        "tier_unlock": "ロック解除",
        "tier_locked": "アップグレード必要",
        "tier_current": "現在のプラン",
        "tier_upgrade": "アップグレード",
        "upgrade_title": "🔒 この機能にはプランのアップグレードが必要です",
        "upgrade_current_tier": "現在のプラン",
        "upgrade_compare": "プラン比較",
        "upgrade_btn": "アップグレードプランを見る",
        "upgrade_drive_limited": "今月の Drive 配分を使い切りました。翌月にリセットされます。",
        "tier_plan_comparison": "📊 プラン比較",
        "tier_basic_price": "Basic",
        "tier_standard_price": "Standard",
        "tier_premium_price": "Premium",
        "tier_ultra_price": "Ultra",
        "chat_exit": "✅ <b>論文横断Q&Aモード</b>を終了しました。\n\n/chat で再入できます。",
        "chat_enter": "💬 <b>論文横断Q&Aモードに入りました</b>\n\n📚 文献ライブラリ：{count} 本\n\n直接質問を入力できます。例：\n• これらの論文の方法論の違いは？\n• どれがエッジコンピューティングに最適？\n• これらの研究の共通の限界は？\n\n終了するには /chat を入力してください。",
        "chat_first_use": "👋 <b>論文横断Q&A 初回使用</b>\n\nこの機能はライブラリから関連論文を見つけ、<b>論文横断分析</b>を行います。\n\n💡 おすすめの質問：\n• 比較：「これらの論文の[方法/結果]の違いは？」\n• 推薦：「どれが[自分のシナリオ]に最適？」\n• ギャップ：「共通の限界は何？」\n\n⏳ 初回分析は10-20秒かかる場合があります...",
        "chat_empty_library": "📂 ライブラリに論文がありません。まず検索して保存してください！",
        "chat_loading": "🧠 <b>AI が {count} 本の論文を横断分析中...</b>",
        "chat_header": "💬 <b>論文横断回答レポート</b>\n❓ <i>質問：{query}</i>\n\n",
        "chat_disclaimer": "\n\n---\n📚 <i>ライブラリの論文のみに基づく分析です。無制限のQ&Aには Pro にアップグレード。</i>",
        "reports_empty": "📝 レポートがまだありません。<code>/review [テーマ]</code> で作成してください！",
        "reports_list_header": "📑 <b>文献レビュー報告書（全 {count} 件）：</b>\n\n",
        "reports_list_footer": "\nWeb研究総本部で全文閲覧・Markdown/PDFエクスポートが可能！",
        "follow_missing_args": "著者名を入力してください。例：<code>/follow Yann LeCun</code>",
        "unfollow_missing_args": "フォロー解除する著者名を入力してください。",
        "drive_connected": "✅ Google Drive が接続されました！論文の保存と references.bib の同期が可能です。",
        "drive_auth_prompt": "以下のボタンをクリックして Google Drive を認証してください：",
        "drive_auth_button": "🔗 Google Drive を認証",
        "drive_oauth_not_configured": "❌ Google OAuth が設定されていません。.env を確認してください。",
        "drive_auth_success": "✅ Google Drive 認証成功！論文をクラウドに保存できます。",
        "search_missing_args": "キーワードを入力してください。例：<code>/search CRISPR</code>",
        "review_empty": "論文がまだありません。まず検索して保存してください！",
        "review_loading": "🧠 {count} 本の論文の文献レビューを生成中...",
        "gap_empty": "論文がまだありません。まず検索して保存してください！",
        "gap_loading": "🔍 {count} 本の論文の研究ギャップを分析中...",
        "trend_loading": "📈 「{topic}」のトレンドを分析中...",
        "trend_year_format": "{year}年: {count}本",
        "trend_result_header": "📊 <b>「{topic}」トレンド分析</b>\n\n📚 関連論文：{count} 本\n📅 年度分布：{year_str}\n\n",
        "trend_ai_analysis": "🤖 <b>AI トレンド分析：</b>\n{analysis}",
        "export_empty": "論文がまだありません。",
        "export_prompt": "📚 {count} 本の論文があります。エクスポート方法を選択してください：",
        "export_all_button": "📦 全部エクスポート ({count} 本)",
        "export_select_button": "☑️ 選択してエクスポート",
        "export_format_prompt": "エクスポート形式を選択してください：",
        "export_select_prompt": "☑️ <b>エクスポートする論文を選択</b>（選択中：{count} 本）\n\n",
        "export_confirm_button": "✅ エクスポート確認",
        "export_cancel_button": "❌ キャンセル",
        "export_selected_count": "選択中 {count} 本",
        "export_no_selection": "まず1本以上選択してください",
        "export_cancelled": "❌ エクスポートをキャンセルしました。",
        "export_cancel_callback": "キャンセル済み",
        "export_no_papers": "エクスポートする論文がありません",
        "export_generating": "📄 {fmt} 形式を生成中...",
        "export_result_caption": "📄 <b>{fmt} エクスポート結果</b>\n📚 {count} 本の論文\n\nZotero / EndNote / Mendeley に直接インポート可能",
        "export_selected_format": "{count} 本を選択。形式を選択してください：",
        "archive_choose_folder": "📁 保存フォルダを選択してください：",
        "archive_skip_button": "🔙 戻る",
        "archive_invalid_button": "❌ 無効なボタン",
        "archive_skip_archive": "⏭ 保存をスキップ",
        "archive_archiving": "☁️ 保存中...",
        "archive_drive_auth_prompt": "まず Google Drive を認証してください：",
        "archive_drive_auth_button": "🔗 Google Drive を認証",
        "archive_drive_not_configured": "❌ Google OAuth が未設定です。",
        "my_title": "📚 <b>研究文献ライブラリ概要</b>\n\n",
        "my_tier_label": "👤 会員等級：{tier}",
        "my_drive_status_label": "☁️ Google Drive 状態：{status}",
        "my_drive_connected": "🟢 接続済み",
        "my_drive_disconnected": "⚪ 未接続（/drive で認証）",
        "my_paper_count": "📑 保存論文数：合計 <b>{count}</b> 本",
        "my_folders_label": "📁 カスタムフォルダ：{folders}",
        "my_default_folders": "デフォルト分類",
        "my_recent_papers": "<b>🕒 最近の論文（最新3本）：</b>\n{list}",
        "my_recent_hint": "\n💡 <code>/chat [質問]</code> で論文横断Q&A、<code>/export</code> で一括エクスポートが可能！",
        "my_empty_library": "まだ論文がありません。検索して【☁️ ドライブ保存】で追加！",
        "my_export_button": "📄 文献エクスポート",
        "my_drive_button": "☁️ Drive 認証",
        "bind_title": "🔗 <b>Web研究総本部 アカウント連携</b>\n\n",
        "bind_code": "6桁同期コード：<code>{code}</code>\n\n",
        "bind_instructions": "💻 Web研究総本部を開き、<b>【Telegram連携】</b>をクリックしてこのコードを入力。\nすべてのマーク（既読/スキップ/保存/メモ）が双方向同期されます！",
        "help_bind_button": "🔗 Web連携",
        "help_pro_button": "👑 Pro機能を見る",
        "unknown_command": "❌ 未知のコマンド：{cmd}\n/help で利用可能なコマンド一覧を確認できます。",
        "paper_et_al": "他 {count} 名",
        "paper_seen_badge": "👁 [閲覧済み]",
        "paper_ai_summary": "🧠 <b>AI 解説：</b>\n{text}",
        "card_citations": "引用",
        "card_disclaimer": "AI による要約です。引用する場合は原著を必ずご確認ください。",
        "deep_disclaimer": "このディープリーディングは論文の要約を基に AI が生成したものです。引用する場合は原著を必ずご確認ください。",
        "mode_switched_confirm": "✅ {mode} に切り替えました",
        "lang_switched_confirm": "✅ 言語を {lang} に設定しました",
        "mark_seen_callback": "👁 既読に設定",
        "mark_skip_callback": "❌ スキップ済み",
        "pro_text": (
            "📊 <b>PaperFilterBot プラン比較</b>\n\n"
            "👤 現在のプラン：{tier}\n\n"
            "🆓 <b>Free 無料版</b>\n"
            "• 検索：10 回/日\n"
            "• 詳細解説：1 回/日\n"
            "• Drive：5 本/月\n"
            "• 広告：あり\n\n"
            "🔧 <b>Basic</b>\n"
            "• 検索：30 回/日\n"
            "• 詳細解説：5 回/日\n"
            "• /chat 論文横断Q&A：10 回/月\n"
            "• Drive：30 本/月\n"
            "• 広告なし\n\n"
            "⭐ <b>Standard</b>\n"
            "• 検索：100 回/日\n"
            "• 詳細解説：15 回/日\n"
            "• /review 文献レビュー + /gap 研究ギャップ\n"
            "• Drive：100 本/月\n"
            "• 月次 AI レポート\n\n"
            "💎 <b>Premium</b>\n"
            "• 検索：200 回/日\n"
            "• 詳細解説：30 回/日\n"
            "• 全機能大幅強化\n"
            "• Drive：無制限\n"
            "• 週次 AI レポート\n\n"
            "👑 <b>Ultra</b>\n"
            "• 検索：500 回/日\n"
            "• 詳細解説：50 回/日\n"
            "• 全機能無制限\n"
            "• 日次 AI レポート\n\n"
            "💡 Web研究総本部で今すぐアップグレード！"
        ),
    }
}

# ===================== 2. 多語系與核心工具 =====================
def _get_lang(user_id: int, tg_lang_code: str = None) -> str:
    try:
        saved = db.get_user_lang(user_id)
        if saved:
            return saved
    except Exception:
        pass
    if tg_lang_code:
        code = tg_lang_code.lower()
        if "zh" in code:
            return "zh_hant" if "tw" in code or "hk" in code else "zh_hans"
        if "ja" in code:
            return "ja"
    return "en"

def detect_user_lang(user_id_or_code):
    if isinstance(user_id_or_code, int):
        return _get_lang(user_id_or_code)
    return "en"

def _t(user_id: int, key: str, tg_lang_code: str = None, **kwargs) -> str:
    lang = _get_lang(user_id, tg_lang_code)
    template = MESSAGES.get(lang, MESSAGES["zh_hant"]).get(key, key)
    try:
        if kwargs and isinstance(template, str):
            return template.format(**kwargs)
        return template
    except Exception:
        return template

def get_text(user_id_or_lang, key, **kwargs):
    if isinstance(user_id_or_lang, int):
        return _t(user_id_or_lang, key, **kwargs)
    lang = user_id_or_lang if user_id_or_lang in MESSAGES else "zh_hant"
    template = MESSAGES.get(lang, MESSAGES["zh_hant"]).get(key, key)
    try:
        if kwargs and isinstance(template, str):
            return template.format(**kwargs)
        return template
    except Exception:
        return template

def fetch_user_papers(user_id: int) -> list:
    return db.get_user_library(user_id)

# ===================== 3. Bot 初始化 =====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 10000))

if not TELEGRAM_TOKEN:
    print("❌ 缺少 TELEGRAM_TOKEN！請在 .env 中設定", file=sys.stderr)

bot = telebot.TeleBot(TELEGRAM_TOKEN or "DUMMY_TOKEN", parse_mode="HTML")
app = Flask(__name__)

def make_main_menu(user_id):
    lang = _get_lang(user_id)
    t = lambda k: MESSAGES.get(lang, MESSAGES["zh_hant"]).get(k, k)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(t("btn_search"), switch_inline_query_current_chat=""),
        InlineKeyboardButton(t("btn_web"), callback_data="cmd_web")
    )
    markup.add(
        InlineKeyboardButton(t("btn_bind"), callback_data="cmd_bind"),
        InlineKeyboardButton(t("btn_pro"), callback_data="cmd_pro")
    )
    markup.add(
        InlineKeyboardButton(t("btn_lang"), callback_data="cmd_lang")
    )
    return markup

def _build_folder_keyboard(user_id: int, paper_id: str, lang: str) -> types.InlineKeyboardMarkup:
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
    # Extract user_id from the caller context - we'll use a simple approach
    markup.add(types.InlineKeyboardButton(
        MESSAGES.get(lang, MESSAGES["en"]).get("archive_skip_button", "🔙 Back"),
        callback_data=f"archive|{paper_id[:40]}|返回"
    ))
    return markup

# ===================== 4. 指令系統 =====================
@bot.message_handler(commands=['start', 'welcome'])
def handle_start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "Researcher"
    welcome_text = _t(user_id, "welcome", name=name)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "btn_hot_transformer"), callback_data="search_kw|Transformer"),
        types.InlineKeyboardButton(_t(user_id, "btn_hot_crispr"), callback_data="search_kw|CRISPR"),
    )
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "btn_bind_web"), callback_data="cmd_bind"),
        types.InlineKeyboardButton(_t(user_id, "btn_view_pro"), callback_data="cmd_pro")
    )
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "btn_full_help"), callback_data="cmd_help")
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=['help', 'h', 'guide'])
def handle_help(message, override_user_id=None):
    user_id = override_user_id or message.from_user.id
    help_text = _t(user_id, "help")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "help_bind_button"), callback_data="cmd_bind"),
        types.InlineKeyboardButton(_t(user_id, "help_pro_button"), callback_data="cmd_pro")
    )
    bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=['my', 'library'])
def handle_my_command(message):
    """查看我的文獻庫、分類資料夾與 Google Drive 狀態"""
    user_id = message.from_user.id
    papers = db.get_user_library(user_id)
    token = db.get_token(user_id)
    drive_status = _t(user_id, "my_drive_connected") if token else _t(user_id, "my_drive_disconnected")
    categories = db.get_user_categories(user_id)
    cats_str = "、".join(categories) if categories else _t(user_id, "my_default_folders")
    tier_info = db.get_user_tier(user_id)
    tier = tier_info.get("tier", "free")
    tier_names = {"free": _t(user_id, "tier_free"), "basic": _t(user_id, "tier_basic"), "standard": _t(user_id, "tier_standard"), "premium": _t(user_id, "tier_premium"), "ultra": _t(user_id, "tier_ultra")}
    tier_badge = tier_names.get(tier, _t(user_id, "tier_free"))
    text = (
        _t(user_id, "my_title")
        + _t(user_id, "my_tier_label", tier=tier_badge) + "\n"
        + _t(user_id, "my_drive_status_label", status=drive_status) + "\n"
        + _t(user_id, "my_paper_count", count=len(papers)) + "\n"
        + _t(user_id, "my_folders_label", folders=cats_str) + "\n\n"
    )

    if papers:
        recent_lines = ""
        for i, p in enumerate(papers[:3], 1):
            recent_lines += f"{i}. <b>{p.get('title', '')[:55]}</b> ({p.get('year', 'N/A')})\n"
        text += _t(user_id, "my_recent_papers", list=recent_lines)
        text += _t(user_id, "my_recent_hint")
    else:
        text += _t(user_id, "my_empty_library")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "my_export_button"), callback_data="cmd_export"),
        types.InlineKeyboardButton(_t(user_id, "my_drive_button"), callback_data="cmd_drive")
    )
    bot.reply_to(message, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=['chat', 'ask'])
def handle_chat_command(message):
    """切換跨文獻問答模式"""
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)

    # 如果有帶問題，直接回答（兼容舊用法）
    if len(parts) > 1:
        _process_chat_query(message, parts[1].strip())
        return

    # 切換模式
    if _chat_mode_users.get(user_id):
        del _chat_mode_users[user_id]
        bot.reply_to(message, _t(user_id, "chat_exit"), parse_mode="HTML")
    else:
        papers = db.get_user_library(user_id)
        _chat_mode_users[user_id] = True
        bot.reply_to(message, _t(user_id, "chat_enter", count=len(papers)), parse_mode="HTML")

def _process_chat_query(message, query):
    """處理跨文獻問答"""
    user_id = message.from_user.id

    # 檢查是否第一次使用
    first_use_key = f"chat_first_{user_id}"
    if first_use_key not in _user_first_use:
        _user_first_use.add(first_use_key)
        bot.reply_to(message, _t(user_id, "chat_first_use"), parse_mode="HTML")

    allowed, err_msg = db.check_quota(user_id, "chat")
    if not allowed:
        bot.reply_to(message, f"⚠️ {err_msg}")
        return

    papers = db.get_user_library(user_id)
    if not papers:
        bot.reply_to(message, _t(user_id, "chat_empty_library"))
        return

    loading_msg = bot.reply_to(message, _t(user_id, "chat_loading", count=len(papers)), parse_mode="HTML")
    answer = search_engine.chat_with_user_library(user_id, query, papers)
    db.increment_usage(user_id, "chat")

    try:
        bot.delete_message(loading_msg.chat.id, loading_msg.message_id)
    except Exception:
        pass

    header = _t(user_id, "chat_header", query=query)
    disclaimer = _t(user_id, "chat_disclaimer")
    full_response = header + answer + disclaimer

    if len(full_response) > 4000:
        for i in range(0, len(full_response), 4000):
            bot.send_message(message.chat.id, full_response[i:i+4000], parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, full_response, parse_mode="HTML")

@bot.message_handler(commands=['bind', 'web'])
def handle_bind_command(message, override_user_id=None):
    user_id = override_user_id or message.from_user.id
    code = db.generate_sync_code(user_id)
    text = _t(user_id, "bind_title") + _t(user_id, "bind_code", code=code) + _t(user_id, "bind_instructions")
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['pro'])
def handle_pro_command(message, override_user_id=None):
    user_id = override_user_id or message.from_user.id
    tier_info = db.get_user_tier(user_id)
    tier = tier_info.get("tier", "free")
    tier_names = {"free": _t(user_id, "tier_free"), "basic": _t(user_id, "tier_basic"), "standard": _t(user_id, "tier_standard"), "premium": _t(user_id, "tier_premium"), "ultra": _t(user_id, "tier_ultra")}
    tier_badge = tier_names.get(tier, _t(user_id, "tier_free"))
    text = _t(user_id, "pro_text", tier=tier_badge)
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['reports'])
def handle_reports_command(message):
    user_id = message.from_user.id
    reports = db.get_user_reports(user_id)
    if not reports:
        bot.reply_to(message, _t(user_id, "reports_empty"))
        return
    text = _t(user_id, "reports_list_header", count=len(reports))
    for r in reports[:5]:
        text += f"• <b>{r.get('topic', '綜合綜述')}</b> ({str(r.get('created_at', ''))[:10]})\n"
    text += _t(user_id, "reports_list_footer")
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['mode'])
def handle_mode(message):
    user_id = message.from_user.id
    current_mode = db.get_filter_mode(user_id)
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

@bot.message_handler(commands=['lang', 'language'])
def handle_lang(message, override_user_id=None):
    user_id = override_user_id or message.from_user.id
    lang = _get_lang(user_id, message.from_user.language_code)
    lang_names = {"en": "English", "zh_hant": "繁體中文", "zh_hans": "简体中文", "ja": "日本語"}
    current_display = lang_names.get(lang, lang)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("English", callback_data="set_lang|en"),
        types.InlineKeyboardButton("繁體中文", callback_data="set_lang|zh_hant"),
        types.InlineKeyboardButton("简体中文", callback_data="set_lang|zh_hans"),
        types.InlineKeyboardButton("日本語", callback_data="set_lang|ja"),
    )
    bot.reply_to(message, _t(user_id, "lang_switch_title", current=current_display), reply_markup=markup)

@bot.message_handler(commands=['follow', 'track'])
def handle_follow(message):
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, _t(user_id, "follow_missing_args"))
        return
    author_name = parts[1].strip()
    db.add_followed_author(user_id, author_name)
    bot.reply_to(message, _t(user_id, "follow_success", name=author_name))

@bot.message_handler(commands=['unfollow', 'untrack'])
def handle_unfollow(message):
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, _t(user_id, "unfollow_missing_args"))
        return
    author_name = parts[1].strip()
    success = db.remove_followed_author(user_id, author_name)
    if success:
        bot.reply_to(message, _t(user_id, "unfollow_success", name=author_name))
    else:
        bot.reply_to(message, _t(user_id, "unfollow_failed", name=author_name))

@bot.message_handler(commands=['following', 'authors'])
def handle_following(message):
    user_id = message.from_user.id
    authors = db.get_followed_authors(user_id)
    if not authors:
        bot.reply_to(message, _t(user_id, "no_following"))
    else:
        authors_list = "\n".join(f"• <code>{a}</code>" for a in authors)
        bot.reply_to(message, _t(user_id, "following_list", list=authors_list))

@bot.message_handler(commands=['folders', 'myfolders', 'categories', 'cats'])
def handle_folders_command(message):
    user_id = message.from_user.id
    cats = db.get_user_categories(user_id)
    default_cats = MESSAGES.get(_get_lang(user_id), MESSAGES["en"]).get("default_categories", [])
    all_cats = cats if cats else default_cats
    if all_cats:
        cats_list = "\n".join(f"• {c}" for c in all_cats)
        bot.reply_to(message, _t(user_id, "my_folders", list=cats_list), parse_mode="HTML")
    else:
        bot.reply_to(message, _t(user_id, "no_custom_folders"))

@bot.message_handler(commands=['drive'])
def handle_drive(message, override_user_id=None):
    user_id = override_user_id or message.from_user.id
    text = (message.text or "").strip().lower()
    if text == '/drive revoke':
        db.remove_token(user_id)
        bot.reply_to(message, "✅ Google Drive 授權已清除。如要重新授權請打 /drive")
        return
    token = db.get_token(user_id)
    if token:
        auth_url = drive_manager.get_auth_url(user_id)
        if auth_url:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(_t(user_id, "drive_reauth_button", fallback="🔄 重新授權"), url=auth_url))
            markup.add(types.InlineKeyboardButton(_t(user_id, "drive_disconnect_button", fallback="🔌 斷開連結"), callback_data="drive_disconnect"))
            bot.reply_to(message, _t(user_id, "drive_connected"), reply_markup=markup)
        else:
            bot.reply_to(message, _t(user_id, "drive_connected"))
    else:
        auth_url = drive_manager.get_auth_url(user_id)
        if auth_url:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(_t(user_id, "drive_auth_button"), url=auth_url))
            bot.reply_to(message, _t(user_id, "drive_auth_prompt"), reply_markup=markup)
        else:
            bot.reply_to(message, _t(user_id, "drive_oauth_not_configured"))

@bot.message_handler(commands=['search'])
def handle_search_command(message):
    user_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, _t(user_id, "search_missing_args"))
        return
    query = parts[1].strip()
    _do_search(message, user_id, query)

@bot.message_handler(commands=['review'])
def handle_review(message):
    user_id = message.from_user.id
    allowed, err_msg = db.check_quota(user_id, "litreview")
    if not allowed:
        bot.reply_to(message, f"⚠️ {err_msg}")
        return
    papers = fetch_user_papers(user_id)
    if not papers:
        bot.reply_to(message, _t(user_id, "review_empty"))
        return
    bot.reply_to(message, _t(user_id, "review_loading", count=len(papers)))
    review = search_engine.generate_literature_review(user_id, papers)
    db.increment_usage(user_id, "litreview")
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
        bot.reply_to(message, _t(user_id, "gap_empty"))
        return
    bot.reply_to(message, _t(user_id, "gap_loading", count=len(papers)))
    gaps = search_engine.analyze_research_gaps(user_id, papers)
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
    bot.reply_to(message, _t(user_id, "trend_loading", topic=topic))
    trends = search_engine.analyze_research_trends(user_id, topic)
    year_dist = trends.get("year_distribution", {})
    year_str = " ".join(_t(user_id, "trend_year_format", year=y, count=c) for y, c in sorted(year_dist.items(), reverse=True)[:5])
    ai_analysis = trends.get("ai_analysis", "")
    result = _t(user_id, "trend_result_header", topic=topic, count=trends.get('total_papers_found', 0), year_str=year_str)
    if ai_analysis:
        result += _t(user_id, "trend_ai_analysis", analysis=ai_analysis)
    bot.send_message(message.chat.id, result, parse_mode="HTML")

@bot.message_handler(commands=['export'])
def handle_export(message, override_user_id=None):
    user_id = override_user_id or message.from_user.id
    allowed, err_msg = db.check_quota(user_id, "export")
    if not allowed:
        bot.reply_to(message, f"⚠️ {err_msg}")
        return
    papers = fetch_user_papers(user_id)
    if not papers:
        bot.reply_to(message, _t(user_id, "export_empty"))
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "export_all_button", count=len(papers)), callback_data="export_all"),
        types.InlineKeyboardButton(_t(user_id, "export_select_button"), callback_data="export_select"),
    )
    bot.reply_to(message, _t(user_id, "export_prompt", count=len(papers)), reply_markup=markup)

# 匯出選擇模式
@bot.callback_query_handler(func=lambda call: call.data.startswith("export_"))
def handle_export_callback(call):
    user_id = call.from_user.id
    data = call.data

    if data == "export_all":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("📄 BibTeX", callback_data="export_fmt|BibTeX|all"),
            types.InlineKeyboardButton("📋 RIS", callback_data="export_fmt|RIS|all"),
            types.InlineKeyboardButton("📊 CSV", callback_data="export_fmt|CSV|all"),
        )
        bot.edit_message_text(_t(user_id, "export_format_prompt"), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        return

    if data == "export_select":
        bot.answer_callback_query(call.id)
        papers = fetch_user_papers(user_id)
        # 初始化選取狀態
        if not hasattr(handle_export_callback, '_selections'):
            handle_export_callback._selections = {}
        handle_export_callback._selections[user_id] = set()

        # 顯示論文清單（最多20篇）
        text = _t(user_id, "export_select_prompt", count=0)
        buttons = []
        for i, p in enumerate(papers[:20], 1):
            title_short = p.get('title', '')[:30]
            text += f"{i}. {title_short}...\n"
            buttons.append(types.InlineKeyboardButton(f"❌ {i}", callback_data=f"export_toggle|{i-1}"))

        # 分行按鈕
        row = []
        markup = types.InlineKeyboardMarkup(row_width=5)
        for i, btn in enumerate(buttons):
            row.append(btn)
            if len(row) == 5:
                markup.add(*row)
                row = []
        if row:
            markup.add(*row)

        # 加入確認按鈕
        markup.add(types.InlineKeyboardButton(_t(user_id, "export_confirm_button"), callback_data="export_confirm"))
        markup.add(types.InlineKeyboardButton(_t(user_id, "export_cancel_button"), callback_data="export_cancel"))

        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="HTML")
        return

    if data.startswith("export_toggle|"):
        idx = int(data.split("|")[1])
        selections = handle_export_callback._selections.get(user_id, set())
        if idx in selections:
            selections.discard(idx)
        else:
            selections.add(idx)
        handle_export_callback._selections[user_id] = selections
        bot.answer_callback_query(call.id, _t(user_id, "export_selected_count", count=len(selections)))
        return

    if data == "export_confirm":
        selections = handle_export_callback._selections.get(user_id, set())
        if not selections:
            bot.answer_callback_query(call.id, _t(user_id, "export_no_selection"), show_alert=True)
            return
        bot.answer_callback_query(call.id)
        # 進入格式選擇
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("📄 BibTeX", callback_data=f"export_fmt|BibTeX|{','.join(map(str, selections))}"),
            types.InlineKeyboardButton("📋 RIS", callback_data=f"export_fmt|RIS|{','.join(map(str, selections))}"),
            types.InlineKeyboardButton("📊 CSV", callback_data=f"export_fmt|CSV|{','.join(map(str, selections))}"),
        )
        bot.edit_message_text(_t(user_id, "export_selected_format", count=len(selections)), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        return

    if data == "export_cancel":
        bot.answer_callback_query(call.id, _t(user_id, "export_cancel_callback"))
        bot.edit_message_text(_t(user_id, "export_cancelled"), chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    # 匯出格式
    if data.startswith("export_fmt|"):
        parts = data.split("|")
        fmt = parts[1]
        selection_str = parts[2] if len(parts) > 2 else "all"

        papers = fetch_user_papers(user_id)
        if selection_str == "all":
            export_papers = papers
        else:
            indices = [int(i) for i in selection_str.split(",")]
            export_papers = [papers[i] for i in indices if i < len(papers)]

        if not export_papers:
            bot.answer_callback_query(call.id, _t(user_id, "export_no_papers"), show_alert=True)
            return

        bot.answer_callback_query(call.id, _t(user_id, "export_generating", fmt=fmt))
        export_content = search_engine.export_papers(export_papers, fmt)
        db.increment_usage(user_id, "export")

        # 產生檔案並傳送
        import tempfile
        import os
        ext_map = {"BibTeX": "bib", "RIS": "ris", "CSV": "csv"}
        ext = ext_map.get(fmt, "txt")
        filename = f"PaperFilter_{fmt}_{len(export_papers)}papers.{ext}"

        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{ext}', delete=False, encoding='utf-8') as f:
            f.write(export_content)
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                bot.send_document(
                    call.message.chat.id,
                    f,
                    caption=_t(user_id, "export_result_caption", fmt=fmt, count=len(export_papers)),
                    parse_mode="HTML"
                )
        finally:
            os.unlink(temp_path)
        return
def _send_paper_card(chat_id, user_id, title, ai_summary, link, paper_id, already_seen, authors, raw_summary, year, source, is_open_access, fingerprint, lang, venue_name="", tier=None, is_preprint=False, citations=0):
    authors_str = ", ".join(authors[:3]) if authors else "Unknown"
    if len(authors) > 3:
        authors_str += " " + _t(user_id, "paper_et_al", count=len(authors))
    seen_badge = _t(user_id, "paper_seen_badge") if already_seen else ""
    oa_badge = "🟢 OA" if is_open_access else ""
    # 可信度徽章
    cred_badge = ""
    if academic_tiers_imported:
        emoji, label = academic_tiers.credibility_badge(venue_name, source)
        cred_badge = f"{emoji} {label}"
    citation_text = f" | 📑 {citations} {_t(user_id, 'card_citations')}" if citations else ""
    text = (
        f"📄 <b>{title}</b> {seen_badge}\n\n"
        f"👥 {authors_str}\n"
        f"{year} | 🗂 {source}{citation_text} {oa_badge}\n"
        f"{('🏅 ' + cred_badge + '\n') if cred_badge else ''}"
        f"{_t(user_id, 'paper_ai_summary', text=ai_summary)}\n\n"
        f"🔗 <a href='{link}'>{_t(user_id, 'read_paper')}</a>\n"
        f"<i>⚠️ {_t(user_id, 'card_disclaimer')}</i>"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "btn_deep"), callback_data=f"deep|{fingerprint[:40]}"),
        types.InlineKeyboardButton(_t(user_id, "btn_seen"), callback_data=f"seen|{paper_id[:40]}"),
    )
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "btn_skip"), callback_data=f"skip|{paper_id[:40]}"),
        types.InlineKeyboardButton(_t(user_id, "btn_archive"), callback_data=f"choose_folder|{paper_id[:40]}"),
    )
    if is_open_access:
        markup.add(types.InlineKeyboardButton(_t(user_id, "btn_oa"), url=link))
    else:
        markup.add(types.InlineKeyboardButton(_t(user_id, "btn_doi"), url=link))
    bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)
    _pending_papers[paper_id[:40]] = {
        "title": title, "summary": raw_summary, "link": link,
        "authors": authors, "year": year, "source": source,
        "fingerprint": fingerprint, "id": paper_id,
        "venue_name": venue_name, "tier": tier, "is_preprint": is_preprint,
        "citations": citations,
    }

def _do_search(message, user_id: int, query: str):
    lang = _get_lang(user_id, message.from_user.language_code)
    allowed, err_msg = db.check_quota(user_id, "search")
    if not allowed:
        bot.reply_to(message, f"⚠️ {err_msg}")
        return
    loading_msg = bot.reply_to(message, _t(user_id, "searching", query=query))
    try:
        seen_ids = db.get_seen_papers(user_id)
        bias = db.get_user_bias(user_id)
        user_bias = (bias.get("positive", {}), bias.get("negative", {}))
        followed_authors = db.get_followed_authors(user_id)
        filter_mode = db.get_filter_mode(user_id)
        result = search_engine.fetch_paper_multi_source(
            user_input=query,
            seen_ids=seen_ids,
            user_bias=user_bias,
            followed_authors=followed_authors,
            filter_mode=filter_mode,
            user_id=user_id
        )
        title, ai_summary, link, paper_id, already_seen, authors, raw_summary, year, source, is_open_access, fingerprint, venue_name, tier, is_preprint, citations = result
        if not title:
            bot.edit_message_text(_t(user_id, "not_found", query=query), chat_id=loading_msg.chat.id, message_id=loading_msg.message_id)
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
            lang=lang,
            venue_name=venue_name,
            tier=tier,
            is_preprint=is_preprint,
            citations=citations,
        )
    except Exception as e:
        print(f"搜尋錯誤: {e}", file=sys.stderr)
        try:
            bot.edit_message_text(_t(user_id, "search_error"), chat_id=loading_msg.chat.id, message_id=loading_msg.message_id)
        except Exception:
            bot.reply_to(message, _t(user_id, "search_error"))

# ===================== 6. 聊天室自然語言與 4 語言資料夾/追蹤管理 =====================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()
    lower = text.lower()
    lang = _get_lang(user_id, message.from_user.language_code)

    # 對話模式優先 - 非指令訊息自動進入跨文獻問答
    if _chat_mode_users.get(user_id) and not text.startswith('/'):
        return _process_chat_query(message, text)

    # 1. 查詢資料夾清單 (支援 4 國語言)
    folder_triggers = [
        "我的資料夾", "我的文件夹", "資料夾", "文件夹",
        "my folders", "folders", "categories", "show folders", "list folders",
        "マイフォルダ", "フォルダ一覧", "フォルダ", "/folders", "/categories"
    ]
    if lower in folder_triggers:
        return handle_folders_command(message)

    # 2. 新增資料夾 (支援 4 國語言前綴)
    add_prefixes = ["新增 ", "建立 ", "添加 ", "新建 ", "add folder ", "create folder ", "add ", "追加 ", "作成 "]
    for pfx in add_prefixes:
        if lower.startswith(pfx.lower()):
            folder_name = text[len(pfx):].strip()
            if folder_name:
                db.add_user_category(user_id, folder_name)
                bot.reply_to(message, _t(user_id, "folder_added", name=folder_name))
                return

    # 3. 改名資料夾 (支援 4 國語言前綴與各種分隔符)
    rename_prefixes = ["改名 ", "重命名 ", "rename folder ", "rename ", "変更 ", "名前変更 "]
    for pfx in rename_prefixes:
        if lower.startswith(pfx.lower()):
            sub = text[len(pfx):].strip()
            parts = []
            for sep in ["->", "→", " to ", " に "]:
                if sep in sub:
                    parts = sub.split(sep, 1)
                    break
            if len(parts) == 2:
                old_name, new_name = parts[0].strip(), parts[1].strip()
                db.rename_user_category(user_id, old_name, new_name)
                drive_manager.rename_folder(user_id, old_name, new_name)
                bot.reply_to(message, _t(user_id, "folder_renamed", old=old_name, new=new_name))
                return

    # 4. 刪除資料夾 (支援 4 國語言前綴)
    delete_prefixes = ["刪除 ", "移除 ", "删除 ", "delete folder ", "remove folder ", "delete ", "remove ", "削除 ", "消去 "]
    for pfx in delete_prefixes:
        if lower.startswith(pfx.lower()):
            folder_name = text[len(pfx):].strip()
            cats = db.get_user_categories(user_id)
            if folder_name in cats:
                db.delete_user_category(user_id, folder_name)
                drive_manager.mark_folder_deleted(user_id, folder_name)
                bot.reply_to(message, _t(user_id, "folder_deleted", name=folder_name))
            else:
                bot.reply_to(message, _t(user_id, "folder_not_found", name=folder_name))
            return

    # 5. 追蹤學者 (支援 4 國語言前綴)
    follow_prefixes = ["追蹤 ", "關注 ", "追踪 ", "关注 ", "follow ", "track ", "フォロー "]
    for pfx in follow_prefixes:
        if lower.startswith(pfx.lower()):
            author_name = text[len(pfx):].strip()
            if author_name:
                db.add_followed_author(user_id, author_name)
                bot.reply_to(message, _t(user_id, "follow_success", name=author_name))
                return

    # 6. 取消追蹤學者 (支援 4 國語言前綴)
    unfollow_prefixes = ["取消追蹤 ", "取消追踪 ", "unfollow ", "untrack ", "フォロー解除 "]
    for pfx in unfollow_prefixes:
        if lower.startswith(pfx.lower()):
            author_name = text[len(pfx):].strip()
            if author_name:
                success = db.remove_followed_author(user_id, author_name)
                if success:
                    bot.reply_to(message, _t(user_id, "unfollow_success", name=author_name))
                else:
                    bot.reply_to(message, _t(user_id, "unfollow_failed", name=author_name))
                return

    # 7. 一般關鍵字 -> 自動觸發跨庫檢索
    _do_search(message, user_id, text)

# ===================== 7. Callback 按鈕互動 =====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    data = call.data
    user_id = call.from_user.id

    # 快捷導航按鈕
    if data == "cmd_help":
        bot.answer_callback_query(call.id)
        handle_help(call.message, override_user_id=user_id)
        return
    if data == "cmd_pro":
        bot.answer_callback_query(call.id)
        handle_pro_command(call.message, override_user_id=user_id)
        return
    if data in ("cmd_bind", "cmd_web"):
        bot.answer_callback_query(call.id)
        handle_bind_command(call.message, override_user_id=user_id)
        return
    if data == "cmd_lang":
        bot.answer_callback_query(call.id)
        handle_lang(call.message, override_user_id=user_id)
        return
    if data == "cmd_drive":
        bot.answer_callback_query(call.id)
        handle_drive(call.message, override_user_id=user_id)
        return
    if data == "drive_disconnect":
        db.remove_token(user_id)
        bot.answer_callback_query(call.id, _t(user_id, "drive_disconnected_confirm", fallback="已斷開 Google Drive 連結"))
        bot.edit_message_text(_t(user_id, "drive_disconnected_msg", fallback="⚪ 已斷開 Google Drive 連結。如要重新授權請打 /drive"), chat_id=call.message.chat.id, message_id=call.message.message_id)
        return
    if data == "cmd_export":
        bot.answer_callback_query(call.id)
        handle_export(call.message, override_user_id=user_id)
        return
    if data.startswith("search_kw|"):
        kw = data.split("|", 1)[1]
        bot.answer_callback_query(call.id)
        _do_search(call.message, user_id, kw)
        return

    # 語言切換
    if data.startswith("set_lang|"):
        lang_code = data.split("|", 1)[1]
        db.set_user_lang(user_id, lang_code)
        lang_names = {"en": "English", "zh_hant": "繁體中文", "zh_hans": "简体中文", "ja": "日本語"}
        bot.answer_callback_query(call.id, _t(user_id, "lang_switched_confirm", lang=lang_names.get(lang_code, lang_code)))
        bot.edit_message_text(_t(user_id, "lang_switched"), chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    # 模式切換
    if data.startswith("set_mode|"):
        mode = data.split("|", 1)[1]
        db.set_filter_mode(user_id, mode)
        mode_names = {"top_tier": _t(user_id, "mode_top"), "smart": _t(user_id, "mode_smart"), "free_only": _t(user_id, "mode_free")}
        mode_display = mode_names.get(mode, mode)
        bot.answer_callback_query(call.id, _t(user_id, "mode_switched_confirm", mode=mode_display))
        bot.edit_message_text(_t(user_id, "mode_switched", mode=mode_display), chat_id=call.message.chat.id, message_id=call.message.message_id)
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
        cached = db.get_cached_ai(fingerprint) if fingerprint else None
        if cached and cached[1]:
            deep_report = cached[1]
            bibtex_str = cached[2] or ""
        else:
            papers = db.get_user_library(user_id)
            paper = next((p for p in papers if p.get("fingerprint") == fingerprint), None)
            if not paper:
                paper = next((v for v in _pending_papers.values() if v.get("fingerprint") == fingerprint), None)
            if not paper:
                paper = {"title": "Untitled", "summary": "", "authors": [], "year": "2024", "link": "", "source": "Academic"}
            deep_report = search_engine.generate_deep_analysis(
                title=paper.get("title", ""),
                text=paper.get("summary", ""),
                fingerprint=fingerprint,
                user_id=user_id
            )
            bibtex_str = paper.get("bibtex", "") or search_engine.generate_bibtex_str(
                title=paper.get("title", ""),
                authors=paper.get("authors", []),
                year=paper.get("year", ""),
                link=paper.get("link", ""),
                source=paper.get("source", "")
            )
        db.increment_usage(user_id, "deep")
        disclaimer = f"\n\n<i>⚠️ {_t(user_id, 'deep_disclaimer')}</i>"
        report_msg = f"{_t(user_id, 'deep_header')}\n\n{deep_report}{disclaimer}"
        if len(report_msg) > 4000:
            for i in range(0, len(report_msg), 4000):
                bot.send_message(call.message.chat.id, report_msg[i:i+4000], parse_mode="HTML")
        else:
            bot.send_message(call.message.chat.id, report_msg, parse_mode="HTML")
        if bibtex_str:
            bot.send_message(call.message.chat.id, f"{_t(user_id, 'bibtex_header')}\n<pre>{bibtex_str}</pre>", parse_mode="HTML")
        return

    # 標記已看
    if data.startswith("seen|"):
        paper_id = data.split("|", 1)[1]
        db.add_seen_paper(user_id, paper_id)
        papers = db.get_user_library(user_id)
        paper = next((p for p in papers if p.get("id") == paper_id or p.get("fingerprint") == paper_id), None)
        if paper:
            keywords = search_engine.parse_words(paper.get("title", ""))[:5]
            db.update_user_bias(user_id, keywords, is_positive=True)
            title_display = paper.get("title", paper_id)
        else:
            title_display = paper_id
        bot.answer_callback_query(call.id, _t(user_id, "mark_seen_callback"))
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, _t(user_id, "mark_seen", title=title_display[:100]))
        return

    # 略過
    if data.startswith("skip|"):
        paper_id = data.split("|", 1)[1]
        db.add_seen_paper(user_id, paper_id)
        papers = db.get_user_library(user_id)
        paper = next((p for p in papers if p.get("id") == paper_id or p.get("fingerprint") == paper_id), None)
        if paper:
            keywords = search_engine.parse_words(paper.get("title", ""))[:5]
            db.update_user_bias(user_id, keywords, is_positive=False)
            title_display = paper.get("title", paper_id)
        else:
            title_display = paper_id
        bot.answer_callback_query(call.id, _t(user_id, "mark_skip_callback"))
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, _t(user_id, "mark_skip", title=title_display[:100]))
        return

    # 選擇資料夾
    if data.startswith("choose_folder|"):
        paper_id = data.split("|", 1)[1]
        lang = _get_lang(user_id, call.from_user.language_code)
        markup = _build_folder_keyboard(user_id, paper_id, lang)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, _t(user_id, "archive_choose_folder"), reply_markup=markup)
        return

    # 執行歸檔
    if data.startswith("archive|"):
        parts = data.split("|")
        if len(parts) < 3:
            bot.answer_callback_query(call.id, _t(user_id, "archive_invalid_button"), show_alert=True)
            return
        paper_id = parts[1]
        folder_name = parts[2]
        if folder_name == "返回":
            bot.answer_callback_query(call.id, _t(user_id, "archive_skip_archive"))
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            return

        papers = db.get_user_library(user_id)
        paper = next((p for p in papers if str(p.get("id", ""))[:40] == paper_id or str(p.get("fingerprint", ""))[:40] == paper_id), None)
        if not paper:
            paper = _pending_papers.get(paper_id)
        if not paper:
            paper = {"id": paper_id, "title": "Untitled", "summary": "", "link": "", "authors": [], "year": "2024", "category": folder_name}
            db.add_paper_to_library(user_id, paper)
        bot.answer_callback_query(call.id, _t(user_id, "archive_archiving"))
        bibtex_str = paper.get("bibtex", "") or search_engine.generate_bibtex_str(
            title=paper.get("title", ""),
            authors=paper.get("authors", []),
            year=paper.get("year", ""),
            link=paper.get("link", ""),
            source=paper.get("source", "")
        )
        if bibtex_str and not paper.get("bibtex"):
            paper["bibtex"] = bibtex_str
            paper["category"] = folder_name
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
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            bot.send_message(call.message.chat.id, _t(user_id, "archive_success", folder=folder_name, title=paper.get("title", "")[:80]))
        else:
            if "尚未完成 Google 授權" in str(result):
                auth_url = drive_manager.get_auth_url(user_id)
                if auth_url:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton(_t(user_id, "archive_drive_auth_button"), url=auth_url))
                    bot.send_message(call.message.chat.id, _t(user_id, "archive_drive_auth_prompt"), reply_markup=markup)
                else:
                    bot.send_message(call.message.chat.id, _t(user_id, "archive_drive_not_configured"))
            else:
                err_detail = str(result)
                if "invalid_scope" in err_detail or "invalid_grant" in err_detail:
                    db.remove_token(user_id)
                    auth_url = drive_manager.get_auth_url(user_id)
                    if auth_url:
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton(_t(user_id, "archive_drive_auth_button"), url=auth_url))
                        bot.send_message(call.message.chat.id, _t(user_id, "archive_failed", detail="Google Drive 授權已過期，請重新授權") + "\n\n👇 請點擊下方按鈕重新授權：", reply_markup=markup)
                    else:
                        bot.send_message(call.message.chat.id, _t(user_id, "archive_failed", detail="Google Drive 授權已過期，請用 /drive 重新授權"))
                else:
                    bot.send_message(call.message.chat.id, _t(user_id, "archive_failed", detail=err_detail))
        return

# 未知指令處理
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/') and not any([
    message.text.startswith('/start'), message.text.startswith('/help'),
    message.text.startswith('/my'), message.text.startswith('/chat'),
    message.text.startswith('/bind'), message.text.startswith('/pro'),
    message.text.startswith('/following'), message.text.startswith('/follow '),
    message.text.startswith('/unfollow '), message.text.startswith('/review'),
    message.text.startswith('/gap'), message.text.startswith('/trend'),
    message.text.startswith('/export'), message.text.startswith('/mode'),
    message.text.startswith('/lang'), message.text.startswith('/reports'),
    message.text.startswith('/drive'), message.text.startswith('/web'),
    message.text.startswith('/folders'), message.text.startswith('/myfolders'),
    message.text.startswith('/categories'), message.text.startswith('/cats'),
]))
def handle_unknown_command(message):
    user_id = message.from_user.id
    cmd = message.text.split()[0].split('@')[0]
    bot.reply_to(message, _t(user_id, "unknown_command", cmd=cmd))

# ===================== 8. 科研大總部 Web REST API =====================
@app.route("/api/view_reports", methods=["GET"])
def api_view_reports():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return {"error": "缺少 user_id 參數"}, 400
    reports = db.get_user_reports(user_id)
    return {"success": True, "reports": reports, "count": len(reports)}, 200

@app.route("/api/telegram_login", methods=["POST"])
def api_telegram_login():
    data = request.json or {}
    user_id = data.get("user_id")
    username = data.get("username", "Telegram User")
    if not user_id:
        return {"error": "缺少 user_id"}, 400
    try:
        user_id = int(user_id)
    except ValueError:
        return {"error": "無效的 user_id"}, 400
    tier = db.get_user_tier(user_id).get("tier", "free")
    papers = db.get_user_library(user_id)
    return {
        "success": True,
        "message": f"歡迎回來，{username}！已成功登入 PaperFilterBot 科研大總部。",
        "user": {
            "user_id": user_id,
            "username": username,
            "tier": tier,
            "library_count": len(papers)
        }
    }, 200

@app.route("/api/user_library", methods=["GET"])
def api_user_library():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return {"error": "缺少 user_id"}, 400
    papers = db.get_user_library(user_id)
    categories = db.get_user_categories(user_id)
    return {"success": True, "library": papers, "categories": categories}, 200

@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    granted_scope = request.args.get("scope", "")
    if error:
        return f"<h3>授權失敗：{error}</h3>", 400
    if not code or not state:
        return "<h3>缺少必要參數</h3>", 400
    try:
        user_id = int(state)
    except ValueError:
        return "<h3>無效的 state 參數</h3>", 400
    print(f"🔗 OAuth callback — granted scope: {granted_scope}", file=sys.stderr)
    success, detail = drive_manager.exchange_code(user_id, code)
    if success:
        try:
            bot.send_message(user_id, _t(user_id, "drive_auth_success"))
        except Exception:
            pass
        return "<h3>✅ Google Drive 授權成功！請回到 Telegram 繼續使用。</h3>"
    else:
        has_drive = "drive.file" in granted_scope
        if not has_drive:
            msg = (
                "⚠️ Google 未授予 drive.file 權限。\n\n"
                "<b>請在 Google Cloud Console 做以下檢查：</b>\n"
                "1. 進入 APIs & Services → OAuth consent screen → Data Access\n"
                "2. 確認已加入 Google Drive API (drive.file) scope\n"
                "3. 點擊「PUBLISH」讓 scope 狀態變成 In production\n"
                "4. 如果是 Testing 模式，需將你的 email 加入 Test users\n\n"
                "設定好後請打 /drive revoke 再重新授權。"
            )
            return f"<h3>{msg}</h3>", 500
        return f"<h3>❌ 授權失敗：{detail}</h3>", 500

@app.route("/")
def index():
    return "PaperFilterBot Pro is running! 🤖", 200

@app.route("/health")
def health():
    return "OK", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        abort(403)

# ===================== 9. 伺服器/本機 Polling 啟動 =====================
if __name__ == "__main__":
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook 模式啟動：{webhook_url}", file=sys.stderr)
        app.run(host="0.0.0.0", port=PORT)
    else:
        print("✅ Polling 模式啟動（本機測試）...", file=sys.stderr)
        bot.remove_webhook()
        bot.infinity_polling(timeout=20, long_polling_timeout=15)
