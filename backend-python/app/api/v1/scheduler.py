"""
定时任务管理 API
允许用户查看、控制和监控定时任务的执行状态
"""
from fastapi import APIRouter
from loguru import logger
from app.schemas import success, error
from app.core.scheduler import get_scheduler

router = APIRouter(prefix="", tags=["定时任务"])


@router.get("/scheduler/jobs")
async def list_scheduler_jobs():
    """列出所有定时任务及其执行时间"""
    try:
        scheduler = get_scheduler()
        jobs = scheduler.list_jobs()

        return success({
            "total": len(jobs),
            "jobs": jobs,
            "message": "已加载所有定时任务"
        })

    except Exception as e:
        logger.error(f"Failed to list scheduler jobs: {e}")
        return error(f"获取任务列表失败: {str(e)}")


@router.post("/scheduler/pause/{job_id}")
async def pause_job(job_id: str):
    """暂停指定的定时任务

    Args:
        job_id: 任务 ID (sync_daily, calc_indicators, crawl_eastmoney, cache_warmup)
    """
    try:
        scheduler = get_scheduler()
        scheduler.pause_job(job_id)

        return success({
            "job_id": job_id,
            "status": "paused",
            "message": f"任务 {job_id} 已暂停"
        })

    except Exception as e:
        logger.error(f"Failed to pause job {job_id}: {e}")
        return error(f"暂停任务失败: {str(e)}")


@router.post("/scheduler/resume/{job_id}")
async def resume_job(job_id: str):
    """恢复指定的定时任务

    Args:
        job_id: 任务 ID (sync_daily, calc_indicators, crawl_eastmoney, cache_warmup)
    """
    try:
        scheduler = get_scheduler()
        scheduler.resume_job(job_id)

        return success({
            "job_id": job_id,
            "status": "resumed",
            "message": f"任务 {job_id} 已恢复"
        })

    except Exception as e:
        logger.error(f"Failed to resume job {job_id}: {e}")
        return error(f"恢复任务失败: {str(e)}")


@router.get("/scheduler/status")
async def get_scheduler_status():
    """获取调度器运行状态"""
    try:
        scheduler = get_scheduler()
        jobs = scheduler.list_jobs()

        return success({
            "running": scheduler.scheduler.running,
            "total_jobs": len(jobs),
            "jobs": jobs,
            "description": {
                "sync_daily": "15:30 - 同步日线行情",
                "calc_indicators": "16:00 - 计算技术指标",
                "crawl_eastmoney": "16:30 - 爬取东方财富数据",
                "cache_warmup": "18:00 - 缓存预热"
            }
        })

    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        return error(f"获取调度器状态失败: {str(e)}")


@router.post("/scheduler/run-now/{job_id}")
async def run_job_now(job_id: str):
    """立即执行指定的定时任务（用于测试）

    Args:
        job_id: 任务 ID
    """
    try:
        scheduler = get_scheduler()
        job = scheduler.scheduler.get_job(job_id)

        if not job:
            return error(f"任务不存在: {job_id}")

        # 立即执行任务
        await job.func()

        return success({
            "job_id": job_id,
            "status": "executed",
            "message": f"任务 {job_id} 已立即执行"
        })

    except Exception as e:
        logger.error(f"Failed to run job {job_id} now: {e}")
        return error(f"执行任务失败: {str(e)}")
