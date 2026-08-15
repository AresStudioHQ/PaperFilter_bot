import sqlite3
import json
import os

DB_FILE = "users_data.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # 儲存每位用戶的 Google Drive Token 與個人偏好
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                gdrive_token TEXT,
                positive_keywords TEXT DEFAULT '{}',
                negative_keywords TEXT DEFAULT '{}'
            )
        ''')
        self.conn.commit()

    def get_token(self, user_id: int) -> str | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT gdrive_token FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def save_token(self, user_id: int, token_json: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, gdrive_token) 
            VALUES (?, ?) 
            ON CONFLICT(user_id) DO UPDATE SET gdrive_token = ?
        ''', (user_id, token_json, token_json))
        self.conn.commit()

    def update_preference(self, user_id: int, title: str, is_interested: bool):
        """ 當用戶按資料夾(喜歡)或沒興趣(不喜歡)時，動態學習詞彙 """
        cursor = self.conn.cursor()
        cursor.execute("SELECT positive_keywords, negative_keywords FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        pos = json.loads(row[0]) if row and row[0] else {}
        neg = json.loads(row[1]) if row and row[1] else {}

        target = pos if is_interested else neg
        for word in title.lower().split():
            if len(word) > 3 and word.isalpha():
                target[word] = target.get(word, 0) + 1

        if not row:
            cursor.execute("INSERT INTO users (user_id, positive_keywords, negative_keywords) VALUES (?, ?, ?)",
                           (user_id, json.dumps(pos), json.dumps(neg)))
        else:
            cursor.execute("UPDATE users SET positive_keywords = ?, negative_keywords = ? WHERE user_id = ?",
                           (json.dumps(pos), json.dumps(neg), user_id))
        self.conn.commit()

    def get_user_bias(self, user_id: int) -> tuple[dict, dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT positive_keywords, negative_keywords FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0] or '{}'), json.loads(row[1] or '{}')
        return {}, {}

db = Database()