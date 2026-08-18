from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.chat import router as chat_router
from app.api.v1.users import router as users_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.history import router as history_router
from app.api.v1.search import router as search_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
router.include_router(history_router, prefix="/history", tags=["history"])
router.include_router(search_router, prefix="/search", tags=["search"])
