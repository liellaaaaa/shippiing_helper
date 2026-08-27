import os, uuid, asyncio, logging, base64, hashlib
import httpx
from jose import jwt
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from app.core.config import DOCUMENT_SERVER_URL, ONLYOFFICE_SECRET_KEY, API_BASE_URL

logger = logging.getLogger(__name__)

# Bounded concurrency for OnlyOffice converter
_CONVERT_SEMAPHORE = asyncio.Semaphore(5)


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

    def create_config(self, document_key: str, file_type: str, document_url: str = None, existing_safe_key: str = None) -> tuple[str, dict, str]:
        """
        Generate both JWT token and editor config with the SAME safe key.
        Returns (token, config, safe_key) tuple.
        Ensures documentKey in config and document.key in JWT match.
        safe_key is returned so caller can store document under UUID in DB.
        document_url: URL OnlyOffice uses to download the document (for JWT payload).
        existing_safe_key: reuse a previously-generated safe key (for re-opening existing docs).
        """
        if existing_safe_key:
            safe_key = existing_safe_key
            OnlyOfficeService._safe_key_map[safe_key] = document_key
        else:
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


# ---------------------------------------------------------------------------
# OnlyOffice Conversion API — DOCX → PDF
# ---------------------------------------------------------------------------

def _sign_converter_jwt(body: dict) -> str:
    """Sign JWT for the OnlyOffice /converter endpoint.

    When JWT is enabled, the request body fields are embedded as the JWT
    payload and sent as {"token": "<jwt>"}.
    """
    payload = {**body, "iat": datetime.utcnow(), "exp": datetime.utcnow() + timedelta(minutes=10)}
    return jwt.encode(payload, ONLYOFFICE_SECRET_KEY, algorithm="HS256")


def _create_temp_doc_record(docx_bytes: bytes, filename: str, db) -> str:
    """Store docx in ShipmentDoc temporarily so OnlyOffice can fetch it via HTTP."""
    from app.models.shipment_doc import ShipmentDoc
    temp_key = f"_temp_convert_{uuid.uuid4().hex}"
    content = base64.b64encode(docx_bytes).decode()
    content_hash = hashlib.md5(docx_bytes).hexdigest()
    record = ShipmentDoc(
        doc_key=temp_key,
        doc_type="msds_convert",
        order_id=None,
        file_blob=content,
        content_hash=content_hash,
        version=1,
        file_name=filename,
        created_by="system_converter",
    )
    db.add(record)
    db.commit()
    return temp_key


def _delete_temp_doc_record(temp_key: str, db) -> None:
    """Delete the temporary ShipmentDoc record."""
    from app.models.shipment_doc import ShipmentDoc
    try:
        db.query(ShipmentDoc).filter(ShipmentDoc.doc_key == temp_key).delete()
        db.commit()
    except Exception as e:
        logger.warning(f"[converter] Failed to clean up temp record {temp_key}: {e}")
        db.rollback()


async def convert_docx_to_pdf(docx_bytes: bytes, filename: str) -> tuple:
    """Convert docx bytes to PDF via OnlyOffice Conversion API.

    1. Store docx temporarily in DB so OnlyOffice can fetch it
    2. POST to /converter with JWT
    3. Download converted PDF from fileUrl
    4. Clean up temp record

    Returns: (content_bytes, extension) — falls back to (docx_bytes, ".docx") on failure.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    temp_key = None
    try:
        temp_key = _create_temp_doc_record(docx_bytes, filename, db)

        source_url = f"{_callback_base()}/api/v1/onlyoffice/download/{temp_key}"
        conversion_key = f"convert_{uuid.uuid4().hex}"

        converter_body = {
            "async": False,
            "filetype": "docx",
            "outputtype": "pdf",
            "key": conversion_key,
            "title": filename,
            "url": source_url,
        }

        token = _sign_converter_jwt(converter_body)
        request_body = {"token": token}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{DOCUMENT_SERVER_URL}/converter",
                json=request_body,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()

        if result.get("endConvert") is not True:
            error_msg = result.get("error", "Unknown conversion error")
            logger.error(f"[converter] OnlyOffice conversion failed for {filename}: {error_msg}")
            return docx_bytes, ".docx"

        file_url = result.get("fileUrl")
        if not file_url:
            logger.error(f"[converter] No fileUrl in conversion response for {filename}")
            return docx_bytes, ".docx"

        async with httpx.AsyncClient(timeout=60.0) as client:
            pdf_resp = await client.get(file_url)
            pdf_resp.raise_for_status()
            pdf_bytes = pdf_resp.content

        if len(pdf_bytes) == 0:
            logger.error(f"[converter] Downloaded PDF is empty for {filename}")
            return docx_bytes, ".docx"

        logger.info(f"[converter] Converted {filename}: {len(docx_bytes)} -> {len(pdf_bytes)} bytes")
        return pdf_bytes, ".pdf"

    except Exception as e:
        logger.error(f"[converter] Conversion failed for {filename}: {e}")
        return docx_bytes, ".docx"

    finally:
        if temp_key:
            _delete_temp_doc_record(temp_key, db)
        db.close()


async def convert_docx_to_pdf_batch(tasks: list) -> list:
    """Convert multiple docx files to PDF concurrently with bounded concurrency.

    Args:
        tasks: list of (docx_bytes, filename) tuples

    Returns:
        list of (content_bytes, extension) tuples, same order as input
    """
    async def _bounded_convert(docx_bytes, filename):
        async with _CONVERT_SEMAPHORE:
            return await convert_docx_to_pdf(docx_bytes, filename)

    return await asyncio.gather(
        *[_bounded_convert(b, f) for b, f in tasks],
        return_exceptions=False,
    )


def cleanup_stale_temp_records(max_age_minutes: int = 30) -> int:
    """Delete temporary conversion records older than max_age_minutes.

    Safety net for orphaned records from crashed conversions.
    """
    from app.database import SessionLocal
    from app.models.shipment_doc import ShipmentDoc

    cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    db = SessionLocal()
    try:
        deleted = db.query(ShipmentDoc).filter(
            ShipmentDoc.doc_key.like("_temp_convert_%"),
            ShipmentDoc.created_at < cutoff,
        ).delete()
        db.commit()
        if deleted:
            logger.info(f"[converter] Cleaned up {deleted} stale temp records")
        return deleted
    except Exception as e:
        logger.error(f"[converter] Cleanup failed: {e}")
        db.rollback()
        return 0
    finally:
        db.close()