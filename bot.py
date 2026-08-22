import os
import sys
import json
import html
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
            "👋 嗨 <b>{name}</b>，這是 <b>PaperFilterBot</b>。\n\n"
            "文獻每天多到篩不完時，在這裡打自己領域的關鍵字（例如 <code>CRISPR</code>）。"
            "會從 arXiv、PubMed、Semantic Scholar、CrossRef、OpenAlex 撈一批，依相關與新舊排序。\n\n"
            "卡片上可以：\n"
            "• 👎 沒興趣 — 之後較少再推同類\n"
            "• 看過／收藏進自己的庫\n"
            "• 短導讀與深度導讀 — <b>只根據標題和摘要</b>，沒有讀 PDF\n\n"
            "這是測試版。排序會偏、導讀可能講錯。"
            "請用 <code>/feedback</code> 寫具體問題（例如太偏 CS、太舊）。指令一覽：<code>/help</code>\n\n"
            "若久沒回覆，等一分鐘再傳一次 <code>hi</code>。直接打關鍵字即可搜尋。"
        ),
        "help": (
            "📖 <b>PaperFilterBot 指令與按鈕</b>\n\n"
            "<b>搜尋</b>\n"
            "直接打關鍵字，或 <code>/search 關鍵字</code>\n"
            "來源：arXiv / PubMed / Semantic Scholar / Crossref / OpenAlex\n"
            "導讀只根據標題和摘要，沒有讀 PDF。沒有早上自動推播。\n\n"
            "<b>過濾與回饋</b>\n"
            "• <code>/digest CRISPR, LLM</code> — 立刻過濾今日新論文\n"
            "• <code>/digest</code> 再跑一次　• <code>/digest off</code> 關閉\n"
            "• <code>/feedback 意見</code> — 打給開發者\n"
            "• <code>/waitlist</code> — 之後若收費想被通知\n"
            "• <code>/redeem PF-XXXXXX</code>\n\n"
            "<b>文獻庫</b>\n"
            "• <code>/my</code> — 庫、資料夾、Drive 狀態\n"
            "• <code>/folders</code> — 分類資料夾\n"
            "• <code>/export</code> — BibTeX / RIS / CSV\n"
            "• <code>/chat</code> 或 <code>/ask</code> — 針對已看過的文獻提問（有額度）\n"
            "• <code>/review</code> — 依收藏的標題與摘要寫綜述草稿\n"
            "• <code>/gap</code> — 依收藏文獻分析缺口（同樣根據摘要）\n"
            "• <code>/reports</code> — 綜述歷史\n\n"
            "<b>偏好</b>\n"
            "• <code>/follow 學者名</code> — 搜尋提高該名字權重（不會自動抓動態）\n"
            "• <code>/unfollow 學者名</code>　• <code>/following</code>\n"
            "• <code>/mode</code> — 頂刊 / 智慧 / 只 OA\n"
            "• <code>/lang</code>\n\n"
            "<b>網頁與雲端</b>\n"
            "• <code>/bind</code> 或 <code>/web</code> — 科研大總部（同一 Telegram 帳才同步）\n"
            "• <code>/drive</code> — Google Drive（授權失敗就當沒這功能）\n"
            "• <code>/pro</code>　• <code>/start</code>　• <code>/help</code>\n\n"
            "<b>搜尋結果卡片按鈕</b>\n"
            "深度導讀、看過了、沒興趣、歸檔到雲端、免費全文 (OA)、官方 DOI\n\n"
            "<b>選單按鈕</b>\n"
            "檢索論文、開啟科研大總部、綁定同步碼、Pro、切換語言、完整指令\n\n"
            "若沒反應，等 30–60 秒再傳 <code>hi</code>。"
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
        "btn_open_web": "🌐 開啟科研大總部",
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
        "deep_processing": "🧠 AI 正在依據標題與摘要萃取結構化要點，請稍候...",
        "deep_header": "💡 <b>AI 深度導讀報告（依據標題與摘要）</b>",
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
        "tier_pro": "Pro 方案",
        "tier_basic": "Basic 方案",
        "tier_standard": "Standard 方案",
        "tier_premium": "Premium 方案",
        "tier_ultra": "Ultra 方案",
        "tier_lab": "實驗室方案",
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
        "tier_report_weekly_n": "每週 {count} 次",
        "tier_report_unlimited": "無限制",
        "pro_combo_rgc": "/review + /gap + /chat：各 {count}/日",
        "pro_text_header": "📊 <b>PaperFilterBot 方案比較</b>\n\n👤 您目前方案：{tier}\n",
        "pro_text_footer": "💡 可在科研大總部一鍵升級！",
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
        "chat_disclaimer": "\n\n---\n📚 <i>以上分析僅基於您文獻庫中的論文，不代表全域學術觀點。升級 Pro 可提高每日問答次數。</i>",
        "reports_empty": "📝 您目前尚無生成的文獻綜述報告。可使用 <code>/review 主題</code> 立即生成！",
        "reports_list_header": "📑 <b>您生成的學術綜述報告清單（共 {count} 份）：</b>\n\n",
        "reports_list_footer": "\n可在網頁端科研大總部查看全文與匯出 Markdown/PDF！",
        "follow_missing_args": "請輸入學者名稱，例如：<code>/follow Yann LeCun</code>",
        "unfollow_missing_args": "請輸入要取消追蹤的學者名稱。",
        "library_full": "📚 文獻庫已滿（{limit} 篇）。請刪除部分論文，或升級 Pro 以擴大容量。",
        "follow_limit_reached": "👤 追蹤學者已達上限（{limit} 位）。請取消部分追蹤，或升級 Pro。",
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
        "bind_no_code": "請先開啟網頁端「研究大總部」，點「連接 Telegram」取得 6 位驗證碼，再輸入 <code>/bind 你的碼</code> 完成綁定。",
        "bind_success": "✅ 已與網頁端綁定！你的文獻庫、歷史與方案現在雙向同步，且資料始終跟著你的 Telegram 帳號。",
        "bind_invalid": "❌ 驗證碼無效或已過期，請在網頁端重新產生一組驗證碼。",
        "help_bind_button": "🔗 綁定網頁端",
        "help_pro_button": "👑 查看 Pro 特權",
        "unknown_command": "❌ 沒有此指令：{cmd}\n請輸入 /help 查看所有可用指令。",
        "help_beta_extra": "",
        "beta_mission": (
            "🧪 <b>7 天測試任務</b>（請盡量做完，這決定正式版要不要收費）\n"
            "1. 傳自己領域的關鍵字搜 5 次，把沒興趣的按 👎\n"
            "2. 收藏至少 3 篇，到網頁看是否同一庫\n"
            "3. <code>/digest 你的主題</code> 看今日過濾準不準\n"
            "4. 用 <code>/feedback</code> 罵得越具體越好\n"
            "5. 若 7 天後還想留著 → <code>/waitlist</code>"
        ),
        "digest_usage": "用法：<code>/digest CRISPR, graph neural network</code>\n關掉：<code>/digest off</code>",
        "digest_off": "已關閉每日過濾。再設定主題即可重新打開。",
        "digest_on": "✅ 已記住主題：<b>{topics}</b>\n正在拉取你還沒看過的論文（依據標題與摘要，不含全文）…",
        "digest_header": "📬 <b>今日過濾</b> · {topics}\n沒興趣請按 👎，系統會越來越準。",
        "digest_empty": "這批主題暫時沒有你沒看過的新論文。明天再試，或換關鍵字。",
        "digest_need_pro": "每日過濾是 Pro 功能。測試請 /redeem 測試碼，或先用關鍵字搜尋。",
        "feedback_usage": "用法：<code>/feedback 搜尋太偏 CS、我要的是植物病理</code>",
        "feedback_ok": "✅ 收到。正式版會優先改測試者反覆提到的問題。",
        "waitlist_ok": "✅ 已列入正式版候補。金流開放時會從 Telegram 通知你。",
        "waitlist_already": "你已在候補名單裡。",
        "trial_expiring": "⏰ 測試 Pro 將於 <b>{expires}</b> 到期（不到 24 小時）。\n若這週少不了它：<code>/waitlist</code>\n有話要罵：<code>/feedback ...</code>",
        "paper_et_al": "等 {count} 位",
        "paper_seen_badge": "👁 [已看過]",
        "paper_ai_summary": "🧠 <b>AI 導讀：</b>\n{text}",
        "card_summary_generating": "🧠 <b>AI 導讀：</b>\n⏳ 生成中…",
        "card_citations": "引用",
        "card_disclaimer": "AI 摘要僅供快速理解，正式引用請核對原文。",
        "deep_disclaimer": "此深度導讀由 AI 根據論文摘要生成，僅供快速理解，正式引用請務必核對原文。",
        "mode_switched_confirm": "✅ 已切換為 {mode}",
        "lang_switched_confirm": "✅ 語言已切換為 {lang}",
        "mark_seen_callback": "👁 已標記為已讀",
        "mark_skip_callback": "❌ 已略過",
        "pro_text": "",
        "promo_generated": "🎫 測試碼已生成：<code>{code}</code>\n備註：{note}\n⏳ 請在 72 小時內兌換（/redeem {code}）",
        "promo_admin_only": "⛔ 此指令僅限管理員使用。",
        "promo_redeem_ok": "🎉 兌換成功！全功能已開通至 <b>{expires}</b>（7 天）。\n👑 感謝你成為 Beta 測試員——測試過程中任何想法都歡迎直接傳訊告訴我！",
        "promo_redeem_usage": "用法：<code>/redeem PF-XXXXXX</code>",
        "promo_invalid": "❌ 找不到這組測試碼，請確認後重試。",
        "promo_already_used": "⚠️ 這組測試碼已被使用。",
        "promo_expired": "⏰ 這組測試碼已過期（72 小時兌換期限），請聯絡發碼人重新生成。",
        "codes_header": "🎫 測試碼總覽（{used} 已用 / {unused} 未用 / {expired} 過期）：\n\n",
        "codes_empty": "目前沒有任何測試碼。用 /gencode 產生第一組。",
        "feedbacks_empty": "目前還沒有回饋。",
        "feedbacks_header": "📬 最新回饋（{n} 則，新到舊）：",
        "founder_granted": "👑 已將 <code>{uid}</code> 設為 Founding Member（終身全功能）！",
        "founder_fail": "找不到該使用者（需先與 Bot 有過互動）。",
        "founder_badge_line": "\n👑 <b>Founding Member</b> · 終身榮譽全功能\n",
    },
    "zh_hans": {
        "welcome": (
            "👋 嗨 <b>{name}</b>，这是 <b>PaperFilterBot</b>。\n\n"
            "文献每天多到筛不完时，在这里打自己领域的关键词（例如 <code>CRISPR</code>）。"
            "会从 arXiv、PubMed、Semantic Scholar、CrossRef、OpenAlex 捞一批，按相关与新旧排序。\n\n"
            "卡片上可以：\n"
            "• 👎 没兴趣 — 之后较少再推同类\n"
            "• 看过／收藏进自己的库\n"
            "• 短导读与深度导读 — <b>只根据标题和摘要</b>，没有读 PDF\n\n"
            "这是测试版。排序会偏、导读可能说错。"
            "请用 <code>/feedback</code> 写具体问题。指令一览：<code>/help</code>\n\n"
            "若久没回复，等一分钟再发一次 <code>hi</code>。直接打关键词即可搜索。"
        ),
        "help": (
            "📖 <b>PaperFilterBot 指令与按钮</b>\n\n"
            "<b>搜索</b>\n"
            "直接打关键词，或 <code>/search 关键词</code>\n"
            "来源：arXiv / PubMed / Semantic Scholar / Crossref / OpenAlex\n"
            "导读只根据标题和摘要，没有读 PDF。没有早上自动推送。\n\n"
            "<b>过滤与反馈</b>\n"
            "• <code>/digest CRISPR, LLM</code> — 立刻过滤今日新论文\n"
            "• <code>/digest</code> 再跑一次　• <code>/digest off</code> 关闭\n"
            "• <code>/feedback 意见</code> — 打给开发者\n"
            "• <code>/waitlist</code> — 之后若收费想被通知\n"
            "• <code>/redeem PF-XXXXXX</code>\n\n"
            "<b>文献库</b>\n"
            "• <code>/my</code> — 库、文件夹、Drive 状态\n"
            "• <code>/folders</code> — 分类文件夹\n"
            "• <code>/export</code> — BibTeX / RIS / CSV\n"
            "• <code>/chat</code> 或 <code>/ask</code> — 针对已看过的文献提问（有额度）\n"
            "• <code>/review</code> — 依收藏的标题与摘要写综述草稿\n"
            "• <code>/gap</code> — 依收藏文献分析缺口（同样根据摘要）\n"
            "• <code>/reports</code> — 综述历史\n\n"
            "<b>偏好</b>\n"
            "• <code>/follow 学者名</code> — 搜索提高该名字权重（不会自动抓动态）\n"
            "• <code>/unfollow 学者名</code>　• <code>/following</code>\n"
            "• <code>/mode</code> — 顶刊 / 智能 / 只 OA\n"
            "• <code>/lang</code>\n\n"
            "<b>网页与云端</b>\n"
            "• <code>/bind</code> 或 <code>/web</code> — 科研大总部（同一 Telegram 帐才同步）\n"
            "• <code>/drive</code> — Google Drive（授权失败就当没这功能）\n"
            "• <code>/pro</code>　• <code>/start</code>　• <code>/help</code>\n\n"
            "<b>搜索结果卡片按钮</b>\n"
            "深度导读、看过了、没兴趣、归档到云端、免费全文 (OA)、官方 DOI\n\n"
            "<b>菜单按钮</b>\n"
            "检索论文、开启科研大总部、绑定同步码、Pro、切换语言、完整指令\n\n"
            "若没反应，等 30–60 秒再传 <code>hi</code>。"
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
        "btn_open_web": "🌐 打开科研大总部",
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
        "deep_processing": "🧠 AI 正在依据标题与摘要萃取结构化要点，请稍候...",
        "deep_header": "💡 <b>AI 深度导读报告（依据标题与摘要）</b>",
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
        "tier_pro": "Pro 方案",
        "tier_basic": "Basic 方案",
        "tier_standard": "Standard 方案",
        "tier_premium": "Premium 方案",
        "tier_ultra": "Ultra 方案",
        "tier_lab": "实验室方案",
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
        "tier_report_weekly_n": "每周 {count} 次",
        "tier_report_unlimited": "无限制",
        "pro_combo_rgc": "/review + /gap + /chat：各 {count}/日",
        "pro_text_header": "📊 <b>PaperFilterBot 方案比较</b>\n\n👤 您目前方案：{tier}\n",
        "pro_text_footer": "💡 可在科研大总部一键升级！",
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
        "chat_disclaimer": "\n\n---\n📚 <i>以上分析仅基于您文献库中的论文，不代表全域学术观点。升级 Pro 可提高每日问答次数。</i>",
        "reports_empty": "📝 您目前尚无生成的文献综述报告。可使用 <code>/review 主题</code> 立即生成！",
        "reports_list_header": "📑 <b>您生成的学术综述报告清单（共 {count} 份）：</b>\n\n",
        "reports_list_footer": "\n可在网页端科研大总部查看全文与导出 Markdown/PDF！",
        "follow_missing_args": "请输入学者名称，例如：<code>/follow Yann LeCun</code>",
        "unfollow_missing_args": "请输入要取消追踪的学者名称。",
        "library_full": "📚 文献库已满（{limit} 篇）。请删除部分论文，或升级 Pro 以扩大容量。",
        "follow_limit_reached": "👤 追踪学者已达上限（{limit} 位）。请取消部分追踪，或升级 Pro。",
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
        "bind_no_code": "请先打开网页端「研究大总部」，点「连接 Telegram」取得 6 位验证码，再输入 <code>/bind 你的码</code> 完成绑定。",
        "bind_success": "✅ 已与网页端绑定！你的文献库、历史与方案现在双向同步，且数据始终跟着你的 Telegram 账号。",
        "bind_invalid": "❌ 验证码无效或已过期，请在网页端重新生成一组验证码。",
        "help_bind_button": "🔗 绑定网页端",
        "help_pro_button": "👑 查看 Pro 特权",
        "unknown_command": "❌ 没有此指令：{cmd}\n请输入 /help 查看所有可用指令。",
        "help_beta_extra": "",
        "beta_mission": (
            "🧪 <b>7 天测试任务</b>\n"
            "1. 用自己领域的关键词搜 5 次，没兴趣按 👎\n"
            "2. 收藏至少 3 篇，到网页确认同一库\n"
            "3. <code>/digest 你的主题</code>\n"
            "4. <code>/feedback</code> 写具体问题\n"
            "5. 还想留着 → <code>/waitlist</code>"
        ),
        "digest_usage": "用法：<code>/digest CRISPR, graph neural network</code>\n关闭：<code>/digest off</code>",
        "digest_off": "已关闭每日过滤。",
        "digest_on": "✅ 已记住主题：<b>{topics}</b>\n正在拉取你还没看过的论文…",
        "digest_header": "📬 <b>今日过滤</b> · {topics}\n没兴趣请按 👎。",
        "digest_empty": "这批主题暂时没有你没看过的新论文。",
        "digest_need_pro": "每日过滤是 Pro 功能。测试请 /redeem，或先用关键词搜索。",
        "feedback_usage": "用法：<code>/feedback 搜索太偏 CS</code>",
        "feedback_ok": "✅ 收到。",
        "waitlist_ok": "✅ 已列入正式版候补。",
        "waitlist_already": "你已在候补名单里。",
        "trial_expiring": "⏰ 测试 Pro 将于 <b>{expires}</b> 到期。想留着请 /waitlist。",
        "paper_et_al": "等 {count} 位",
        "paper_seen_badge": "👁 [已看过]",
        "paper_ai_summary": "🧠 <b>AI 导读：</b>\n{text}",
        "card_summary_generating": "🧠 <b>AI 导读：</b>\n⏳ 生成中…",
        "card_citations": "引用",
        "card_disclaimer": "AI 摘要仅供快速理解，正式引用请核对原文。",
        "deep_disclaimer": "此深度导读由 AI 根据论文摘要生成，仅供快速理解，正式引用请务必核对原文。",
        "mode_switched_confirm": "✅ 已切换为 {mode}",
        "lang_switched_confirm": "✅ 语言已切换为 {lang}",
        "mark_seen_callback": "👁 已标记为已读",
        "mark_skip_callback": "❌ 已跳过",
        "pro_text": "",
        "promo_generated": "🎫 测试码已生成：<code>{code}</code>\n备注：{note}\n⏳ 请在 72 小时内兑换（/redeem {code}）",
        "promo_admin_only": "⛔ 此指令仅限管理员使用。",
        "promo_redeem_ok": "🎉 兑换成功！全功能已开通至 <b>{expires}</b>（7 天）。\n👑 感谢你成为 Beta 测试员——测试过程中任何想法都欢迎直接传讯告诉我！",
        "promo_redeem_usage": "用法：<code>/redeem PF-XXXXXX</code>",
        "promo_invalid": "❌ 找不到这组测试码，请确认后重试。",
        "promo_already_used": "⚠️ 这组测试码已被使用。",
        "promo_expired": "⏰ 这组测试码已过期（72 小时兑换期限），请联系发码人重新生成。",
        "codes_header": "🎫 测试码总览（{used} 已用 / {unused} 未用 / {expired} 过期）：\n\n",
        "codes_empty": "目前没有任何测试码。用 /gencode 产生第一组。",
        "feedbacks_empty": "目前还没有反馈。",
        "feedbacks_header": "📬 最新反馈（{n} 则，新到旧）：",
        "founder_granted": "👑 已将 <code>{uid}</code> 设为 Founding Member（终身全功能）！",
        "founder_fail": "找不到该用户（需先与 Bot 有过互动）。",
        "founder_badge_line": "\n👑 <b>Founding Member</b> · 终身荣誉全功能\n",
    },
    "en": {
        "welcome": (
            "👋 Hi <b>{name}</b>, this is <b>PaperFilterBot</b>.\n\n"
            "When too many new papers land each day, type a topic from your field (e.g. <code>CRISPR</code>). "
            "It searches arXiv, PubMed, Semantic Scholar, CrossRef, and OpenAlex, then ranks by relevance and recency.\n\n"
            "On each card you can:\n"
            "• 👎 skip — similar papers show up less later\n"
            "• mark seen / save to your library\n"
            "• short and deep summaries — <b>title and abstract only</b>, not the PDF\n\n"
            "This is a beta. Ranking will be wrong sometimes; the AI can misread an abstract. "
            "Tell me with <code>/feedback</code> (e.g. too CS-heavy, too old). Commands: <code>/help</code>\n\n"
            "If nothing comes back, wait a minute and send <code>hi</code> again. Or just type keywords to search."
        ),
        "help": (
            "📖 <b>PaperFilterBot commands and buttons</b>\n\n"
            "<b>Search</b>\n"
            "Type keywords, or <code>/search keywords</code>\n"
            "Sources: arXiv / PubMed / Semantic Scholar / Crossref / OpenAlex\n"
            "Deep read is title + abstract only — no PDFs. No morning auto-push.\n\n"
            "<b>Filter and feedback</b>\n"
            "• <code>/digest CRISPR, LLM</code> — filter today's new papers now\n"
            "• <code>/digest</code> run again　• <code>/digest off</code>\n"
            "• <code>/feedback notes</code> — sent to the developer\n"
            "• <code>/waitlist</code> — ping if paid Pro ever launches\n"
            "• <code>/redeem PF-XXXXXX</code>\n\n"
            "<b>Library</b>\n"
            "• <code>/my</code> — library, folders, Drive status\n"
            "• <code>/folders</code>\n"
            "• <code>/export</code> — BibTeX / RIS / CSV\n"
            "• <code>/chat</code> or <code>/ask</code> — questions on papers you've seen (quota)\n"
            "• <code>/review</code> — review draft from saved titles/abstracts\n"
            "• <code>/gap</code> — gap notes from saved papers (abstracts too)\n"
            "• <code>/reports</code> — review history\n\n"
            "<b>Prefs</b>\n"
            "• <code>/follow Name</code> — boosts that name in search (no author feed)\n"
            "• <code>/unfollow Name</code>　• <code>/following</code>\n"
            "• <code>/mode</code> — top-tier / smart / OA only\n"
            "• <code>/lang</code>\n\n"
            "<b>Web and Drive</b>\n"
            "• <code>/bind</code> or <code>/web</code> — Web HQ (same Telegram account to sync)\n"
            "• <code>/drive</code> — Google Drive (skip if OAuth fails)\n"
            "• <code>/pro</code>　• <code>/start</code>　• <code>/help</code>\n\n"
            "<b>Result-card buttons</b>\n"
            "Deep read, Seen, Not interested, Archive, Open Access, DOI\n\n"
            "<b>Menu buttons</b>\n"
            "Search, Open Web HQ, Bind, Pro, Language, Full help\n\n"
            "If nothing comes back, wait 30–60s and send <code>hi</code>."
        ),
        "btn_search": "🔍 Search Papers",
        "btn_web": "💻 Open Web HQ",
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
        "btn_open_web": "🌐 Open Web HQ",
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
        "deep_processing": "🧠 AI is analyzing the title and abstract for structured highlights...",
        "deep_header": "💡 <b>AI Deep Reading (title & abstract)</b>",
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
        "tier_pro": "Pro",
        "tier_basic": "Basic Plan",
        "tier_standard": "Standard Plan",
        "tier_premium": "Premium Plan",
        "tier_ultra": "Ultra Plan",
        "tier_lab": "Lab Plan",
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
        "tier_report_weekly_n": "{count}/week",
        "tier_report_unlimited": "Unlimited",
        "pro_combo_rgc": "/review + /gap + /chat: {count}/day each",
        "pro_text_header": "📊 <b>PaperFilterBot Plan Comparison</b>\n\n👤 Your current plan: {tier}\n",
        "pro_text_footer": "💡 Upgrade now at Web Research HQ!",
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
        "chat_disclaimer": "\n\n---\n📚 <i>Analysis based only on your library papers. Upgrade to Pro for a higher daily Q&A quota.</i>",
        "reports_empty": "📝 No reports yet. Use <code>/review [Topic]</code> to generate one!",
        "reports_list_header": "📑 <b>Your Literature Reports ({count} total):</b>\n\n",
        "reports_list_footer": "\nView full text & export Markdown/PDF at Web Research HQ!",
        "follow_missing_args": "Enter author name, e.g.: <code>/follow Yann LeCun</code>",
        "unfollow_missing_args": "Enter the author name to unfollow.",
        "library_full": "📚 Library is full ({limit} papers). Delete some papers or upgrade to Pro.",
        "follow_limit_reached": "👤 Follow limit reached ({limit}). Unfollow someone or upgrade to Pro.",
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
        "bind_no_code": "Open the Web Research HQ, click Connect Telegram to get a 6-digit code, then send <code>/bind YOURCODE</code> to link.",
        "bind_success": "✅ Linked to the Web app! Your library, history and plan are now synced both ways, and your data always stays with your Telegram account.",
        "bind_invalid": "❌ Invalid or expired code. Generate a new one in the Web app.",
        "help_bind_button": "🔗 Bind to Web",
        "help_pro_button": "👑 View Pro Features",
        "unknown_command": "❌ Unknown command: {cmd}\nType /help to see all commands.",
        "help_beta_extra": "",
        "beta_mission": (
            "<b>7-day beta mission</b>\n"
            "1. Search your field 5 times; 👎 what you don't want\n"
            "2. Save ≥3 papers; confirm they show up on the web\n"
            "3. <code>/digest your topics</code>\n"
            "4. <code>/feedback</code> with specifics\n"
            "5. Still need it after 7 days → <code>/waitlist</code>"
        ),
        "digest_usage": "Usage: <code>/digest CRISPR, graph neural network</code>\nOff: <code>/digest off</code>",
        "digest_off": "Daily filter off.",
        "digest_on": "✅ Topics saved: <b>{topics}</b>\nFetching papers you haven't seen…",
        "digest_header": "📬 <b>Today's filter</b> · {topics}\n👎 anything off-topic.",
        "digest_empty": "No unseen papers for these topics right now.",
        "digest_need_pro": "Daily filter is Pro. Redeem a test code or search by keyword.",
        "feedback_usage": "Usage: <code>/feedback search is too CS-heavy</code>",
        "feedback_ok": "✅ Logged. Repeated tester complaints get fixed first.",
        "waitlist_ok": "✅ You're on the launch list. We'll message you when paid Pro opens.",
        "waitlist_already": "You're already on the list.",
        "trial_expiring": "⏰ Trial Pro ends <b>{expires}</b> (under 24h).\nWant to keep it? <code>/waitlist</code>\nNotes: <code>/feedback ...</code>",
        "paper_et_al": "et al. ({count} authors)",
        "paper_seen_badge": "👁 [Seen]",
        "paper_ai_summary": "🧠 <b>AI Summary:</b>\n{text}",
        "card_summary_generating": "🧠 <b>AI Summary:</b>\n⏳ Generating…",
        "card_citations": "citations",
        "card_disclaimer": "AI summary for quick reference only. Please verify against the original paper before citing.",
        "deep_disclaimer": "This deep reading was generated by AI based on the paper abstract for quick reference only. Please verify against the original paper before citing.",
        "mode_switched_confirm": "✅ Switched to {mode}",
        "lang_switched_confirm": "✅ Language set to {lang}",
        "mark_seen_callback": "👁 Marked as read",
        "mark_skip_callback": "❌ Skipped",
        "pro_text": "",
        "promo_generated": "🎫 Test code generated: <code>{code}</code>\nNote: {note}\n⏳ Must be redeemed within 72 hours (/redeem {code})",
        "promo_admin_only": "⛔ Admin only.",
        "promo_redeem_ok": "🎉 Redeemed! Full access unlocked until <b>{expires}</b> (7 days).\n👑 Thanks for joining the beta — feel free to message me anytime with feedback!",
        "promo_redeem_usage": "Usage: <code>/redeem PF-XXXXXX</code>",
        "promo_invalid": "❌ Code not found. Please double-check and try again.",
        "promo_already_used": "⚠️ This code has already been used.",
        "promo_expired": "⏰ This code has expired (72-hour redemption window). Please ask for a new one.",
        "codes_header": "🎫 Test codes ({used} used / {unused} unused / {expired} expired):\n\n",
        "codes_empty": "No test codes yet. Use /gencode to create the first one.",
        "feedbacks_empty": "No feedback yet.",
        "feedbacks_header": "📬 Latest feedback ({n}, newest first):",
        "founder_granted": "👑 <code>{uid}</code> is now a Founding Member (lifetime full access)!",
        "founder_fail": "User not found (they need to interact with the bot first).",
        "founder_badge_line": "\n👑 <b>Founding Member</b> · Lifetime full access\n",
    },
    "ja": {
        "welcome": (
            "👋 こんにちは <b>{name}</b>、これは <b>PaperFilterBot</b> です。\n\n"
            "毎日新しい論文が多すぎるとき、自分の分野のキーワードを送ってください（例：<code>CRISPR</code>）。"
            "arXiv / PubMed / Semantic Scholar / CrossRef / OpenAlex から集め、関連度と新しさで並べます。\n\n"
            "カードでは：\n"
            "• 👎 興味なし — 似た論文を後で減らせます\n"
            "• 既読／ライブラリに保存\n"
            "• 短い解説と詳細解説 — <b>タイトルと要旨のみ</b>。PDF は読んでいません\n\n"
            "ベータ版です。順位は偏ることがあり、解説も間違えることがあります。"
            "<code>/feedback</code> で具体的に書いてください。コマンド一覧：<code>/help</code>\n\n"
            "返事がないときは1分待って <code>hi</code> を再送。キーワードを送れば検索できます。"
        ),
        "help": (
            "📖 <b>PaperFilterBot コマンドとボタン</b>\n\n"
            "<b>検索</b>\n"
            "キーワードを送るか <code>/search キーワード</code>\n"
            "出典：arXiv / PubMed / Semantic Scholar / Crossref / OpenAlex\n"
            "詳細解説はタイトルと要約のみ。PDFは読みません。朝の自動配信はありません。\n\n"
            "<b>フィルタとフィードバック</b>\n"
            "• <code>/digest CRISPR, LLM</code> — 今日の新着を今すぐフィルタ\n"
            "• <code>/digest</code> 再実行　• <code>/digest off</code>\n"
            "• <code>/feedback 意見</code> — 開発者に送る\n"
            "• <code>/waitlist</code> — 有料化時に通知\n"
            "• <code>/redeem PF-XXXXXX</code>\n\n"
            "<b>ライブラリ</b>\n"
            "• <code>/my</code> — 庫・フォルダ・Drive状態\n"
            "• <code>/folders</code>\n"
            "• <code>/export</code> — BibTeX / RIS / CSV\n"
            "• <code>/chat</code> または <code>/ask</code> — 既読論文への質問（回数制限あり）\n"
            "• <code>/review</code> — 保存したタイトルと要約からレビュー草稿\n"
            "• <code>/gap</code> — 保存文献からギャップ（要約ベース）\n"
            "• <code>/reports</code> — レビュー履歴\n\n"
            "<b>設定</b>\n"
            "• <code>/follow 著者名</code> — 検索でその名前を優遇（フィード自動取得なし）\n"
            "• <code>/unfollow 著者名</code>　• <code>/following</code>\n"
            "• <code>/mode</code> — トップ誌 / スマート / OAのみ\n"
            "• <code>/lang</code>\n\n"
            "<b>WebとDrive</b>\n"
            "• <code>/bind</code> または <code>/web</code> — Web総本部（同じTelegramアカウントで同期）\n"
            "• <code>/drive</code> — Google Drive（認証に失敗したら使わなくてよい）\n"
            "• <code>/pro</code>　• <code>/start</code>　• <code>/help</code>\n\n"
            "<b>検索カードのボタン</b>\n"
            "詳細解説、閲覧済み、興味なし、ドライブ保存、OA、DOI\n\n"
            "<b>メニューボタン</b>\n"
            "論文検索、Web総本部、連携コード、Pro、言語、コマンド一覧\n\n"
            "反応がないときは 30–60 秒待って <code>hi</code> を送ってください。"
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
        "btn_open_web": "🌐 Web総本部を開く",
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
        "deep_processing": "🧠 AI がタイトルと要約に基づいて要点を抽出しています...",
        "deep_header": "💡 <b>AI 詳細解説レポート（タイトルと要約に基づく）</b>",
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
        "tier_pro": "Pro プラン",
        "tier_basic": "Basic プラン",
        "tier_standard": "Standard プラン",
        "tier_premium": "Premium プラン",
        "tier_ultra": "Ultra プラン",
        "tier_lab": "Lab プラン",
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
        "tier_report_weekly_n": "週 {count} 回",
        "tier_report_unlimited": "無制限",
        "pro_combo_rgc": "/review + /gap + /chat：各 {count}/日",
        "pro_text_header": "📊 <b>PaperFilterBot プラン比較</b>\n\n👤 現在のプラン：{tier}\n",
        "pro_text_footer": "💡 Web研究総本部で今すぐアップグレード！",
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
        "chat_disclaimer": "\n\n---\n📚 <i>ライブラリの論文のみに基づく分析です。Pro にアップグレードすると毎日の Q&A 回数を増やせます。</i>",
        "reports_empty": "📝 レポートがまだありません。<code>/review [テーマ]</code> で作成してください！",
        "reports_list_header": "📑 <b>文献レビュー報告書（全 {count} 件）：</b>\n\n",
        "reports_list_footer": "\nWeb研究総本部で全文閲覧・Markdown/PDFエクスポートが可能！",
        "follow_missing_args": "著者名を入力してください。例：<code>/follow Yann LeCun</code>",
        "unfollow_missing_args": "フォロー解除する著者名を入力してください。",
        "library_full": "📚 ライブラリが上限です（{limit} 本）。論文を削除するか、Pro にアップグレードしてください。",
        "follow_limit_reached": "👤 フォロー上限です（{limit} 人）。解除するか、Pro にアップグレードしてください。",
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
        "bind_no_code": "Web 研究総本部を開き「Telegram 連携」で 6 桁のコードを取得し、<code>/bind あなたのコード</code> を送信して連携。",
        "bind_success": "✅ Web アプリと連携しました！文献庫・履歴・プランが双方向同期され、データは常にあなたの Telegram アカウントに紐づきます。",
        "bind_invalid": "❌ コードが無効または期限切れです。Web アプリで新しいコードを生成してください。",
        "help_bind_button": "🔗 Web連携",
        "help_pro_button": "👑 Pro機能を見る",
        "unknown_command": "❌ 未知のコマンド：{cmd}\n/help で利用可能なコマンド一覧を確認できます。",
        "help_beta_extra": "",
        "beta_mission": (
            "<b>7日間のテスト</b>\n"
            "1. 自分の分野で5回検索し、不要なら 👎\n"
            "2. 3本以上保存し、Webで同じ庫か確認\n"
            "3. <code>/digest テーマ</code>\n"
            "4. <code>/feedback</code>\n"
            "5. まだ必要なら <code>/waitlist</code>"
        ),
        "digest_usage": "使い方：<code>/digest CRISPR, graph neural network</code>\n停止：<code>/digest off</code>",
        "digest_off": "デイリーフィルタをオフにしました。",
        "digest_on": "✅ テーマ：<b>{topics}</b>\n未読論文を取得中…",
        "digest_header": "📬 <b>今日のフィルタ</b> · {topics}",
        "digest_empty": "このテーマの未読論文は今はありません。",
        "digest_need_pro": "デイリーフィルタは Pro です。/redeem するかキーワード検索を。",
        "feedback_usage": "使い方：<code>/feedback 検索がCSに偏っている</code>",
        "feedback_ok": "✅ 受け取りました。",
        "waitlist_ok": "✅ 正式版ウェイトリストに登録しました。",
        "waitlist_already": "すでに登録済みです。",
        "trial_expiring": "⏰ 試用 Pro は <b>{expires}</b> に終了します。残したい場合は /waitlist。",
        "paper_et_al": "他 {count} 名",
        "paper_seen_badge": "👁 [閲覧済み]",
        "paper_ai_summary": "🧠 <b>AI 解説：</b>\n{text}",
        "card_summary_generating": "🧠 <b>AI 解説：</b>\n⏳ 生成中…",
        "card_citations": "引用",
        "card_disclaimer": "AI による要約です。引用する場合は原著を必ずご確認ください。",
        "deep_disclaimer": "このディープリーディングは論文の要約を基に AI が生成したものです。引用する場合は原著を必ずご確認ください。",
        "mode_switched_confirm": "✅ {mode} に切り替えました",
        "lang_switched_confirm": "✅ 言語を {lang} に設定しました",
        "mark_seen_callback": "👁 既読に設定",
        "mark_skip_callback": "❌ スキップ済み",
        "pro_text": "",
        "promo_generated": "🎫 テストコードを生成しました：<code>{code}</code>\nメモ：{note}\n⏳ 72 時間以内に引き換えてください（/redeem {code}）",
        "promo_admin_only": "⛔ 管理者専用コマンドです。",
        "promo_redeem_ok": "🎉 引き換え完了！全機能が <b>{expires}</b> まで利用可能（7 日間）。\n👑 ベータテスターへの参加ありがとうございます——フィードバックはいつでもメッセージでどうぞ！",
        "promo_redeem_usage": "使い方：<code>/redeem PF-XXXXXX</code>",
        "promo_invalid": "❌ そのコードは見つかりません。確認して再試行してください。",
        "promo_already_used": "⚠️ このコードは既に使用されています。",
        "promo_expired": "⏰ このコードは期限切れです（72 時間の引き換え期限）。新しいコードを発行者にお問い合わせください。",
        "codes_header": "🎫 テストコード一覧（{used} 使用済 / {unused} 未使用 / {expired} 期限切れ）：\n\n",
        "codes_empty": "まだテストコードがありません。/gencode で最初の 1 枚を作成してください。",
        "feedbacks_empty": "まだフィードバックはありません。",
        "feedbacks_header": "📬 最新のフィードバック（{n} 件、新しい順）：",
        "founder_granted": "👑 <code>{uid}</code> を Founding Member（永久フルアクセス）に設定しました！",
        "founder_fail": "ユーザーが見つかりません（先に Bot とやり取りが必要です）。",
        "founder_badge_line": "\n👑 <b>Founding Member</b> · 永久フルアクセス\n",
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
WEB_APP_URL = os.getenv("WEB_APP_URL", "") or os.getenv("APP_URL", "")
PORT = int(os.getenv("PORT", 10000))
# Beta 測試碼管理員（逗號分隔的 Telegram user ID）
ADMIN_USER_IDS = {int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip().isdigit()}

def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS

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

def _fmt_quota(user_id, n):
    if n is None or n >= 999999:
        return _t(user_id, "tier_drive_unlimited")
    return str(n)

def _report_quota(user_id, n):
    if n is None or n >= 999999:
        return _t(user_id, "tier_report_unlimited")
    if n <= 0:
        return _t(user_id, "tier_report_none")
    return _t(user_id, "tier_report_weekly_n", count=n)

def _build_pro_text(user_id, current_label):
    """方案比較：Free / Pro。digest 以週計，Free 為 0。"""
    emojis = {"free": "🆓", "pro": "💎"}
    parts = [_t(user_id, "pro_text_header", tier=current_label)]
    for tc in ("free", "pro"):
        d = db.TIER_DEFS[tc]
        name = _t(user_id, f"tier_{tc}")
        search_n = _fmt_quota(user_id, d["daily_search_limit"])
        deep_n = _fmt_quota(user_id, d["daily_deep_limit"])
        combo_n = _fmt_quota(user_id, d.get("daily_chat_limit", d["daily_litreview_limit"]))
        drive_n = d["drive_monthly_limit"]
        if drive_n >= 999999:
            drive_line = f"• {_t(user_id, 'tier_drive')}：{_t(user_id, 'tier_drive_unlimited')}"
        else:
            drive_line = f"• {_t(user_id, 'tier_drive')}：{_t(user_id, 'tier_drive_limit', count=drive_n)}"
        report_line = f"• {_t(user_id, 'tier_report')}：{_report_quota(user_id, d['daily_digest_limit'])}"
        parts.append(
            f"{emojis[tc]} <b>{name}</b>\n"
            f"• {_t(user_id, 'tier_search_daily', count=search_n)}\n"
            f"• {_t(user_id, 'tier_deep_daily', count=deep_n)}\n"
            f"• {_t(user_id, 'pro_combo_rgc', count=combo_n)}\n"
            f"{drive_line}\n"
            f"{report_line}\n"
        )
    parts.append(_t(user_id, "pro_text_footer"))
    return "\n".join(parts)

def _try_follow_author(user_id, author_name) -> tuple[bool, str]:
    author_name = (author_name or "").strip()
    if not author_name:
        return False, _t(user_id, "follow_missing_args")
    existing = db.get_followed_authors(user_id)
    if author_name not in existing:
        limit = db.get_user_tier(user_id).get("follow_limit", 3)
        if len(existing) >= limit:
            return False, _t(user_id, "follow_limit_reached", limit=limit)
    db.add_followed_author(user_id, author_name)
    return True, _t(user_id, "follow_success", name=author_name)

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
    # 第一次接觸時，依 Telegram 語系自動存入偏好（僅在尚未設定時），讓網頁端也跟隨語言
    try:
        if not db.get_user_lang(user_id) and message.from_user.language_code:
            db.set_user_lang(user_id, _get_lang(user_id, message.from_user.language_code))
    except Exception:
        pass
    welcome_text = _t(user_id, "welcome", name=name)

    markup = make_main_menu(user_id)
    markup.add(
        types.InlineKeyboardButton(_t(user_id, "btn_full_help"), callback_data="cmd_help")
    )
    if WEB_APP_URL:
        markup.add(
            types.InlineKeyboardButton(_t(user_id, "btn_open_web"), url=WEB_APP_URL)
        )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")
    _check_trial_reminder(message)

@bot.message_handler(commands=['help', 'h', 'guide'])
def handle_help(message, override_user_id=None):
    user_id = override_user_id or message.from_user.id
    help_text = _t(user_id, "help") + _t(user_id, "help_beta_extra")

    # 管理員專屬：附加 Beta 測試碼管理指令（一般用戶與測試員看不到）
    if _is_admin(user_id):
        help_text += (
            "\n\n🔧 <b>── Admin / Beta Tools (hidden for others) ──</b>\n"
            "• <code>/gencode [note]</code> — 產生測試碼（72h 兌換期限）\n"
            "• <code>/codes</code> — 測試碼名冊（誰兌換了、ID 是多少）\n"
            "• <code>/feedbacks</code> — 查看使用者回饋（<code>/inbox</code> 相同）\n"
            "• <code>/redeem PF-XXXXXX</code> — 兌換測試碼（7 天全功能）\n"
            "• <code>/grant &lt;user_id&gt; &lt;days&gt;</code> — 依貢獻授予 N 天全功能\n"
            "• <code>/founder &lt;user_id&gt;</code> — 授予 👑 終身 Founding Member\n"
            "\n💡 測試員的 user_id 在 /codes 兌換紀錄裡直接看得到。"
        )

    markup = make_main_menu(user_id)
    if WEB_APP_URL:
        markup.add(
            types.InlineKeyboardButton(_t(user_id, "btn_open_web"), url=WEB_APP_URL)
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
    tier_names = {"free": _t(user_id, "tier_free"), "pro": _t(user_id, "tier_pro")}
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
    # 使用者從網頁端取得驗證碼後，在此輸入：/bind PF123456
    parts = (message.text or "").split(maxsplit=1)
    code = parts[1].strip().upper() if len(parts) > 1 and parts[1].strip() else ""
    if not code:
        bot.reply_to(message, _t(user_id, "bind_no_code"), parse_mode="HTML")
        return
    if db.link_telegram(code, user_id):
        bot.reply_to(message, _t(user_id, "bind_success"), parse_mode="HTML")
    else:
        bot.reply_to(message, _t(user_id, "bind_invalid"), parse_mode="HTML")

@bot.message_handler(commands=['pro'])
def handle_pro_command(message, override_user_id=None):
    user_id = override_user_id or message.from_user.id
    tier_info = db.get_user_tier(user_id)
    tier = tier_info.get("tier", "free")
    tier_names = {"free": _t(user_id, "tier_free"), "pro": _t(user_id, "tier_pro")}
    tier_badge = tier_names.get(tier, _t(user_id, "tier_free"))
    text = _build_pro_text(user_id, tier_badge)
    # 👑 Founding Member 終身徽章
    if tier_info.get("is_founder"):
        text += _t(user_id, "founder_badge_line")
    elif tier_info.get("tier_expires_at") and tier != "free":
        text += f"\n⏳ Beta full access until <b>{str(tier_info['tier_expires_at'])[:10]}</b>\n"
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
    _, msg = _try_follow_author(user_id, author_name)
    bot.reply_to(message, msg, parse_mode="HTML")

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

# ===================== Beta 測試碼系統 =====================
@bot.message_handler(commands=['gencode'])
def handle_gencode(message):
    user_id = message.from_user.id
    if not _is_admin(user_id):
        bot.reply_to(message, _t(user_id, "promo_admin_only"))
        return
    note = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else "-"
    info = db.create_promo_code(note)
    bot.reply_to(message, _t(user_id, "promo_generated", code=info["code"], note=info["note"]))

@bot.message_handler(commands=['codes'])
def handle_codes(message):
    user_id = message.from_user.id
    if not _is_admin(user_id):
        bot.reply_to(message, _t(user_id, "promo_admin_only"))
        return
    codes = db.list_promo_codes()
    if not codes:
        bot.reply_to(message, _t(user_id, "codes_empty"))
        return
    used = sum(1 for c in codes if c["status"] == "used")
    expired = sum(1 for c in codes if c["status"] == "expired")
    unused = len(codes) - used - expired
    lines = [_t(user_id, "codes_header", used=used, unused=unused, expired=expired)]
    from datetime import datetime
    now = datetime.utcnow()
    for c in codes[:20]:
        status_icon = {"used": "✅", "expired": "⏰"}.get(c["status"], "🟡")
        line = f"{status_icon} <code>{c['code']}</code>"
        if c["note"] and c["note"] != "-":
            line += f"（{c['note']}）"
        if c["status"] == "used":
            line += f" → <code>{c['redeemed_by']}</code>"
        elif c["status"] == "unused":
            try:
                remain = datetime.fromisoformat(c["redeem_deadline"]) - now
                hrs = max(0, int(remain.total_seconds() // 3600))
                line += f" ⏳ {hrs}h"
            except (ValueError, TypeError):
                pass
        lines.append(line)
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=['grant'])
def handle_grant(message):
    """管理員手動授予全功能 N 天：/grant <user_id> <days>"""
    user_id = message.from_user.id
    if not _is_admin(user_id):
        bot.reply_to(message, _t(user_id, "promo_admin_only"))
        return
    parts = message.text.split()
    if len(parts) < 3 or not parts[1].lstrip('@').isdigit() or not parts[2].isdigit():
        bot.reply_to(message, "Usage: /grant <user_id> <days>  (e.g. /grant 123456789 30)")
        return
    target_uid = int(parts[1].lstrip('@'))
    days = max(1, min(3650, int(parts[2])))
    from datetime import datetime, timedelta
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
    db.set_user_tier(target_uid, "pro")
    db.cursor.execute(
        "UPDATE user_tier SET tier_expires_at = ?, expiry_notified = 0 WHERE user_id = ?",
        (expires_at, target_uid)
    )
    db.conn.commit()
    bot.reply_to(message, f"✅ Granted <code>{target_uid}</code> full access for <b>{days} days</b> (until {expires_at[:10]}).")
    try:
        bot.send_message(target_uid, f"🎁 Thank you for your contribution! Your full access has been extended by <b>{days} days</b> (until {expires_at[:10]}).")
    except Exception:
        pass

@bot.message_handler(commands=['founder'])
def handle_founder(message):
    user_id = message.from_user.id
    if not _is_admin(user_id):
        bot.reply_to(message, _t(user_id, "promo_admin_only"))
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().lstrip('@').isdigit():
        bot.reply_to(message, "Usage: /founder 123456789")
        return
    target_uid = int(parts[1].strip().lstrip('@'))
    if db.set_founder(target_uid):
        bot.reply_to(message, _t(user_id, "founder_granted", uid=target_uid))
        try:
            bot.send_message(target_uid, "👑 Congratulations! You've been granted <b>Founding Member</b> status — lifetime full access as a thank-you for your beta feedback!")
        except Exception:
            pass
    else:
        bot.reply_to(message, _t(user_id, "founder_fail"))

@bot.message_handler(commands=['redeem'])
def handle_redeem(message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, _t(user_id, "promo_redeem_usage"))
        return
    ok, result = db.redeem_promo_code(parts[1], user_id)
    if ok:
        expires_display = result[:10] if isinstance(result, str) else str(result)
        bot.reply_to(message, _t(user_id, "promo_redeem_ok", expires=expires_display), parse_mode="HTML")
        bot.send_message(user_id, _t(user_id, "beta_mission"), parse_mode="HTML")
    else:
        bot.reply_to(message, _t(user_id, result))

def _parse_digest_topics(raw: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[,，;；]+", raw or "") if p.strip()]
    if len(parts) == 1 and " " in parts[0] and "," not in raw:
        # "/digest graph neural nets" as one topic is OK; keep as one
        return [parts[0][:80]]
    return [p[:80] for p in parts[:5]]


def _run_digest_for_user(user_id: int, chat_id: int, announce: bool = True) -> bool:
    """Send up to 5 unseen papers across the user's digest topics. Returns True if sent."""
    from datetime import date
    allowed, err_msg = db.check_quota(user_id, "digest")
    if not allowed:
        if announce:
            bot.send_message(chat_id, f"⚠️ {err_msg}")
        return False
    settings = db.get_digest_settings(user_id)
    topics = settings.get("topics") or []
    if not topics:
        if announce:
            bot.send_message(chat_id, _t(user_id, "digest_usage"), parse_mode="HTML")
        return False
    seen_ids = db.get_seen_papers(user_id)
    bias = db.get_user_bias(user_id)
    user_bias = (bias.get("positive", {}), bias.get("negative", {}))
    followed = db.get_followed_authors(user_id)
    filter_mode = db.get_filter_mode(user_id)
    per = max(1, 5 // max(len(topics), 1))
    bundled = []
    used_fp = set()
    for topic in topics[:3]:
        papers = search_engine.list_top_papers(
            user_input=topic,
            seen_ids=seen_ids.union(used_fp),
            user_bias=user_bias,
            followed_authors=followed,
            filter_mode=filter_mode,
            limit=per,
            unseen_only=True,
        )
        for p in papers:
            fp = p.get("fingerprint") or p.get("id")
            if fp in used_fp:
                continue
            used_fp.add(fp)
            bundled.append(p)
            if len(bundled) >= 5:
                break
        if len(bundled) >= 5:
            break
    if not bundled:
        if announce:
            bot.send_message(chat_id, _t(user_id, "digest_empty"))
        return False
    topic_label = " · ".join(topics[:3])
    bot.send_message(chat_id, _t(user_id, "digest_header", topics=topic_label), parse_mode="HTML")
    lang = _get_lang(user_id)
    for p in bundled:
        snippet = (p.get("summary") or "")[:280]
        _send_paper_card(
            chat_id=chat_id,
            user_id=user_id,
            title=p.get("title") or "",
            ai_summary=snippet,
            link=p.get("link") or "",
            paper_id=str(p.get("id") or p.get("fingerprint") or "p"),
            already_seen=False,
            authors=p.get("authors") or [],
            raw_summary=p.get("summary") or "",
            year=p.get("year") or "",
            source=p.get("source") or "",
            is_open_access=bool(p.get("is_open_access")),
            fingerprint=p.get("fingerprint") or "",
            lang=lang,
            venue_name=p.get("venue_name") or "",
            tier=p.get("tier"),
            is_preprint=bool(p.get("is_preprint")),
            citations=p.get("citations") or 0,
        )
    db.increment_usage(user_id, "digest")
    db.mark_digest_sent(user_id, date.today().isoformat())
    db.log_activity(user_id, "digest", paper_title=topic_label, details=f"{len(bundled)} papers")
    return True


def _maybe_lazy_digest(message):
    """If Pro user has digest on and hasn't received one today, send when they next talk."""
    try:
        from datetime import date
        user_id = message.from_user.id
        tier = db.get_user_tier(user_id).get("tier", "free")
        if tier == "free":
            return
        settings = db.get_digest_settings(user_id)
        if not settings.get("is_active") or not settings.get("topics"):
            return
        today = date.today().isoformat()
        if settings.get("last_digest_on") == today:
            return
        _run_digest_for_user(user_id, message.chat.id, announce=False)
    except Exception as e:
        print(f"lazy digest skip: {e}", file=sys.stderr)


@bot.message_handler(commands=['digest'])
def handle_digest(message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=1)
    arg = parts[1].strip() if len(parts) > 1 else ""
    if arg.lower() in ("off", "stop", "關閉", "关闭", "オフ"):
        db.set_digest_settings(user_id, is_active=0)
        bot.reply_to(message, _t(user_id, "digest_off"))
        return
    if arg:
        topics = _parse_digest_topics(arg)
        db.set_digest_settings(user_id, topics=topics, is_active=1, frequency="daily", max_papers=5)
        bot.reply_to(message, _t(user_id, "digest_on", topics=" · ".join(topics)), parse_mode="HTML")
    _run_digest_for_user(user_id, message.chat.id, announce=True)


@bot.message_handler(commands=['feedback'])
def handle_feedback(message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=1)
    body = parts[1].strip() if len(parts) > 1 else ""
    if not body:
        bot.reply_to(message, _t(user_id, "feedback_usage"), parse_mode="HTML")
        return
    db.add_feedback(user_id, body)
    bot.reply_to(message, _t(user_id, "feedback_ok"))


@bot.message_handler(commands=['feedbacks', 'inbox'])
def handle_feedbacks(message):
    user_id = message.from_user.id
    if not _is_admin(user_id):
        bot.reply_to(message, _t(user_id, "promo_admin_only"))
        return
    rows = db.list_feedback(limit=15)
    if not rows:
        bot.reply_to(message, _t(user_id, "feedbacks_empty"))
        return
    lines = [_t(user_id, "feedbacks_header", n=len(rows))]
    for row in rows:
        raw_ts = str(row.get("created_at") or "")
        date_str = raw_ts.replace("T", " ")[:16] if raw_ts else "-"
        uid = row.get("user_id")
        body = (row.get("body") or "").replace("\n", " ").strip()
        if len(body) > 200:
            body = body[:197] + "..."
        lines.append(f"{html.escape(date_str)}  <code>{uid}</code>\n{html.escape(body)}")
    bot.reply_to(message, "\n\n".join(lines), parse_mode="HTML")


@bot.message_handler(commands=['waitlist'])
def handle_waitlist(message):
    user_id = message.from_user.id
    if db.is_on_waitlist(user_id):
        bot.reply_to(message, _t(user_id, "waitlist_already"))
        return
    db.join_waitlist(user_id)
    bot.reply_to(message, _t(user_id, "waitlist_ok"))

def _check_trial_reminder(message):
    """到期前 24 小時自動提醒填回饋表單（每次互動時惰性檢查）"""
    try:
        user_id = message.from_user.id
        for trial in db.get_expiring_trials(within_hours=24):
            if trial["user_id"] != user_id:
                continue
            expires_display = (trial.get("tier_expires_at") or "")[:10]
            bot.send_message(user_id, _t(user_id, "trial_expiring", expires=expires_display))
            db.mark_expiry_notified(user_id)
    except Exception:
        pass

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
def _build_card_text(user_id, title, ai_summary, authors, year, source, is_open_access, citations, venue_name, already_seen, link):
    authors_str = ", ".join(authors[:3]) if authors else "Unknown"
    if len(authors) > 3:
        authors_str += " " + _t(user_id, "paper_et_al", count=len(authors))
    seen_badge = _t(user_id, "paper_seen_badge") if already_seen else ""
    oa_badge = "🟢 OA" if is_open_access else ""
    cred_badge = ""
    if academic_tiers_imported:
        emoji, label = academic_tiers.credibility_badge(venue_name, source)
        cred_badge = f"{emoji} {label}"
    citation_text = f" | 📑 {citations} {_t(user_id, 'card_citations')}" if citations else ""
    return (
        f"📄 <b>{title}</b> {seen_badge}\n\n"
        f"👥 {authors_str}\n"
        f"{year} | 🗂 {source}{citation_text} {oa_badge}\n"
        f"{('🏅 ' + cred_badge + '\n') if cred_badge else ''}"
        f"{_t(user_id, 'paper_ai_summary', text=ai_summary)}\n\n"
        f"🔗 <a href='{link}'>{_t(user_id, 'read_paper')}</a>\n"
        f"<i>⚠️ {_t(user_id, 'card_disclaimer')}</i>"
    )


def _build_card_markup(user_id, fingerprint, paper_id, link, is_open_access):
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
    return markup


def _send_paper_card(chat_id, user_id, title, ai_summary, link, paper_id, already_seen, authors, raw_summary, year, source, is_open_access, fingerprint, lang, venue_name="", tier=None, is_preprint=False, citations=0):
    text = _build_card_text(user_id, title, ai_summary, authors, year, source, is_open_access, citations, venue_name, already_seen, link)
    markup = _build_card_markup(user_id, fingerprint, paper_id, link, is_open_access)
    msg = bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)
    _pending_papers[paper_id[:40]] = {
        "title": title, "summary": raw_summary, "link": link,
        "authors": authors, "year": year, "source": source,
        "fingerprint": fingerprint, "id": paper_id,
        "venue_name": venue_name, "tier": tier, "is_preprint": is_preprint,
        "citations": citations,
    }
    return msg

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
            user_id=user_id,
            generate_summary=False
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
        # Send card immediately (no AI summary yet), then fill summary in to feel faster
        msg = _send_paper_card(
            chat_id=message.chat.id,
            user_id=user_id,
            title=title,
            ai_summary=_t(user_id, "card_summary_generating"),
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
        try:
            real_summary = search_engine.generate_ai_summary(raw_summary, user_id=user_id)
            if real_summary:
                if fingerprint:
                    db.set_cached_ai(fingerprint, summary=real_summary)
                text = _build_card_text(user_id, title, real_summary, authors, year, source, is_open_access, citations, venue_name, already_seen, link)
                markup = _build_card_markup(user_id, fingerprint, paper_id, link, is_open_access)
                bot.edit_message_text(text, chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=markup, disable_web_page_preview=True, parse_mode="HTML")
        except Exception:
            pass
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

    # Beta 試用到期前提醒（惰性檢查，不打擾正常流程）
    _check_trial_reminder(message)
    _maybe_lazy_digest(message)

    # 對話模式優先 - 非指令訊息自動進入跨文獻問答
    if _chat_mode_users.get(user_id) and not text.startswith('/'):
        return _process_chat_query(message, text)

    # 未知指令防護：以 / 開頭但無對應功能時，回覆指令不存在（不誤觸發論文搜尋）
    if text.startswith('/'):
        cmd = text.split()[0].split('@')[0]
        bot.reply_to(message, _t(user_id, "unknown_command", cmd=cmd))
        return

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
                _, msg = _try_follow_author(user_id, author_name)
                bot.reply_to(message, msg, parse_mode="HTML")
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
        try:
            db.log_activity(user_id, "seen", paper_id=paper_id, paper_title=title_display[:200])
        except Exception:
            pass
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
        try:
            db.log_activity(user_id, "skip", paper_id=paper_id, paper_title=title_display[:200])
        except Exception:
            pass
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
        bot.answer_callback_query(call.id, _t(user_id, "archive_archiving"))
        bibtex_str = paper.get("bibtex", "") or search_engine.generate_bibtex_str(
            title=paper.get("title", ""),
            authors=paper.get("authors", []),
            year=paper.get("year", ""),
            link=paper.get("link", ""),
            source=paper.get("source", "")
        )
        if bibtex_str:
            paper["bibtex"] = bibtex_str
        paper["category"] = folder_name
        if db.add_paper_to_library(user_id, paper) is None:
            limit = db.get_user_tier(user_id).get("library_limit", 80)
            bot.send_message(call.message.chat.id, _t(user_id, "library_full", limit=limit), parse_mode="HTML")
            return

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
    message.text.startswith('/gap'),
    message.text.startswith('/export'), message.text.startswith('/mode'),
    message.text.startswith('/lang'), message.text.startswith('/reports'),
    message.text.startswith('/drive'), message.text.startswith('/web'),
    message.text.startswith('/folders'), message.text.startswith('/myfolders'),
    message.text.startswith('/categories'), message.text.startswith('/cats'),
    message.text.startswith('/gencode'), message.text.startswith('/codes'),
    message.text.startswith('/founder'), message.text.startswith('/redeem'),
    message.text.startswith('/grant'), message.text.startswith('/digest'),
    message.text.startswith('/feedbacks'), message.text.startswith('/inbox'),
    message.text.startswith('/feedback'), message.text.startswith('/waitlist'),
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
