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
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred."}
    )

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "online", "application": "LegalGPT Enterprise API"}
