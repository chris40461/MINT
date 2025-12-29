"""API v1 router"""

from fastapi import APIRouter
from .stocks import router as stocks_router
from .triggers import router as triggers_router
from .analysis import router as analysis_router
from .reports import router as reports_router

# v1 라우터 생성
api_router = APIRouter(prefix="/api/v1")

# 서브 라우터 등록
api_router.include_router(stocks_router)
api_router.include_router(triggers_router)
api_router.include_router(analysis_router)
api_router.include_router(reports_router)

__all__ = ["api_router"]
