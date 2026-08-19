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

        # 7. 用戶訂閱方案 (free / premium / pro)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_tier (
            user_id INTEGER PRIMARY KEY,
            tier TEXT DEFAULT 'free',
            daily_search_limit INTEGER DEFAULT 20,
            daily_deep_limit INTEGER DEFAULT 3,
            daily_litreview_limit INTEGER DEFAULT 0,
            daily_gap_analysis_limit INTEGER DEFAULT 0,
            daily_export_limit INTEGER DEFAULT 5,
            daily_digest_limit INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # --- 5. AI 快取管理 ---
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
    def get_user_tier(self, user_id: int) -> dict:
        self.cursor.execute("SELECT tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit FROM user_tier WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if not row:
            self.cursor.execute('''
            INSERT INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit)
            VALUES (?, 'free', 20, 3, 0, 0, 5, 0)
            ''', (user_id,))
            self.conn.commit()
            return {"tier": "free", "daily_search_limit": 20, "daily_deep_limit": 3, "daily_litreview_limit": 0, "daily_gap_analysis_limit": 0, "daily_export_limit": 5, "daily_digest_limit": 0}
        return {"tier": row[0], "daily_search_limit": row[1], "daily_deep_limit": row[2], "daily_litreview_limit": row[3], "daily_gap_analysis_limit": row[4], "daily_export_limit": row[5], "daily_digest_limit": row[6]}

    def set_user_tier(self, user_id: int, tier: str, limits: dict = None):
        default_limits = {
            "free": {"daily_search_limit": 20, "daily_deep_limit": 3, "daily_litreview_limit": 0, "daily_gap_analysis_limit": 0, "daily_export_limit": 5, "daily_digest_limit": 0},
            "premium": {"daily_search_limit": 100, "daily_deep_limit": 30, "daily_litreview_limit": 5, "daily_gap_analysis_limit": 5, "daily_export_limit": 50, "daily_digest_limit": 1},
            "pro": {"daily_search_limit": 500, "daily_deep_limit": 100, "daily_litreview_limit": 20, "daily_gap_analysis_limit": 20, "daily_export_limit": 200, "daily_digest_limit": 7},
        }
        l = limits or default_limits.get(tier, default_limits["free"])
        self.cursor.execute('''
        INSERT INTO user_tier (user_id, tier, daily_search_limit, daily_deep_limit, daily_litreview_limit, daily_gap_analysis_limit, daily_export_limit, daily_digest_limit, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET tier = ?, daily_search_limit = ?, daily_deep_limit = ?, daily_litreview_limit = ?, daily_gap_analysis_limit = ?, daily_export_limit = ?, daily_digest_limit = ?, updated_at = CURRENT_TIMESTAMP
        ''', (user_id, tier, l["daily_search_limit"], l["daily_deep_limit"], l["daily_litreview_limit"], l["daily_gap_analysis_limit"], l["daily_export_limit"], l["daily_digest_limit"], tier, l["daily_search_limit"], l["daily_deep_limit"], l["daily_litreview_limit"], l["daily_gap_analysis_limit"], l["daily_export_limit"], l["daily_digest_limit"]))
        self.conn.commit()

    def check_quota(self, user_id: int, action: str) -> tuple[bool, str]:
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
        }
        if action not in limit_map:
            return True, ""
        col, limit = limit_map[action]
        if limit <= 0:
            return False, f"您的方案 ({tier_info['tier']}) 不支援此功能，請升級為 Pro 會員解鎖。"
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

    def remove_paper_from_library(self, user_id: int, paper_id: str) -> bool:
        self.cursor.execute("DELETE FROM user_paper_library WHERE user_id = ? AND paper_id = ?", (user_id, paper_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_user_reports(self, user_id: int) -> list:
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

    def generate_sync_code(self, user_id: int) -> str:
        import random
        code = f"PF{random.randint(1000, 9999)}"
        return code

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


db = Database()
