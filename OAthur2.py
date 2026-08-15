"""Google Drive 多用戶 1 鍵授權模組"""
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

    def get_auth_url(self, user_id: int) -> str:
        if not self.client_config:
            return "#"
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        # 將 user_id 放在 state 裡面，Google 授權完會自動帶回來
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=str(user_id)
        )
        return auth_url

    def exchange_code(self, user_id: int, code: str) -> bool:
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            flow.fetch_token(code=code)
            db.save_token(user_id, flow.credentials.to_json())
            return True
        except Exception as e:
            print(f"換取 Token 失敗: {e}", file=sys.stderr)
            return False

    def get_user_service(self, user_id: int):
        token_json = db.get_token(user_id)
        if not token_json:
            return None
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
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
            note = f"標題: {title}\n連結: {link}\n歸檔時間: {datetime.now(timezone.utc)}\n\n摘要:\n{summary}"
            
            media = MediaIoBaseUpload(io.BytesIO(note.encode("utf-8")), mimetype="text/plain")
            service.files().create(body={"name": f"{safe_name}.txt", "parents": [folder_id]}, media_body=media).execute()
            return True, folder_name
        except Exception as e:
            return False, str(e)

drive_manager = DriveOAuthManager()