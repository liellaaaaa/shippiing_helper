import os
from jose import jwt
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from app.core.config import DOCUMENT_SERVER_URL, ONLYOFFICE_SECRET_KEY, API_BASE_URL


def _callback_base() -> str:
    """OnlyOffice 容器内需要用 host.docker.internal 才能访问宿主机后端"""
    return os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")


class OnlyOfficeService:
    def generate_jwt_token(self, document_key: str, file_type: str) -> str:
        # URL-encode doc_key for safe transport in URLs
        encoded_key = quote(document_key, safe="")
        now = datetime.utcnow()
        payload = {
            "document": {
                "key": encoded_key,
                "title": f"Document.{file_type}",
                "fileType": file_type,
                "callbackUrl": f"{_callback_base()}/api/v1/onlyoffice/callback?doc_key={encoded_key}",
            },
            "user": {"name": "admin", "id": "1"},
            "editorConfig": {
                "callbackUrl": f"{_callback_base()}/api/v1/onlyoffice/callback?doc_key={encoded_key}",
                "mode": "edit",
                "forcesave": True,
            },
            "iat": now,
            "exp": now + timedelta(hours=2),
        }
        return jwt.encode(payload, ONLYOFFICE_SECRET_KEY, algorithm="HS256")

    def build_editor_config(self, token: str, document_key: str, doc_type: str) -> dict:
        # URL-encode doc_key for safe use in URLs
        encoded_key = quote(document_key, safe="")
        return {
            "token": token,
            "documentServerUrl": DOCUMENT_SERVER_URL,
            "documentKey": encoded_key,
            "docType": doc_type,
        }