import os
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import DOCUMENT_SERVER_URL, ONLYOFFICE_SECRET_KEY, API_BASE_URL


class OnlyOfficeService:
    def generate_jwt_token(self, document_key: str, file_type: str) -> str:
        now = datetime.utcnow()
        payload = {
            "document": {
                "key": document_key,
                "title": f"Document.{file_type}",
                "fileType": file_type,
                "callbackUrl": f"{API_BASE_URL}/api/v1/onlyoffice/callback?doc_key={document_key}",
            },
            "user": {"name": "admin", "id": "1"},
            "editorConfig": {
                "callbackUrl": f"{API_BASE_URL}/api/v1/onlyoffice/callback?doc_key={document_key}",
                "mode": "edit",
            },
            "iat": now,
            "exp": now + timedelta(hours=2),
        }
        return jwt.encode(payload, ONLYOFFICE_SECRET_KEY, algorithm="HS256")

    def build_editor_config(self, token: str, document_key: str, doc_type: str) -> dict:
        return {
            "token": token,
            "documentServerUrl": DOCUMENT_SERVER_URL,
            "documentKey": document_key,
            "docType": doc_type,
        }