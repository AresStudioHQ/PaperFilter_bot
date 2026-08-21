import sqlite3
import json
import os
import sys

try:
    import libsql
except ImportError:
    libsql = None

class Database:
    def __init__(self, db_path=None):
        turso_url = os.getenv("TURSO_DATABASE_URL")
        turso_token = os.getenv("TURSO_AUTH_TOKEN")
        if turso_url and turso_token:
            # 正式環境：連線到 Turso 雲端資料庫（資料持久化，不會因重新部署而消失）
            if libsql is None:
                raise RuntimeError(
                    "偵測到 TURSO_DATABASE_URL / TURSO_AUTH_TOKEN，"
                    "但尚未安裝 libsql 套件，請先執行：pip install libsql"
                )
            self.db_path = None
            self.conn = libsql.connect(database=turso_url, auth_token=turso_token)
            print("✅ Database: 已連線至 Turso 雲端資料庫", file=sys.stderr)
        else:
            # 本機開發用：沒有設定 Turso 環境變數時，退回本機 SQLite 檔案
            if db_path is None:
                data_dir = os.getenv("DATA_DIR", ".")
                db_path = os.path.join(data_dir, "users_data.db")
            self.db_path = db_path
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            print(f"⚠️ Database: 未偵測到 Turso 環境變數，改用本機 SQLite：{db_path}", file=sys.stderr)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # 1. 用戶表 (新增 filter_mode 與 user_lang)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                gdrive_token TEXT,
                positive_keywords TEXT DEFAULT '{}',
                negative_keywords TEXT DEFAULT '{}',
                filter_mode TEXT DEFAULT 'smart',
                user_lang TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 遷移檢查
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN filter_mode TEXT DEFAULT 'smart'")
            self.conn.commit()
        except Exception:
            pass
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN user_lang TEXT DEFAULT NULL")
            self.conn.commit()
        except Exception:
            pass

        # 2. 已讀論文表 (支援標題指紋去重)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_papers (
                user_id INTEGER,
                paper_id TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, paper_id)
            )
        ''')

        # 3. 分類資料夾表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_categories (
                user_id INTEGER,
                category_name TEXT,
                PRIMARY KEY (user_id, category_name)
            )
        ''')

        # 4. 學者關注追蹤表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS author_tracking (
                user_id INTEGER,
                author_name TEXT,
                PRIMARY KEY (user_id, author_name)
            )
        ''')

        # 5. 推播排程設定表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                user_id INTEGER PRIMARY KEY,
                is_active INTEGER DEFAULT 1,
                push_time TEXT DEFAULT '08:30',
                topics TEXT DEFAULT '[]'
            )
        ''')

        # 6. AI 摘要快取表 (大幅降低重複請求的 API 成本)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_cache (
                cache_key TEXT PRIMARY KEY,
                summary TEXT,
                deep_report TEXT,
                bibtex TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 7. 用戶訂閱方案 (free / basic / standard / premium / ultra / lab)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tier (
                user_id INTEGER PRIMARY KEY,
                tier TEXT DEFAULT 'free',
                daily_search_limit INTEGER DEFAULT 500,
                daily_deep_limit INTEGER DEFAULT 50,
                daily_litreview_limit INTEGER DEFAULT 20,
                daily_gap_analysis_limit INTEGER DEFAULT 20,
                daily_export_limit INTEGER DEFAULT 999999,
                daily_digest_limit INTEGER DEFAULT 7,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Beta 測試碼系統：一人一碼，72h 兌換期限，兌換後 7 天全功能
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                redeem_deadline TIMESTAMP,
                redeemed_by INTEGER,
                redeemed_at TIMESTAMP,
                status TEXT DEFAULT 'unused'
            )
        ''')

        # 舊庫升級：user_tier 加入到期/創始成員欄位
        for col_def in ("tier_expires_at TEXT", "is_founder INTEGER DEFAULT 0",
                        "expiry_notified INTEGER DEFAULT 0"):
            try:
                self.cursor.execute(f"ALTER TABLE user_tier ADD COLUMN {col_def}")
            except Exception:
                pass

        # 7.5 Telegram ↔ Web 綁定關聯表（驗證碼僅為暫時憑證，資料跟 telegram_user_id 走）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS telegram_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_code TEXT UNIQUE,
                web_uid TEXT,
                telegram_user_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')

        # 8. 用戶論文收藏庫 (用於批量操作：文獻綜述、缺口分析、匯出、RAG 跨文獻問答)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_paper_library (
                user_id INTEGER,
                paper_id TEXT,
                title TEXT,
                authors TEXT,
                year TEXT,
                source TEXT,
                link TEXT,
                abstract TEXT,
                fingerprint TEXT,
                bibtex TEXT,
                category TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, paper_id)
            )
        ''')

        # 9. 自動生成的文獻綜述
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS literature_reviews (
                review_id TEXT PRIMARY KEY,
                user_id INTEGER,
                topic TEXT,
                papers_json TEXT,
                review_text TEXT,
                gap_analysis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 10. 研究缺口分析快取
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS research_gaps (
                gap_id TEXT PRIMARY KEY,
                user_id INTEGER,
                topic TEXT,
                papers_json TEXT,
                gaps_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 11. 趨勢分析快取
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trend_analysis (
                cache_key TEXT PRIMARY KEY,
                topic TEXT,
                trend_data_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 12. 匯出歷史記錄
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS export_history (
                export_id TEXT PRIMARY KEY,
                user_id INTEGER,
                format TEXT,
                paper_count INTEGER,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 13. 每日/每週摘要設定
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS digest_settings (
                user_id INTEGER PRIMARY KEY,
                frequency TEXT DEFAULT 'weekly',
                push_time TEXT DEFAULT '08:00',
                topics_json TEXT DEFAULT '[]',
                max_papers INTEGER DEFAULT 10,
                include_deep INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0
            )
        ''')

        # 14. 使用量追蹤 (配額控制)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_tracking (
                user_id INTEGER,
                date TEXT,
                searches INTEGER DEFAULT 0,
                deep_reads INTEGER DEFAULT 0,
                lit_reviews INTEGER DEFAULT 0,
                gap_analyses INTEGER DEFAULT 0,
                exports INTEGER DEFAULT 0,
                digests INTEGER DEFAULT 0,
                chats INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )
        ''')

        # 15. Drive 歸檔紀錄 (控制每月 Drive 歸檔額度)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS drive_archive_log (
                user_id INTEGER,
                date TEXT,
                PRIMARY KEY (user_id, date)
            )
        ''')
        self.conn.commit()

    # --- 1. 用戶與 Token ---
    def get_token(self, user_id: int) -> str | None:
        self.cursor.execute("SELECT gdrive_token FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def save_token(self, user_id: int, token_json: str):
        self.cursor.execute('''
            INSERT INTO users (user_id, gdrive_token)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET gdrive_token = ?
        ''', (user_id, token_json, token_json))
        self.conn.commit()

    def remove_token(self, user_id: int):
        self.cursor.execute("UPDATE users SET gdrive_token = NULL WHERE user_id = ?", (user_id,))
        self.conn.commit()

    # --- 1.1 語言偏好設定 (en | zh_hant | zh_hans | ja) ---
    def get_user_lang(self, user_id: int) -> str | None:
        self.cursor.execute("SELECT user_lang FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row and row[0] else None

    def set_user_lang(self, user_id: int, lang_code: str):
        self.cursor.execute('''
            INSERT INTO users (user_id, user_lang)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET user_lang = ?
        ''', (user_id, lang_code, lang_code))
        self.conn.commit()

    # --- 1.2 檢索模式設定 (smart: 智能平衡 | top_tier: 頂刊權威優先 | free_only: 開源免費優先) ---
    def get_filter_mode(self, user_id: int) -> str:
        self.cursor.execute("SELECT filter_mode FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row and row[0] else 'smart'

    def set_filter_mode(self, user_id: int, mode: str):
        self.cursor.execute('''
            INSERT INTO users (user_id, filter_mode)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET filter_mode = ?
        ''', (user_id, mode, mode))
        self.conn.commit()

    # --- 2. 偏好與已讀管理 ---
    def get_seen_papers(self, user_id: int) -> set:
        self.cursor.execute("SELECT paper_id FROM seen_papers WHERE user_id = ?", (user_id,))
        return set(r[0] for r in self.cursor.fetchall())

    def add_seen_paper(self, user_id: int, paper_id: str):
        self.cursor.execute("INSERT OR IGNORE INTO seen_papers (user_id, paper_id) VALUES (?, ?)", (user_id, paper_id))
        self.conn.commit()

    def get_user_bias(self, user_id: int) -> dict:
        self.cursor.execute("SELECT positive_keywords, negative_keywords FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if not row:
            return {"positive": {}, "negative": {}}
        try:
            pos = json.loads(row[0]) if row[0] else {}
        except Exception:
            pos = {}
        try:
            neg = json.loads(row[1]) if row[1] else {}
        except Exception:
            neg = {}
        return {"positive": pos, "negative": neg}

    def update_user_bias(self, user_id: int, keywords: list[str], is_positive: bool = True):
        current_bias = self.get_user_bias(user_id)
        target_dict = current_bias["positive"] if is_positive else current_bias["negative"]
        for kw in keywords:
            kw_clean = kw.lower().strip()
            if kw_clean:
                target_dict[kw_clean] = target_dict.get(kw_clean, 0) + 1
        pos_str = json.dumps(current_bias["positive"], ensure_ascii=False)
        neg_str = json.dumps(current_bias["negative"], ensure_ascii=False)
        self.cursor.execute('''
            INSERT INTO users (user_id, positive_keywords, negative_keywords)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET positive_keywords = ?, negative_keywords = ?
        ''', (user_id, pos_str, neg_str, pos_str, neg_str))
        self.conn.commit()

    # --- 3. 自訂分類資料夾管理 ---
    def get_user_categories(self, user_id: int) -> list[str]:
        self.cursor.execute("SELECT category_name FROM user_categories WHERE user_id = ?", (user_id,))
        rows = self.cursor.fetchall()
        return [r[0] for r in rows]

    def add_user_category(self, user_id: int, category_name: str):
        clean_name = category_name.strip()
        if clean_name:
            self.cursor.execute("INSERT OR IGNORE INTO user_categories (user_id, category_name) VALUES (?, ?)", (user_id, clean_name))
            self.conn.commit()

    def rename_user_category(self, user_id: int, old_name: str, new_name: str):
        self.cursor.execute("UPDATE user_categories SET category_name = ? WHERE user_id = ? AND category_name = ?", (new_name.strip(), user_id, old_name.strip()))
        self.conn.commit()

    def delete_user_category(self, user_id: int, category_name: str):
        self.cursor.execute("DELETE FROM user_categories WHERE user_id = ? AND category_name = ?", (user_id, category_name.strip()))
        self.conn.commit()

    # --- 4. 學者關注追蹤管理 ---
    def add_followed_author(self, user_id: int, author_name: str):
        clean_name = author_name.strip()
        if clean_name:
            self.cursor.execute("INSERT OR IGNORE INTO author_tracking (user_id, author_name) VALUES (?, ?)", (user_id, clean_name))
            self.conn.commit()

    def remove_followed_author(self, user_id: int, author_name: str) -> bool:
        clean_name = author_name.strip()
        self.cursor.execute("DELETE FROM author_tracking WHERE user_id = ? AND author_name = ?", (user_id, clean_name))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_followed_authors(self, user_id: int) -> list[str]:
        self.cursor.execute("SELECT author_name FROM author_tracking WHERE user_id = ?", (user_id,))
        rows = self.cursor.fetchall()
        return [r[0] for r in rows]

    # --- 5. AI 快取管理 (省 API 費用) ---
    def get_cached_ai(self, cache_key: str):
        self.cursor.execute("SELECT summary, deep_report, bibtex FROM ai_cache WHERE cache_key = ?", (cache_key,))
        return self.cursor.fetchone()

    def set_cached_ai(self, cache_key: str, summary: str = None, deep_report: str = None, bibtex: str = None):
        self.cursor.execute('''
            INSERT INTO ai_cache (cache_key, summary, deep_report, bibtex)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                summary = COALESCE(?, summary),
                deep_report = COALESCE(?, deep_report),
                bibtex = COALESCE(?, bibtex)
        ''', (cache_key, summary, deep_report, bibtex, summary, deep_report, bibtex))
        self.conn.commit()

    # --- 6. 用戶訂閱方案與配額管理 ---
    # === 5 級訂閱方案定義 ===
    TIER_DEFS = {
        "free": {
            "daily_search_limit": 20, "daily_deep_limit": 5,
            "daily_litreview_limit": 3, "daily_gap_analysis_limit": 3,
            "daily_export_limit": 10, "daily_digest_limit": 2,
            "daily_chat_limit": 3,
            "drive_monthly_limit": 20,
            "follow_limit": 3, "category_limit": 5,
        },
        "basic": {
            "daily_search_limit": 50, "daily_deep_limit": 15,
            "daily_litreview_limit": 10, "daily_gap_analysis_limit": 10,
            "daily_export_limit": 25, "daily_digest_limit": 5,
            "daily_chat_limit": 10,
            "drive_monthly_limit": 50,
            "follow_limit": 10, "category_limit": 20,
        },
        "standard": {
            "daily_search_limit": 150, "daily_deep_limit": 50,
            "daily_litreview_limit": 25, "daily_gap_analysis_limit": 25,
            "daily_export_limit": 80, "daily_digest_limit": 10,
            "daily_chat_limit": 25,
            "drive_monthly_limit": 100,
            "follow_limit": 30, "category_limit": 999999,
        },
        "premium": {
            "daily_search_limit": 300, "daily_deep_limit": 150,
            "daily_litreview_limit": 100, "daily_gap_analysis_limit": 100,
            "daily_export_limit": 250, "daily_digest_limit": 20,
            "daily_chat_limit": 100,
            "drive_monthly_limit": 999999,
            "follow_limit": 999999, "category_limit": 999999,
        },
        "ultra": {
            "daily_search_limit": 500, "daily_deep_limit": 300,
            "daily_litreview_limit": 999999, "daily_gap_analysis_limit": 999999,
            "daily_export_limit": 999999, "daily_digest_limit": 50,
            "daily_chat_limit": 999999,
            "drive_monthly_limit": 999999,
            "follow_limit": 999999, "category_limit": 999999,
        },
        "lab": {
            "daily_search_limit": 999999, "daily_deep_limit": 999999,
            "daily_litreview_limit": 999999, "daily_gap_analysis_limit": 999999,
            "daily_export_limit": 999999, "daily_digest_limit": 999999,
            "daily_chat_limit": 999999,
            "drive_monthly_limit": 999999,
            "follow_limit": 999999, "category_limit": 999999,
        },
    }
    TIER_PRICES = {
        "free": 0, "basic": 150, "standard": 299, "premium": 499, "ultra": 999, "lab": 2999,
    }
    TIER_RANK = {"free": 0, "basic": 1, "standard": 2, "premium": 3, "ultra": 4, "lab": 5}

    def get_user_tier(self, user_id: int) -> dict:
        self.cursor.execute("SELECT tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit, tier_expires_at, is_founder FROM user_tier WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if not row:
            d = self.TIER_DEFS["free"]
            self.cursor.execute('''
                INSERT INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit)
                VALUES (?, 'free', ?, ?, ?, ?, ?, ?)
            ''', (user_id, d["daily_search_limit"], d["daily_deep_limit"], d["daily_litreview_limit"], d["daily_gap_analysis_limit"], d["daily_export_limit"], d["daily_digest_limit"]))
            self.conn.commit()
            return {"tier": "free", **d}
        tier = row[0]
        tier_expires_at = row[7]
        is_founder = bool(row[8])
        # 到期自動降級（Founder 終身不受影響）
        if tier_expires_at and not is_founder and tier != "free":
            from datetime import datetime
            try:
                if datetime.utcnow() > datetime.fromisoformat(tier_expires_at):
                    self.set_user_tier(user_id, "free")
                    return {"tier": "free", **self.TIER_DEFS["free"]}
            except (ValueError, TypeError):
                pass
        # Serve live TIER_DEFS limits for every tier so plan changes apply instantly
        d = self.TIER_DEFS.get(tier, self.TIER_DEFS["free"])
        return {"tier": tier, "tier_expires_at": tier_expires_at, "is_founder": is_founder, **d}

    def set_user_tier(self, user_id: int, tier: str, limits: dict = None):
        d = limits or self.TIER_DEFS.get(tier, self.TIER_DEFS["free"])
        self.cursor.execute('''
            INSERT INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET tier = ?, daily_search_limit = ?, daily_deep_limit = ?, daily_litreview_limit = ?, daily_gap_analysis_limit = ?, daily_export_limit = ?, daily_digest_limit = ?, updated_at = CURRENT_TIMESTAMP
        ''', (user_id, tier, d["daily_search_limit"], d["daily_deep_limit"], d["daily_litreview_limit"], d["daily_gap_analysis_limit"], d["daily_export_limit"], d["daily_digest_limit"], tier, d["daily_search_limit"], d["daily_deep_limit"], d["daily_litreview_limit"], d["daily_gap_analysis_limit"], d["daily_export_limit"], d["daily_digest_limit"]))
        self.conn.commit()

    # --- Beta 測試碼系統 ---
    PROMO_REDEEM_HOURS = 72    # 生成後多久內要兌換
    PROMO_ACCESS_DAYS = 7      # 兌換後全功能天數

    def create_promo_code(self, note: str = "") -> dict:
        import secrets as _secrets
        from datetime import datetime, timedelta
        code = "PF-" + _secrets.token_hex(3).upper()
        deadline = (datetime.utcnow() + timedelta(hours=self.PROMO_REDEEM_HOURS)).isoformat()
        self.cursor.execute(
            "INSERT INTO promo_codes (code, note, redeem_deadline) VALUES (?, ?, ?)",
            (code, note, deadline)
        )
        self.conn.commit()
        return {"code": code, "note": note, "redeem_deadline": deadline}

    def redeem_promo_code(self, code: str, user_id: int) -> tuple[bool, str]:
        """兌換測試碼。回傳 (是否成功, 訊息 key / 說明)"""
        from datetime import datetime, timedelta
        code = (code or "").strip().upper()
        self.cursor.execute("SELECT status, redeem_deadline, redeemed_by FROM promo_codes WHERE code = ?", (code,))
        row = self.cursor.fetchone()
        if not row:
            return False, "promo_invalid"
        status, deadline, redeemed_by = row[0], row[1], row[2]
        if status == "used":
            return False, "promo_already_used"
        try:
            if datetime.utcnow() > datetime.fromisoformat(deadline):
                self.cursor.execute("UPDATE promo_codes SET status = 'expired' WHERE code = ?", (code,))
                self.conn.commit()
                return False, "promo_expired"
        except (ValueError, TypeError):
            return False, "promo_invalid"
        # 升級為 lab 全功能 + 寫入到期日
        expires_at = (datetime.utcnow() + timedelta(days=self.PROMO_ACCESS_DAYS)).isoformat()
        self.set_user_tier(user_id, "lab")
        self.cursor.execute(
            "UPDATE user_tier SET tier_expires_at = ?, expiry_notified = 0 WHERE user_id = ?",
            (expires_at, user_id)
        )
        self.cursor.execute(
            "UPDATE promo_codes SET status = 'used', redeemed_by = ?, redeemed_at = CURRENT_TIMESTAMP WHERE code = ?",
            (user_id, code)
        )
        self.conn.commit()
        return True, expires_at

    def list_promo_codes(self) -> list:
        self.cursor.execute("SELECT code, note, created_at, redeem_deadline, redeemed_by, status FROM promo_codes ORDER BY created_at DESC")
        rows = self.cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "code": r[0], "note": r[1], "created_at": r[2],
                "redeem_deadline": r[3], "redeemed_by": r[4], "status": r[5]
            })
        return result

    def get_expiring_trials(self, within_hours: int = 24) -> list:
        """取得即將到期、尚未提醒的試用者"""
        from datetime import datetime, timedelta
        horizon = (datetime.utcnow() + timedelta(hours=within_hours)).isoformat()
        now = datetime.utcnow().isoformat()
        self.cursor.execute(
            "SELECT user_id, tier_expires_at FROM user_tier WHERE tier != 'free' AND is_founder = 0 AND expiry_notified = 0 AND tier_expires_at IS NOT NULL AND tier_expires_at > ? AND tier_expires_at <= ?",
            (now, horizon)
        )
        return [{"user_id": r[0], "tier_expires_at": r[1]} for r in self.cursor.fetchall()]

    def mark_expiry_notified(self, user_id: int):
        self.cursor.execute("UPDATE user_tier SET expiry_notified = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def set_founder(self, user_id: int) -> bool:
        self.cursor.execute(
            "UPDATE user_tier SET is_founder = 1, tier = CASE WHEN tier = 'free' THEN 'lab' ELSE tier END, tier_expires_at = NULL, expiry_notified = 0 WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def is_founder(self, user_id: int) -> bool:
        self.cursor.execute("SELECT is_founder FROM user_tier WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return bool(row and row[0])

    def check_drive_quota(self, user_id: int) -> tuple[bool, str]:
        """檢查 Drive 歸檔額度，回傳 (是否允許, 訊息)"""
        from datetime import date
        today = date.today().isoformat()
        tier_info = self.get_user_tier(user_id)
        tier = tier_info.get("tier", "free")
        drive_limit = self.TIER_DEFS.get(tier, self.TIER_DEFS["free"])["drive_monthly_limit"]
        if drive_limit >= 999999:
            return True, ""
        self.cursor.execute("SELECT COUNT(*) FROM drive_archive_log WHERE user_id = ? AND date = ?", (user_id, today))
        row = self.cursor.fetchone()
        used = row[0] if row else 0
        if used >= drive_limit:
            return False, f"今日 Drive 歸檔額度已用盡 ({used}/{drive_limit})，明日 00:00 重置或升級方案。"
        return True, ""

    def log_drive_archive(self, user_id: int):
        """記錄一次 Drive 歸檔"""
        from datetime import date
        today = date.today().isoformat()
        self.cursor.execute("INSERT INTO drive_archive_log (user_id, date) VALUES (?, ?)", (user_id, today))
        self.conn.commit()

    def check_quota(self, user_id: int, action: str) -> tuple[bool, str]:
        """檢查用戶是否還有配額。回傳 (是否允許, 錯誤訊息)"""
        from datetime import date
        today = date.today().isoformat()
        tier_info = self.get_user_tier(user_id)
        limit_map = {
            "search": ("searches", tier_info["daily_search_limit"]),
            "deep": ("deep_reads", tier_info["daily_deep_limit"]),
            "litreview": ("lit_reviews", tier_info["daily_litreview_limit"]),
            "gap_analysis": ("gap_analyses", tier_info["daily_gap_analysis_limit"]),
            "export": ("exports", tier_info["daily_export_limit"]),
            "digest": ("digests", tier_info["daily_digest_limit"]),
            "chat": ("chats", self.TIER_DEFS.get(tier_info["tier"], self.TIER_DEFS["free"])["daily_chat_limit"]),
        }
        if action not in limit_map:
            return True, ""
        col, limit = limit_map[action]
        if limit <= 0:
            return False, f"您的方案 ({tier_info['tier']}) 不支援此功能，請升級訂閱。"
        self.cursor.execute(f"SELECT {col} FROM usage_tracking WHERE user_id = ? AND date = ?", (user_id, today))
        row = self.cursor.fetchone()
        used = row[0] if row else 0
        if used >= limit:
            return False, f"今日 {action} 配額已用盡 ({used}/{limit})，請明天再試或升級方案。"
        return True, ""

    def increment_usage(self, user_id: int, action: str):
        from datetime import date
        today = date.today().isoformat()
        col_map = {
            "search": "searches",
            "deep": "deep_reads",
            "litreview": "lit_reviews",
            "gap_analysis": "gap_analyses",
            "export": "exports",
            "digest": "digests",
            "chat": "chats",
        }
        if action not in col_map:
            return
        col = col_map[action]
        self.cursor.execute(f'''
            INSERT INTO usage_tracking (user_id, date, {col})
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, date) DO UPDATE SET {col} = {col} + 1
        ''', (user_id, today))
        self.conn.commit()

    # --- 7. 用戶論文收藏庫 ---
    def add_paper_to_library(self, user_id: int, paper: dict):
        import uuid
        paper_id = paper.get("id") or paper.get("fingerprint") or str(uuid.uuid4())[:16]
        authors_json = json.dumps(paper.get("authors", []), ensure_ascii=False)
        self.cursor.execute('''
            INSERT INTO user_paper_library (user_id, paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, paper_id) DO UPDATE SET
                title = ?, authors = ?, year = ?, source = ?, link = ?,
                abstract = ?, fingerprint = ?, bibtex = ?, category = ?
        ''', (user_id, paper_id, paper.get("title", ""), authors_json, paper.get("year", ""), paper.get("source", ""), paper.get("link", ""), paper.get("summary", ""), paper.get("fingerprint", ""), paper.get("bibtex", ""), paper.get("category", "未分類"),
              paper.get("title", ""), authors_json, paper.get("year", ""), paper.get("source", ""), paper.get("link", ""), paper.get("summary", ""), paper.get("fingerprint", ""), paper.get("bibtex", ""), paper.get("category", "未分類")))
        self.conn.commit()
        return paper_id

    def get_user_library(self, user_id: int, category: str = None, limit: int = 100) -> list[dict]:
        if category:
            self.cursor.execute("SELECT paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category FROM user_paper_library WHERE user_id = ? AND category = ? ORDER BY added_at DESC LIMIT ?", (user_id, category, limit))
        else:
            self.cursor.execute("SELECT paper_id, title, authors, year, source, link, abstract, fingerprint, bibtex, category FROM user_paper_library WHERE user_id = ? ORDER BY added_at DESC LIMIT ?", (user_id, limit))
        rows = self.cursor.fetchall()
        papers = []
        for r in rows:
            papers.append({
                "id": r[0], "title": r[1], "authors": json.loads(r[2]) if r[2] else [], "year": r[3], "source": r[4], "link": r[5], "summary": r[6], "fingerprint": r[7], "bibtex": r[8], "category": r[9]
            })
        return papers

    def get_library_stats(self, user_id: int) -> dict:
        self.cursor.execute("SELECT COUNT(*), COUNT(DISTINCT category) FROM user_paper_library WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        total, categories = row if row else (0, 0)
        self.cursor.execute("SELECT category, COUNT(*) FROM user_paper_library WHERE user_id = ? GROUP BY category", (user_id,))
        cat_counts = dict(self.cursor.fetchall())
        return {"total_papers": total, "categories": categories, "by_category": cat_counts}

    def remove_paper_from_library(self, user_id: int, paper_id: str) -> bool:
        self.cursor.execute("DELETE FROM user_paper_library WHERE user_id = ? AND paper_id = ?", (user_id, paper_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def clear_library(self, user_id: int):
        self.cursor.execute("DELETE FROM user_paper_library WHERE user_id = ?", (user_id,))
        self.conn.commit()

    # --- 8. 文獻綜述管理 ---
    def save_literature_review(self, user_id: int, topic: str, papers: list[dict], review_text: str, gap_analysis: str = "") -> str:
        import uuid
        review_id = str(uuid.uuid4())[:16]
        papers_json = json.dumps(papers, ensure_ascii=False)
        self.cursor.execute('''
            INSERT INTO literature_reviews (review_id, user_id, topic, papers_json, review_text, gap_analysis)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (review_id, user_id, topic, papers_json, review_text, gap_analysis))
        self.conn.commit()
        return review_id

    def get_literature_reviews(self, user_id: int, limit: int = 20) -> list[dict]:
        self.cursor.execute("SELECT review_id, topic, papers_json, review_text, gap_analysis, created_at FROM literature_reviews WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
        rows = self.cursor.fetchall()
        reviews = []
        for r in rows:
            reviews.append({"review_id": r[0], "topic": r[1], "papers": json.loads(r[2]) if r[2] else [], "review_text": r[3], "gap_analysis": r[4], "created_at": r[5]})
        return reviews

    # --- 9. 研究缺口分析 ---
    def save_research_gaps(self, user_id: int, topic: str, papers: list[dict], gaps: list[dict]) -> str:
        import uuid
        gap_id = str(uuid.uuid4())[:16]
        papers_json = json.dumps(papers, ensure_ascii=False)
        gaps_json = json.dumps(gaps, ensure_ascii=False)
        self.cursor.execute('''
            INSERT INTO research_gaps (gap_id, user_id, topic, papers_json, gaps_json)
            VALUES (?, ?, ?, ?, ?)
        ''', (gap_id, user_id, topic, papers_json, gaps_json))
        self.conn.commit()
        return gap_id

    def get_research_gaps(self, user_id: int, topic: str = None) -> list[dict]:
        if topic:
            self.cursor.execute("SELECT gap_id, topic, papers_json, gaps_json, created_at FROM research_gaps WHERE user_id = ? AND topic = ? ORDER BY created_at DESC", (user_id, topic))
        else:
            self.cursor.execute("SELECT gap_id, topic, papers_json, gaps_json, created_at FROM research_gaps WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = self.cursor.fetchall()
        gaps = []
        for r in rows:
            gaps.append({"gap_id": r[0], "topic": r[1], "papers": json.loads(r[2]) if r[2] else [], "gaps": json.loads(r[3]) if r[3] else [], "created_at": r[4]})
        return gaps

    # --- 10. 趨勢分析快取 ---
    def get_trend_cache(self, cache_key: str):
        self.cursor.execute("SELECT trend_data_json FROM trend_analysis WHERE cache_key = ?", (cache_key,))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else None

    def set_trend_cache(self, cache_key: str, topic: str, trend_data: dict):
        trend_json = json.dumps(trend_data, ensure_ascii=False)
        self.cursor.execute('''
            INSERT INTO trend_analysis (cache_key, topic, trend_data_json)
            VALUES (?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET trend_data_json = ?
        ''', (cache_key, topic, trend_json, trend_json))
        self.conn.commit()

    # --- 11. 匯出歷史 ---
    def save_export_history(self, user_id: int, format: str, paper_count: int, file_path: str) -> str:
        import uuid
        export_id = str(uuid.uuid4())[:16]
        self.cursor.execute('''
            INSERT INTO export_history (export_id, user_id, format, paper_count, file_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (export_id, user_id, format, paper_count, file_path))
        self.conn.commit()
        return export_id

    def get_export_history(self, user_id: int, limit: int = 20) -> list[dict]:
        self.cursor.execute("SELECT export_id, format, paper_count, file_path, created_at FROM export_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
        rows = self.cursor.fetchall()
        return [{"export_id": r[0], "format": r[1], "paper_count": r[2], "file_path": r[3], "created_at": r[4]} for r in rows]

    def get_user_reports(self, user_id: int) -> list:
        """從資料庫查詢用戶的文獻綜述與分析報告"""
        self.cursor.execute("SELECT review_id, topic, papers_json, review_text, gap_analysis, created_at FROM literature_reviews WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = self.cursor.fetchall()
        reports = []
        for r in rows:
            reports.append({
                'review_id': r[0],
                'topic': r[1],
                'papers_json': r[2],
                'review_text': r[3],
                'gap_analysis': r[4],
                'created_at': r[5]
            })
        return reports

    # --- 13. 網頁大總部同步碼 ---
    # --- 11.5 Telegram ↔ Web 綁定（驗證碼為暫時憑證，資料跟 telegram_user_id 走）---
    def create_bind_code(self, web_uid: str, ttl_minutes: int = 10) -> str:
        """為某個 web session 產生一組唯一、有時效的綁定碼，存入 telegram_links。"""
        import random
        from datetime import datetime, timedelta
        # 先讓同一 web_uid 的舊 pending 碼失效，避免堆積
        self.cursor.execute(
            "UPDATE telegram_links SET status='expired' WHERE web_uid=? AND status='pending'",
            (web_uid,),
        )
        for _ in range(20):
            code = f"PF{random.randint(100000, 999999)}"
            try:
                expires = (datetime.now() + timedelta(minutes=ttl_minutes)).strftime("%Y-%m-%d %H:%M:%S")
                self.cursor.execute(
                    "INSERT INTO telegram_links (link_code, web_uid, status, expires_at) VALUES (?, ?, 'pending', ?)",
                    (code, web_uid, expires),
                )
                self.conn.commit()
                return code
            except Exception:
                # link_code UNIQUE 衝突 → 重試
                continue
        raise RuntimeError("無法產生唯一綁定碼")

    def resolve_bind_code(self, code: str):
        """解析尚未過期、仍 pending 的綁定碼，回傳該筆 row 或 None。"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "SELECT id, link_code, web_uid, telegram_user_id, status, expires_at FROM telegram_links "
            "WHERE link_code=? AND status='pending' AND expires_at > ?",
            (code, now),
        )
        return self.cursor.fetchone()

    def link_telegram(self, code: str, telegram_user_id: int) -> bool:
        """用驗證碼把 telegram_user_id 與 web_uid 綁定。只更新關聯表，絕不動用戶資料表。"""
        row = self.resolve_bind_code(code)
        if not row:
            return False
        web_uid = row[2]
        # 同一 telegram 帳號若已有舊連結，先標為 superseded（資料不刪）
        self.cursor.execute(
            "UPDATE telegram_links SET status='superseded' WHERE telegram_user_id=? AND status='linked'",
            (telegram_user_id,),
        )
        # 啟用這組碼對應的連結
        self.cursor.execute(
            "UPDATE telegram_links SET telegram_user_id=?, status='linked' WHERE link_code=?",
            (telegram_user_id, code),
        )
        self.conn.commit()
        return True

    def get_link_by_telegram(self, telegram_user_id: int):
        self.cursor.execute(
            "SELECT id, link_code, web_uid, telegram_user_id, status FROM telegram_links "
            "WHERE telegram_user_id=? AND status='linked' ORDER BY id DESC LIMIT 1",
            (telegram_user_id,),
        )
        return self.cursor.fetchone()

    def get_link_by_web(self, web_uid: str):
        self.cursor.execute(
            "SELECT id, link_code, web_uid, telegram_user_id, status FROM telegram_links "
            "WHERE web_uid=? AND status='linked' ORDER BY id DESC LIMIT 1",
            (web_uid,),
        )
        return self.cursor.fetchone()

    # --- 12. 摘要設定 ---
    def get_digest_settings(self, user_id: int) -> dict:
        self.cursor.execute("SELECT frequency, push_time, topics_json, max_papers, include_deep, is_active FROM digest_settings WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if not row:
            return {"frequency": "weekly", "push_time": "08:00", "topics": [], "max_papers": 10, "include_deep": 0, "is_active": 0}
        return {"frequency": row[0], "push_time": row[1], "topics": json.loads(row[2]) if row[2] else [], "max_papers": row[3], "include_deep": row[4], "is_active": row[5]}

    def set_digest_settings(self, user_id: int, frequency: str = None, push_time: str = None, topics: list = None, max_papers: int = None, include_deep: int = None, is_active: int = None):
        current = self.get_digest_settings(user_id)
        freq = frequency or current["frequency"]
        pt = push_time or current["push_time"]
        tp = json.dumps(topics, ensure_ascii=False) if topics is not None else json.dumps(current["topics"], ensure_ascii=False)
        mp = max_papers if max_papers is not None else current["max_papers"]
        idp = include_deep if include_deep is not None else current["include_deep"]
        ia = is_active if is_active is not None else current["is_active"]
        self.cursor.execute('''
            INSERT INTO digest_settings (user_id, frequency, push_time, topics_json, max_papers, include_deep, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET frequency = ?, push_time = ?, topics_json = ?, max_papers = ?, include_deep = ?, is_active = ?
        ''', (user_id, freq, pt, tp, mp, idp, ia, freq, pt, tp, mp, idp, ia))
        self.conn.commit()

# 單例實例
db = Database()
