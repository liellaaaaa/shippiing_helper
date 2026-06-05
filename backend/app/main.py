from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.orders import router as orders_router
from app.api.v1.pi import router as pi_router
from app.api.v1.merge import router as merge_router
from app.api.v1.packages import router as packages_router
from app.api.v1.packaging import router as packaging_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1 import documents, msds, transport, export_codes, onlyoffice
from app.api.v1.data_center import router as data_center_router
from app.api.v1.transport_reports import router as transport_reports_router
from app.core.config import MSDS_DIR, TRANSPORT_REPORTS_DIR
from app.database import SessionLocal
from app.services.data_center_service import DataCenterService
from app.services.transport_service import TransportService

app = FastAPI(
    title="ShippingHelper API",
    version="1.0.0",
    description="外贸船务效率工具 - Phase 1 API",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders_router)
app.include_router(pi_router)
app.include_router(merge_router)
app.include_router(packages_router)
app.include_router(packaging_router)
app.include_router(dashboard_router)
app.include_router(documents.router)
app.include_router(msds.router)
app.include_router(transport.router)
app.include_router(export_codes.router)
app.include_router(onlyoffice.router)
app.include_router(data_center_router)
app.include_router(transport_reports_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    """启动时全量扫描 MSDS 和运输鉴定报告目录，建立内存索引。"""
    db = SessionLocal()
    try:
        dc_svc = DataCenterService()
        dc_count = dc_svc.scan_msds_directory(MSDS_DIR, db)
        print(f"[startup] MSDS index: {dc_count} files scanned")
    except Exception as e:
        print(f"[startup] MSDS index scan failed: {e}")
    try:
        tr_svc = TransportService()
        tr_count = tr_svc.scan_directory(TRANSPORT_REPORTS_DIR, db)
        print(f"[startup] Transport reports index: {tr_count} files scanned")
    except Exception as e:
        print(f"[startup] Transport reports index scan failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)