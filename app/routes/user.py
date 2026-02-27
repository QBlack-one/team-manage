"""
用户路由
处理用户兑换页面和自助查询
"""
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    tags=["user"]
)

# 速率限制器
limiter = Limiter(key_func=get_remote_address)


# 请求模型
class UserQueryRequest(BaseModel):
    """用户查询请求"""
    email: EmailStr = Field(..., description="用户邮箱")


@router.get("/", response_class=HTMLResponse)
async def redeem_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    用户兑换页面

    Args:
        request: FastAPI Request 对象
        db: 数据库会话

    Returns:
        用户兑换页面 HTML
    """
    try:
        from app.main import templates
        from app.services.team import team_service

        remaining_spots = await team_service.get_total_available_spots(db)

        logger.info(f"用户访问兑换页面，剩余车位: {remaining_spots}")

        return templates.TemplateResponse(
            "user/redeem.html",
            {
                "request": request,
                "remaining_spots": remaining_spots
            }
        )

    except Exception as e:
        logger.error(f"渲染兑换页面失败: {e}")
        return HTMLResponse(
            content=f"<h1>页面加载失败</h1><p>{str(e)}</p>",
            status_code=500
        )


@router.get("/query", response_class=HTMLResponse)
async def query_page(request: Request):
    """用户自助查询页面"""
    try:
        from app.main import templates
        return templates.TemplateResponse(
            "user/query.html",
            {"request": request}
        )
    except Exception as e:
        logger.error(f"渲染查询页面失败: {e}")
        return HTMLResponse(
            content=f"<h1>页面加载失败</h1><p>{str(e)}</p>",
            status_code=500
        )


@router.post("/query")
@limiter.limit("5/minute")
async def query_records(
    request: Request,
    query_data: UserQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    查询用户兑换记录

    Args:
        request: FastAPI Request 对象
        query_data: 查询请求数据
        db: 数据库会话

    Returns:
        兑换记录列表
    """
    try:
        from app.services.user_query import user_query_service

        logger.info(f"用户查询兑换记录: {query_data.email}")

        result = await user_query_service.query_by_email(
            query_data.email,
            db
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )
