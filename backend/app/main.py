from dotenv import load_dotenv
load_dotenv()

import os
import subprocess
import httpx
from sqlalchemy import text
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, JSONResponse
from jose import jwt, JWTError

from app.api.v1.orders import router as orders_router
from app.api.v1.pi import router as pi_router
from app.api.v1.merge import router as merge_router
from app.api.v1.packages import router as packages_router
from app.api.v1.packaging import router as packaging_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1 import documents, msds, transport, export_codes, onlyoffice
from app.api.v1.msds_generator import router as msds_generator_router
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
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174", "https://penholder-cleat-unsterile.ngrok-free.dev"],
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
app.include_router(msds_generator_router)

# OnlyOffice Document Server 代理（解决 ngrok 单端口转发问题）
DOCUMENT_SERVER = os.getenv("DOCUMENT_SERVER_URL", "http://localhost:8080")

@app.api_route("/documentserver/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
async def proxy_documentserver(path: str, request: Request):
    """代理 OnlyOffice Document Server 请求，实现单端口转发"""
    target_url = f"{DOCUMENT_SERVER}/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    body = await request.body()
    try:
        headers.pop("accept-encoding", None)
        headers.pop("Accept-Encoding", None)
        headers["Accept-Encoding"] = "identity"
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
            )
        response_headers = dict(resp.headers)
    except httpx.ConnectError:
        return Response(content="OnlyOffice server not available", status_code=503)
    except httpx.TimeoutException:
        return Response(content="OnlyOffice server timeout", status_code=504)

    response_headers["Access-Control-Allow-Origin"] = "*"
    response_headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response_headers["Access-Control-Allow-Headers"] = "*"
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=response_headers,
    )

# ========== /health 端点（必须在 serve_spa 之前注册）==========

@app.get("/health")
def health():
    """
    系统连通性检测：
    - api:         直接返回 ok
    - onlyoffice:  httpx.get(DOCUMENT_SERVER_URL + "/health")
    - database:    SQLAlchemy SELECT 1
    - tesseract:   subprocess.run(["tesseract", "--version"])
    """
    DOCUMENT_SERVER_URL = os.getenv("DOCUMENT_SERVER_URL", "http://localhost:8080")
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")

    checks = {
        "api":        {"status": "ok", "message": "正常运行"},
        "onlyoffice": {"status": "error", "message": ""},
        "database":   {"status": "error", "message": ""},
        "tesseract":  {"status": "error", "message": ""},
    }

    # 2. OnlyOffice
    try:
        resp = httpx.get(DOCUMENT_SERVER_URL, timeout=5.0, follow_redirects=True)
        checks["onlyoffice"] = {"status": "ok", "message": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        checks["onlyoffice"] = {"status": "error", "message": "连接失败"}
    except httpx.TimeoutException:
        checks["onlyoffice"] = {"status": "error", "message": "响应超时"}
    except Exception as e:
        checks["onlyoffice"] = {"status": "error", "message": str(e)}

    # 3. SQLite 数据库
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db.commit()
        checks["database"] = {"status": "ok", "message": "正常"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}
    finally:
        db.close()

    # 4. Tesseract OCR
    try:
        result = subprocess.run(
            [TESSERACT_CMD, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            first_line = result.stdout.strip().split("\n")[0]
            checks["tesseract"] = {"status": "ok", "message": first_line}
        else:
            checks["tesseract"] = {"status": "error", "message": "命令执行失败"}
    except FileNotFoundError:
        checks["tesseract"] = {"status": "error", "message": f"命令不存在: {TESSERACT_CMD}"}
    except subprocess.TimeoutExpired:
        checks["tesseract"] = {"status": "error", "message": "执行超时"}
    except Exception as e:
        checks["tesseract"] = {"status": "error", "message": str(e)}

    overall_status = "ok" if all(c["status"] == "ok" for c in checks.values()) else "degraded"

    return {
        "status": overall_status,
        "checks": checks,
    }

# ========== SPA 静态文件（必须在 /health 之后）==========

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """SPA 路由 fallback"""
        file_path = os.path.join(FRONTEND_DIST, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

# ========== 认证中间件==========

JWT_SECRET = os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """全局认证中间件，排除登录和健康检查端点."""
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/", "/favicon.ico", "/favicon.svg"] or \
       request.url.path.startswith("/api/v1/auth/") or \
       request.url.path.startswith("/api/v1/onlyoffice/") or \
       request.url.path.startswith("/assets/") or \
       request.url.path.startswith("/workflow") or \
       request.url.path.startswith("/dashboard") or \
       request.url.path.startswith("/phase2") or \
       request.url.path.startswith("/phase3") or \
       request.url.path.startswith("/data-center") or \
       request.url.path.startswith("/login") or \
       request.url.path.startswith("/api/v1/packaging/") or \
       request.url.path.startswith("/api/v1/packages/") or \
       request.url.path.startswith("/api/v1/merge/") or \
       request.url.path.startswith("/api/v1/msds") or \
       request.url.path.startswith("/api/v1/name-mapping") or \
       request.url.path.startswith("/api/v1/transport-reports") or \
       request.url.path.startswith("/api/v1/data-center") or \
       request.url.path.startswith("/documentserver"):
        return await call_next(request)

    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "未授权，请先登录"},
            headers={"Access-Control-Allow-Origin": request.headers.get("origin", "*")}
        )

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
            content={"detail": "无效的认证凭证"},
            headers={"Access-Control-Allow-Origin": request.headers.get("origin", "*")}
        )

    return await call_next(request)


@app.on_event("startup")
async def startup():
    """启动时加载品名对照表，全量扫描 MSDS 和运输鉴定报告目录，建立内存索引。"""
    load_name_mapping()
    print("[startup] Product name mapping loaded")
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
