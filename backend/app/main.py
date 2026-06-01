from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.orders import router as orders_router
from app.api.v1.pi import router as pi_router
from app.api.v1.merge import router as merge_router
from app.api.v1.packages import router as packages_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1 import documents, msds, transport, export_codes, onlyoffice

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
app.include_router(dashboard_router)
app.include_router(documents.router)
app.include_router(msds.router)
app.include_router(transport.router)
app.include_router(export_codes.router)
app.include_router(onlyoffice.router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)