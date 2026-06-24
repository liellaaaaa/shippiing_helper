import os, uuid
from jose import jwt
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from app.core.config import DOCUMENT_SERVER_URL, ONLYOFFICE_SECRET_KEY, API_BASE_URL


def _callback_base() -> str:
    """OnlyOffice 容器内需要用 host.docker.internal 才能访问宿主机后端"""
    return os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")


class OnlyOfficeService:
    # Class-level shared mapping: safe_key (UUID) -> original doc_key
    # Shared across ALL instances so onlyoffice.py and documents.py agree on mappings
    _safe_key_map: dict[str, str] = {}

    def _safe_key(self, document_key: str) -> str:
        """Generate pure-ASCII safe key and register mapping."""
        safe = uuid.uuid4().hex
        OnlyOfficeService._safe_key_map[safe] = document_key
        return safe

    def resolve_safe_key(self, safe_key: str) -> str | None:
        """Resolve safe key back to original doc_key."""
        return OnlyOfficeService._safe_key_map.get(safe_key)

    def generate_jwt_token(self, document_key: str, file_type: str) -> str:
        """Generate JWT using original doc_key as document.key (for callback compatibility)."""
        encoded_key = quote(document_key, safe="")
        now = datetime.utcnow()
        doc_url = f"{_callback_base()}/api/v1/onlyoffice/download/{encoded_key}"
        payload = {
            "document": {
                "key": document_key,  # Use original key so callback works
                "title": document_key,
                "fileType": file_type,
                "url": doc_url,  # OnlyOffice 7.1+ requires this
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
        """Build editor config using UUID as documentKey (for OnlyOffice routing)."""
        safe_key = self._safe_key(document_key)
        return {
            "token": token,
            "documentServerUrl": DOCUMENT_SERVER_URL,
            "documentKey": safe_key,  # UUID for routing
            "docType": doc_type,
        }

    def create_config(self, document_key: str, file_type: str, document_url: str = None) -> tuple[str, dict, str]:
        """
        Generate both JWT token and editor config with the SAME safe key.
        Returns (token, config, safe_key) tuple.
        Ensures documentKey in config and document.key in JWT match.
        safe_key is returned so caller can store document under UUID in DB.
        document_url: URL OnlyOffice uses to download the document (for JWT payload).
        """
        safe_key = self._safe_key(document_key)
        now = datetime.utcnow()
        # document.url in JWT must match what OnlyOffice uses to fetch the file
        doc_url = document_url or f"{_callback_base()}/api/v1/onlyoffice/download/{safe_key}"
        payload = {
            "document": {
                "key": safe_key,  # Use safe key for OnlyOffice routing
                "title": document_key,
                "fileType": file_type,
                "url": doc_url,  # OnlyOffice 7.1+ requires this in JWT
                "callbackUrl": f"{_callback_base()}/api/v1/onlyoffice/callback?doc_key={safe_key}",
            },
            "user": {"name": "admin", "id": "1"},
            "editorConfig": {
                "callbackUrl": f"{_callback_base()}/api/v1/onlyoffice/callback?doc_key={safe_key}",
                "mode": "edit",
                "forcesave": True,
            },
            "iat": now,
            "exp": now + timedelta(hours=2),
        }
        token = jwt.encode(payload, ONLYOFFICE_SECRET_KEY, algorithm="HS256")
        config = {
            "token": token,
            "documentServerUrl": DOCUMENT_SERVER_URL,
            "documentKey": safe_key,
            "docType": file_type,
            "title": document_key,
        }
        return token, config, safe_key