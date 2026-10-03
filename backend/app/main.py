from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import router as api_v1_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LegalGPT Enterprise API",
    version="1.0.0",
    description="AI-powered contract intelligence platform"
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception while handling %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred."}
    )

from app.core.config import settings

# Parse allowed origins from settings
allowed_origins_raw = getattr(settings, "ALLOWED_ORIGINS", "")
if not allowed_origins_raw:
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Mount API routers
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "online", "application": "LegalGPT Enterprise API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
