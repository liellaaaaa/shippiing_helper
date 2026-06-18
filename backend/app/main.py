from dotenv import load_dotenv
load_dotenv()

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
from app.api.v1.name_mapping import router as name_mapping_router
from app.api.v1.auth import router as auth_router
from app.core.config import MSDS_DIR, TRANSPORT_REPORTS_DIR, CUSTOMS_CODES_JSON
from app.database import SessionLocal
from app.services.data_center_service import DataCenterService
from app.services.transport_service import TransportService
from app.services.name_mapping_service import load_name_mapping
from app.services.customs_name_service import CustomsNameService

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
app.include_router(name_mapping_router)
app.include_router(auth_router)

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
import os

JWT_SECRET = os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """全局认证中间件，排除登录和健康检查端点."""
    # 放行路径
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"] or \
       request.url.path.startswith("/api/v1/auth/"):
        return await call_next(request)

    # 检查 Authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "未授权，请先登录"}
        )

    # 验证 token
    try:
        token = auth_header[7:]
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )
        request.state.user = {"name": payload.get("sub")}
    except JWTError:
        return JSONResponse(
            status_code=401,
            content={"detail": "无效的认证凭证"}
        )

    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    """启动时加载品名对照表，全量扫描 MSDS 和运输鉴定报告目录，建立内存索引。"""
    # 加载品名中英文对照表
    load_name_mapping()
    print("[startup] Product name mapping loaded")
    # 加载报关名称服务
    CustomsNameService.get_instance(CUSTOMS_CODES_JSON)
    print("[startup] Customs name service loaded")
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