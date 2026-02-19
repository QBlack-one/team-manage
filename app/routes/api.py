"""
API 路由
处理 AJAX 请求的 API 端点
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_admin
from app.services.team import team_service
from app.services.plus import plus_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/api",
    tags=["api"]
)


@router.get("/teams/refresh-all")
async def refresh_all_teams(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """批量刷新所有 Team 信息 (并发执行)"""
    try:
        logger.info("批量刷新所有 Team 信息")
        result = await team_service.sync_all_teams(db)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"批量刷新 Team 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"批量刷新 Team 失败: {str(e)}"}
        )


@router.get("/teams/{team_id}/refresh")
async def refresh_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """刷新单个 Team 信息"""
    try:
        logger.info(f"刷新 Team {team_id} 信息")

        result = await team_service.sync_team_info(team_id, db)

        if not result["success"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=result
            )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"刷新 Team 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": f"刷新 Team 失败: {str(e)}"
            }
        )


@router.post("/teams/retry-errors")
async def retry_error_teams(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """重试所有异常状态的 Team (重新同步)"""
    try:
        logger.info("重试所有异常 Team")
        result = await team_service.retry_error_teams(db)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"重试异常 Team 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"重试异常 Team 失败: {str(e)}"}
        )


# === Plus 账号 API ===


@router.get("/plus/refresh-all")
async def refresh_all_plus(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """批量刷新所有 Plus 账号信息 (并发执行)"""
    try:
        logger.info("批量刷新所有 Plus 账号信息")
        result = await plus_service.sync_all_plus(db)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"批量刷新 Plus 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"批量刷新 Plus 失败: {str(e)}"}
        )


@router.get("/plus/{plus_id}/refresh")
async def refresh_plus(
    plus_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """刷新单个 Plus 账号信息"""
    try:
        logger.info(f"刷新 Plus {plus_id} 信息")

        result = await plus_service.sync_plus_info(plus_id, db)

        if not result["success"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=result
            )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"刷新 Plus 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": f"刷新 Plus 失败: {str(e)}"
            }
        )


@router.post("/plus/retry-errors")
async def retry_error_plus(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """重试所有异常状态的 Plus 账号 (重新同步)"""
    try:
        logger.info("重试所有异常 Plus")
        result = await plus_service.retry_error_plus(db)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"重试异常 Plus 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"重试异常 Plus 失败: {str(e)}"}
        )
