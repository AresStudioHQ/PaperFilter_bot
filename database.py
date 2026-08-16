import sqlite3
import json
import os

DB_FILE = "users_data.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # 用戶表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                gdrive_token TEXT,
                positive_keywords TEXT DEFAULT '{}',
                negative_keywords TEXT DEFAULT '{}'
            )
        ''')
        # 已讀論文表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_papers (
                user_id INTEGER,
                paper_id TEXT,
                PRIMARY KEY (user_id, paper_id)
            )
        ''')
        # 分類表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_categories (
                user_id INTEGER,
                category_name TEXT,
                PRIMARY KEY(user_id, category_name)
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

    # --- 2. 論文紀錄與推薦權重 ---
    def add_seen_paper(self, user_id: int, paper_id: str):
        self.cursor.execute('INSERT OR IGNORE INTO seen_papers (user_id, paper_id) VALUES (?, ?)', (user_id, paper_id))
        self.conn.commit()

    def get_seen_papers(self, user_id: int) -> set[str]:
        self.cursor.execute("SELECT paper_id FROM seen_papers WHERE user_id = ?", (user_id,))
        return {r[0] for r in self.cursor.fetchall()}

    def update_preference(self, user_id: int, title: str, is_interested: bool):
        self.cursor.execute("SELECT positive_keywords, negative_keywords FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        pos = json.loads(row[0]) if row and row[0] else {}
        neg = json.loads(row[1]) if row and row[1] else {}
        target = pos if is_interested else neg
        for word in title.lower().split():
            if len(word) > 3 and word.isalpha():
                target[word] = target.get(word, 0) + 1
        
        if not row:
            self.cursor.execute("INSERT INTO users (user_id, positive_keywords, negative_keywords) VALUES (?, ?, ?)",
                               (user_id, json.dumps(pos), json.dumps(neg)))
        else:
            self.cursor.execute("UPDATE users SET positive_keywords = ?, negative_keywords = ? WHERE user_id = ?",
                               (json.dumps(pos), json.dumps(neg), user_id))
        self.conn.commit()

    def get_user_bias(self, user_id: int) -> tuple[dict, dict]:
        self.cursor.execute("SELECT positive_keywords, negative_keywords FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row:
            return json.loads(row[0] or '{}'), json.loads(row[1] or '{}')
        return {}, {}

    # --- 3. 分類管理功能 (新升級) ---
    def get_user_categories(self, user_id):
        self.cursor.execute("SELECT category_name FROM user_categories WHERE user_id = ?", (user_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def add_user_category(self, user_id, category_name):
        self.cursor.execute("INSERT OR IGNORE INTO user_categories (user_id, category_name) VALUES (?, ?)", (user_id, category_name))
        self.conn.commit()

    def rename_user_category(self, user_id, old_name, new_name):
        self.cursor.execute("UPDATE user_categories SET category_name = ? WHERE user_id = ? AND category_name = ?", (new_name, user_id, old_name))
        self.conn.commit()

    def delete_user_category(self, user_id, category_name):
        self.cursor.execute("DELETE FROM user_categories WHERE user_id = ? AND category_name = ?", (user_id, category_name))
        self.conn.commit()

db = Database()