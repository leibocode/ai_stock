from fastapi import APIRouter
from . import market, limit, fund_flow, pattern, review, sync, crawler, chan, scheduler

# 创建API路由聚合器
api_router = APIRouter()

# 注册所有路由模块
api_router.include_router(market.router)
api_router.include_router(limit.router)
api_router.include_router(fund_flow.router)
api_router.include_router(pattern.router)
api_router.include_router(review.router)
api_router.include_router(sync.router)
api_router.include_router(crawler.router)
api_router.include_router(chan.router)
api_router.include_router(scheduler.router)  # 定时任务管理 API

__all__ = ["api_router"]
