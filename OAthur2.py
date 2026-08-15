"""Google Drive 多用戶 1 鍵授權模組 (Direct REST 終極穩定版)"""
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from database import db

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SKIPPED_KEY = "__skipped__"
SKIPPED_FOLDER_NAME = "沒興趣 (略過)"
REDIRECT_URI = "https://paperfilter-bot.onrender.com/oauth2callback"

def _safe_filename(title: str, max_len: int = 80) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", title).strip()
    return (cleaned[:max_len] if cleaned else "paper").strip()

class DriveOAuthManager:
    def __init__(self):
        creds_json = os.getenv("GOOGLE_CLIENT_SECRETS_JSON")
        if creds_json:
            self.client_config = json.loads(creds_json)
        elif os.path.exists("credentials.json"):
            with open("credentials.json", "r", encoding="utf-8") as f:
                self.client_config = json.load(f)
        else:
            self.client_config = {}

    def get_client_info(self):
        return self.client_config.get("web", self.client_config.get("installed", {}))

    def get_auth_url(self, user_id: int) -> str:
        client_info = self.get_client_info()
        client_id = client_info.get("client_id")
        if not client_id:
            return "#"

        auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": str(user_id)
        }
        req = requests.Request("GET", auth_endpoint, params=params).prepare()
        return req.url

    def exchange_code(self, user_id: int, code: str) -> bool:
        """ 直接向 Google Token Endpoint 請求換發 Token """
        try:
            client_info = self.get_client_info()
            client_id = client_info.get("client_id")
            client_secret = client_info.get("client_secret")

            if not client_id or not client_secret:
                print("❌ 缺少 Client ID 或 Secret", file=sys.stderr)
                return False

            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            res = requests.post(token_url, data=data, timeout=10)
            token_data = res.json()

            if "error" in token_data:
                print(f"❌ Google Token 交換失敗: {token_data.get('error_description')}", file=sys.stderr)
                return False

            # 將完整 Token 存入資料庫
            db.save_token(user_id, json.dumps(token_data))
            print(f"✅ 用戶 {user_id} 成功存入 Google Drive Token！", file=sys.stderr)
            return True
        except Exception as e:
            print(f"❌ 換取 Token 例外: {e}", file=sys.stderr)
            return False

    def get_user_service(self, user_id: int):
        token_json = db.get_token(user_id)
        if not token_json:
            return None

        token_info = json.loads(token_json)
        client_info = self.get_client_info()

        creds = Credentials(
            token=token_info.get("access_token"),
            refresh_token=token_info.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_info.get("client_id"),
            client_secret=client_info.get("client_secret"),
            scopes=SCOPES
        )
        return build('drive', 'v3', credentials=creds, cache_discovery=False)

    def create_or_get_folder(self, service, folder_name: str) -> str:
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=query, fields="files(id, name)").execute()
        files = res.get('files', [])
        if files:
            return files[0]['id']
        
        folder = service.files().create(
            body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"},
            fields="id"
        ).execute()
        return folder['id']

    def archive_paper(self, user_id: int, folder_name: str, title: str, summary: str, link: str) -> tuple[bool, str]:
        service = self.get_user_service(user_id)
        if not service:
            return False, "尚未完成 Google 授權"

        try:
            folder_id = self.create_or_get_folder(service, folder_name)
            safe_name = _safe_filename(title)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            note = f"標題: {title}\n連結: {link}\n歸檔時間: {timestamp}\n資料夾: {folder_name}\n\n摘要:\n{summary}"
            
            media = MediaIoBaseUpload(io.BytesIO(note.encode("utf-8")), mimetype="text/plain")
            service.files().create(body={"name": f"{safe_name}.txt", "parents": [folder_id]}, media_body=media).execute()
            return True, folder_name
        except Exception as e:
            return False, str(e)

drive_manager = DriveOAuthManager()