"""Google Drive 歸檔模組（單一使用者 MVP）"""

import io
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
DRIVE_MAP_FILE = "folder_drive_ids.json"
SKIPPED_KEY = "__skipped__"
SKIPPED_FOLDER_NAME = "沒興趣 (略過)"
DELETED_SUFFIX = " (已刪除選項)"


def _safe_filename(title: str, max_len: int = 80) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return (cleaned[:max_len] if cleaned else "paper").strip()


def arxiv_pdf_url(link: str) -> str | None:
    if "/abs/" in link:
        return link.replace("/abs/", "/pdf/") + ".pdf"
    return None


class DriveStorage:
    """透過 Service Account 存取親戚共享的 Google Drive 資料夾。"""

    def __init__(self):
        self._service = None
        self._root_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
        self._enabled = False
        self._init_error = None

        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not self._root_id:
            self._init_error = "未設定 GOOGLE_DRIVE_ROOT_FOLDER_ID"
            return

        try:
            if creds_json:
                info = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    info, scopes=SCOPES
                )
            elif creds_path and os.path.exists(creds_path):
                credentials = service_account.Credentials.from_service_account_file(
                    creds_path, scopes=SCOPES
                )
            else:
                self._init_error = (
                    "未設定 GOOGLE_CREDENTIALS_JSON 或 GOOGLE_APPLICATION_CREDENTIALS"
                )
                return

            self._service = build("drive", "v3", credentials=credentials, cache_discovery=False)
            self._enabled = True
        except Exception as exc:
            self._init_error = str(exc)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def status_message(self) -> str:
        if self.enabled:
            return "✅ Google Drive 雲端歸檔已連線"
        return f"⚠️ 雲端歸檔未啟用：{self._init_error}"

    def _load_drive_map(self) -> dict:
        if not os.path.exists(DRIVE_MAP_FILE):
            return {}
        with open(DRIVE_MAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_drive_map(self, drive_map: dict):
        with open(DRIVE_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(drive_map, f, ensure_ascii=False, indent=4)

    def _create_folder(self, name: str, parent_id: str) -> str:
        body = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = (
            self._service.files()
            .create(body=body, fields="id", supportsAllDrives=True)
            .execute()
        )
        return folder["id"]

    def _rename_folder(self, folder_id: str, new_name: str):
        self._service.files()
        .update(
            fileId=folder_id,
            body={"name": new_name},
            supportsAllDrives=True,
            fields="id",
        )
        .execute()

    def _folder_exists(self, folder_id: str) -> bool:
        try:
            self._service.files()
            .get(fileId=folder_id, fields="id", supportsAllDrives=True)
            .execute()
            return True
        except HttpError:
            return False

    def ensure_folder(self, key: str, folder_name: str) -> str | None:
        """確保分類在 Drive 上有對應資料夾，回傳 folder_id。"""
        if not self.enabled:
            return None

        drive_map = self._load_drive_map()
        folder_id = drive_map.get(key)

        if folder_id and self._folder_exists(folder_id):
            return folder_id

        folder_id = self._create_folder(folder_name, self._root_id)
        drive_map[key] = folder_id
        self._save_drive_map(drive_map)
        return folder_id

    def ensure_skipped_folder(self) -> str | None:
        return self.ensure_folder(SKIPPED_KEY, SKIPPED_FOLDER_NAME)

    def sync_categories(self, categories: dict[str, str]):
        """依 categories.json 同步 Drive 資料夾（新增缺漏的）。"""
        if not self.enabled:
            return

        self.ensure_skipped_folder()
        for key, name in categories.items():
            if key.startswith("__"):
                continue
            self.ensure_folder(key, name)

    def create_category_folder(self, key: str, folder_name: str) -> bool:
        if not self.enabled:
            return False
        self.ensure_folder(key, folder_name)
        return True

    def rename_category_folder(self, key: str, new_name: str) -> bool:
        if not self.enabled:
            return False

        drive_map = self._load_drive_map()
        folder_id = drive_map.get(key)
        if not folder_id:
            return False

        self._rename_folder(folder_id, new_name)
        return True

    def mark_category_deleted(self, key: str, folder_name: str) -> bool:
        if not self.enabled:
            return False

        drive_map = self._load_drive_map()
        folder_id = drive_map.get(key)
        if not folder_id:
            return False

        deleted_name = f"{folder_name}{DELETED_SUFFIX}"
        self._rename_folder(folder_id, deleted_name)
        return True

    def archive_paper(
        self,
        folder_key: str,
        folder_name: str,
        title: str,
        summary: str,
        link: str,
    ) -> tuple[bool, str]:
        """將論文摘要與 PDF（若為 arXiv）上傳至指定 Drive 資料夾。"""
        if not self.enabled:
            return False, "雲端未設定"

        folder_id = self.ensure_folder(folder_key, folder_name)
        if not folder_id:
            return False, "無法建立雲端資料夾"

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        safe_name = _safe_filename(title)

        note_content = (
            f"標題: {title}\n"
            f"連結: {link}\n"
            f"歸檔時間: {timestamp}\n"
            f"資料夾: {folder_name}\n\n"
            f"摘要:\n{summary}\n"
        )

        try:
            media = MediaIoBaseUpload(
                io.BytesIO(note_content.encode("utf-8")),
                mimetype="text/plain",
            )
            self._service.files()
            .create(
                body={"name": f"{safe_name}.txt", "parents": [folder_id]},
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            )
            .execute()

            pdf_url = arxiv_pdf_url(link)
            if pdf_url:
                response = requests.get(pdf_url, timeout=90)
                if response.status_code == 200:
                    pdf_media = MediaIoBaseUpload(
                        io.BytesIO(response.content),
                        mimetype="application/pdf",
                    )
                    self._service.files()
                    .create(
                        body={"name": f"{safe_name}.pdf", "parents": [folder_id]},
                        media_body=pdf_media,
                        fields="id",
                        supportsAllDrives=True,
                    )
                    .execute()

            return True, folder_name
        except Exception as exc:
            print(f"Drive 歸檔失敗: {exc}", file=sys.stderr)
            return False, str(exc)

    def archive_skipped_paper(self, title: str, summary: str, link: str) -> tuple[bool, str]:
        return self.archive_paper(SKIPPED_KEY, SKIPPED_FOLDER_NAME, title, summary, link)


_drive_instance: DriveStorage | None = None


def get_drive() -> DriveStorage:
    global _drive_instance
    if _drive_instance is None:
        _drive_instance = DriveStorage()
    return _drive_instance
