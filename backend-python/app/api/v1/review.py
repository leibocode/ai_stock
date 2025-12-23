from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_db
from app.schemas import success, error
from app.models import ReviewRecord
from app.utils.cache_decorator import with_cache

router = APIRouter(prefix="", tags=["复盘"])


@router.get("/review")
async def get_review(
    date: str = Query(None, description="交易日期YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db)
):
    """获取复盘记录"""
    if not date:
        return error("日期参数缺失")

    async def fetch_data():
        stmt = select(ReviewRecord).where(ReviewRecord.trade_date == date)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return {}

        return {
            "id": record.id,
            "trade_date": record.trade_date,
            "content": record.content,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    data = await with_cache(f"review:{date}", fetch_data, ttl=3600)
    return success(data)


@router.post("/review")
async def save_review(
    date: str = Query(None, description="交易日期YYYY-MM-DD"),
    content: str = Query(None, description="复盘内容"),
    db: AsyncSession = Depends(get_db)
):
    """保存复盘记录"""
    if not date or not content:
        return error("参数缺失")

    stmt = select(ReviewRecord).where(ReviewRecord.trade_date == date)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.content = content
        await db.merge(existing)
    else:
        new_record = ReviewRecord(trade_date=date, content=content)
        db.add(new_record)

    await db.commit()
    return success({"success": True})


@router.get("/review-history")
async def get_review_history(
    db: AsyncSession = Depends(get_db)
):
    """获取复盘历史"""
    async def fetch_data():
        stmt = (
            select(ReviewRecord)
            .order_by(desc(ReviewRecord.trade_date))
            .limit(20)
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "trade_date": r.trade_date,
                "preview": r.content[:50] if r.content else "",
            }
            for r in records
        ]

    data = await with_cache("review_history", fetch_data, ttl=3600)
    return success(data)
