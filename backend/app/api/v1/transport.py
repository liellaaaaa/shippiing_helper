from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.transport_service import TransportService
import tempfile, os

router = APIRouter(prefix="/api/v1/transport", tags=["transport"])


@router.post("/upload")
async def upload_transport_report(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF supported")
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(await file.read())
    tmp.close()
    try:
        text = TransportService.extract_text_from_pdf(tmp.name)
        fields = TransportService.extract_fields(text)
        return fields
    finally:
        os.unlink(tmp.name)