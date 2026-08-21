import os
import sys
import io
import re
import json
import urllib.parse
from datetime import datetime, timezone
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from database import db

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
]

REQUIRED_SCOPES = {'https://www.googleapis.com/auth/drive.file'}

DELETED_SUFFIX = "（已移除）"


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return cleaned[:80] if cleaned else "untitled"


class DriveOAuthManager:
    def __init__(self):
        self.credentials_file = "credentials.json"

    def get_client_info(self) -> dict:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:10000/oauth2callback")

        secrets_json = os.getenv("GOOGLE_CLIENT_SECRETS_JSON")
        if secrets_json:
            try:
                data = json.loads(secrets_json)
                installed = data.get("installed") or data.get("web")
                if installed:
                    return {
                        "client_id": installed.get("client_id"),
                        "client_secret": installed.get("client_secret"),
                        "redirect_uri": installed.get("redirect_uris", [redirect_uri])[0],
                    }
            except Exception as e:
                print(f"解析 GOOGLE_CLIENT_SECRETS_JSON 警告: {e}", file=sys.stderr)

        if client_id and client_secret:
            return {"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri}

        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    installed = data.get("installed") or data.get("web")
                    if installed:
                        return {
                            "client_id": installed.get("client_id"),
                            "client_secret": installed.get("client_secret"),
                            "redirect_uri": installed.get("redirect_uris", [redirect_uri])[0],
                        }
            except Exception as e:
                print(f"讀取 credentials.json 失敗: {e}", file=sys.stderr)

        return {"client_id": None, "client_secret": None, "redirect_uri": redirect_uri}

    def get_auth_url(self, user_id: int) -> str | None:
        client_info = self.get_client_info()
        client_id = client_info.get("client_id")
        redirect_uri = client_info.get("redirect_uri")
        if not client_id:
            return None
        scope_str = urllib.parse.quote(" ".join(SCOPES))
        encoded_redirect = urllib.parse.quote(redirect_uri, safe="")
        url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={encoded_redirect}&"
            f"response_type=code&"
            f"scope={scope_str}&"
            f"access_type=offline&"
            f"include_granted_scopes=true&"
            f"prompt=consent&"
            f"state={user_id}"
        )
        print(f"🔗 OAuth URL scopes: {[s for s in SCOPES]}", file=sys.stderr)
        print(f"🔗 OAuth URL: {url[:200]}...", file=sys.stderr)
        return url

    def exchange_code(self, user_id: int, code: str) -> tuple[bool, str]:
        client_info = self.get_client_info()
        data = {
            "code": code,
            "client_id": client_info.get("client_id"),
            "client_secret": client_info.get("client_secret"),
            "redirect_uri": client_info.get("redirect_uri"),
            "grant_type": "authorization_code",
        }
        try:
            res = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=10)
            token_data = res.json()
            if "error" in token_data:
                err = token_data.get("error_description") or token_data.get("error", "unknown")
                print(f"❌ Google Token 交換失敗: {err}", file=sys.stderr)
                return False, err
            granted_scopes = set(token_data.get("scope", "").split())
            print(f"✅ 用戶 {user_id} Token 交換成功", file=sys.stderr)
            print(f"   授權的 scopes: {granted_scopes}", file=sys.stderr)
            missing = REQUIRED_SCOPES - granted_scopes
            if missing:
                print(f"   ⚠️ 缺少必要 scope: {missing}", file=sys.stderr)
                db.save_token(user_id, json.dumps(token_data))
                return False, f"缺少必要授權: {', '.join(missing)}。請在 Google Cloud Console 的 OAuth 同意畫面中確認 drive.file scope 已發布。"
            db.save_token(user_id, json.dumps(token_data))
            print(f"   ✅ 用戶 {user_id} 成功存入 Google Drive Token（含 drive.file）", file=sys.stderr)
            return True, "success"
        except Exception as e:
            print(f"❌ 換取 Token 例外: {e}", file=sys.stderr)
            return False, str(e)

    def get_user_service(self, user_id: int):
        token_json = db.get_token(user_id)
        if not token_json:
            return None
        token_info = json.loads(token_json)
        granted = set(token_info.get("scope", "").split())
        if "https://www.googleapis.com/auth/drive.file" not in granted:
            print(f"⚠️ 用戶 {user_id} token 缺少 drive.file scope，清除 token", file=sys.stderr)
            db.remove_token(user_id)
            return None
        client_info = self.get_client_info()
        creds = Credentials(
            token=token_info.get("access_token"),
            refresh_token=token_info.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_info.get("client_id"),
            client_secret=client_info.get("client_secret"),
            scopes=SCOPES,
        )
        return build('drive', 'v3', credentials=creds, cache_discovery=False)

    def get_or_create_root_app_folder(self, service) -> str:
        """確保雲端硬碟根目錄有 PaperFilterBot 主資料夾"""
        query = "name = 'PaperFilterBot' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and 'root' in parents"
        res = service.files().list(q=query, fields="files(id, name)").execute()
        files = res.get('files', [])
        if files:
            return files[0]['id']
        folder = service.files().create(
            body={"name": "PaperFilterBot", "mimeType": "application/vnd.google-apps.folder", "parents": ["root"]},
            fields="id",
        ).execute()
        return folder['id']

    def create_or_get_folder(self, service, folder_name: str) -> str:
        """將所有分類資料夾收納在 PaperFilterBot/ 之下"""
        root_app_id = self.get_or_create_root_app_folder(service)
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{root_app_id}' in parents"
        res = service.files().list(q=query, fields="files(id, name)").execute()
        files = res.get('files', [])
        if files:
            return files[0]['id']
        folder = service.files().create(
            body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder", "parents": [root_app_id]},
            fields="id",
        ).execute()
        return folder['id']

    def rename_folder(self, user_id: int, old_name: str, new_name: str) -> bool:
        """同步更名 Google Drive 裡的子資料夾"""
        service = self.get_user_service(user_id)
        if not service:
            return False
        try:
            root_app_id = self.get_or_create_root_app_folder(service)
            query = f"name = '{old_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{root_app_id}' in parents"
            res = service.files().list(q=query, fields="files(id, name)").execute()
            files = res.get('files', [])
            if files:
                folder_id = files[0]['id']
                service.files().update(fileId=folder_id, body={"name": new_name}).execute()
                return True
            return False
        except Exception as e:
            print(f"更名雲端資料夾失敗: {e}", file=sys.stderr)
            return False

    def mark_folder_deleted(self, user_id: int, folder_name: str) -> bool:
        new_name = f"{folder_name}{DELETED_SUFFIX}"
        return self.rename_folder(user_id, folder_name, new_name)

    def append_to_references_bib(self, service, folder_id: str, bibtex: str):
        """在該分類資料夾下維護 references.bib 總庫（追加新 BibTeX）"""
        if not bibtex:
            return
        query = f"name = 'references.bib' and trashed = false and '{folder_id}' in parents"
        res = service.files().list(q=query, fields="files(id, name)").execute()
        files = res.get('files', [])
        existing_content = ""
        file_id = None
        if files:
            file_id = files[0]['id']
            try:
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                existing_content = fh.getvalue().decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"讀取 references.bib 失敗: {e}", file=sys.stderr)

        if bibtex.strip() in existing_content:
            return

        new_content = existing_content.strip() + "\n\n" + bibtex.strip() + "\n"
        media = MediaIoBaseUpload(io.BytesIO(new_content.encode('utf-8')), mimetype="text/plain", resumable=False)
        if file_id:
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            service.files().create(
                body={"name": "references.bib", "parents": [folder_id]},
                media_body=media
            ).execute()

    def archive_paper(
        self,
        user_id: int,
        folder_name: str,
        title: str,
        summary: str,
        link: str,
        bibtex: str = ""
    ) -> tuple[bool, str]:
        """
        雙軌歸檔：
        1. 方案 A：單篇文件內建完整摘要與專屬 BibTeX 程式碼
        2. 方案 B：自動追加進該資料夾的 references.bib 總庫檔案
        """
        service = self.get_user_service(user_id)
        if not service:
            return False, "尚未完成 Google 授權"
        try:
            folder_id = self.create_or_get_folder(service, folder_name)
            safe_name = _safe_filename(title)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            bib_section = f"\n\n====================\n【BibTeX 學術引用代碼】\n====================\n{bibtex}\n" if bibtex else ""
            note = (
                f"標題: {title}\n"
                f"連結: {link}\n"
                f"歸檔時間: {timestamp}\n"
                f"所屬分類: {folder_name}\n\n"
                f"【核心摘要】\n"
                f"{summary}"
                f"{bib_section}"
            )
            media = MediaIoBaseUpload(io.BytesIO(note.encode("utf-8")), mimetype="text/plain")
            service.files().create(body={"name": f"{safe_name}.txt", "parents": [folder_id]}, media_body=media).execute()

            # 方案 B：自動維護資料夾內的 references.bib 總庫
            if bibtex and folder_name not in ("返回", "略過"):
                try:
                    self.append_to_references_bib(service, folder_id, bibtex)
                except Exception as b_err:
                    print(f"追加 references.bib 警告: {b_err}", file=sys.stderr)

            return True, folder_name
        except Exception as e:
            return False, str(e)


drive_manager = DriveOAuthManager()

