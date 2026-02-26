"""
使用记录路由
查看 Team 和 Plus 的兑换记录
"""
import logging
import math
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models import RedemptionCode
from app.utils.time_utils import get_now

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(tags=["admin-records"])

PER_PAGE = 20


@router.get("/records", response_class=HTMLResponse)
async def records_page(
    request: Request,
    email: Optional[str] = None,
    code: Optional[str] = None,
    page: Optional[str] = "1",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """使用记录页面 - 展示所有已使用的兑换码（Team + Plus）"""
    try:
        from app.main import templates

        # 解析页码
        try:
            page_int = int(page) if page and page.strip() else 1
        except (ValueError, TypeError):
            page_int = 1
        if page_int < 1:
            page_int = 1

        # --- 构建筛选条件 ---
        filters = [RedemptionCode.status == "used"]
        if email and email.strip():
            filters.append(RedemptionCode.used_by_email.ilike(f"%{email.strip()}%"))
        if code and code.strip():
            filters.append(RedemptionCode.code.ilike(f"%{code.strip()}%"))

        where_clause = and_(*filters)

        # --- 统计数据 ---
        now = get_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 总数
        total_stmt = select(func.count()).select_from(RedemptionCode).where(where_clause)
        total_result = await db.execute(total_stmt)
        total_records = total_result.scalar() or 0

        # 今日
        today_stmt = select(func.count()).select_from(RedemptionCode).where(
            and_(where_clause, RedemptionCode.used_at >= today_start)
        )
        today_result = await db.execute(today_stmt)
        today_count = today_result.scalar() or 0

        # Team / Plus 分类统计
        team_stmt = select(func.count()).select_from(RedemptionCode).where(
            and_(where_clause, RedemptionCode.code_type == "team")
        )
        team_result = await db.execute(team_stmt)
        team_count = team_result.scalar() or 0

        plus_stmt = select(func.count()).select_from(RedemptionCode).where(
            and_(where_clause, RedemptionCode.code_type == "plus")
        )
        plus_result = await db.execute(plus_stmt)
        plus_count = plus_result.scalar() or 0

        stats = {
            "total": total_records,
            "today": today_count,
            "team_count": team_count,
            "plus_count": plus_count
        }

        # --- 分页查询 ---
        total_pages = math.ceil(total_records / PER_PAGE) if total_records > 0 else 1
        if page_int > total_pages:
            page_int = total_pages

        offset = (page_int - 1) * PER_PAGE

        records_stmt = (
            select(RedemptionCode)
            .where(where_clause)
            .order_by(RedemptionCode.used_at.desc())
            .limit(PER_PAGE)
            .offset(offset)
        )
        records_result = await db.execute(records_stmt)
        records = records_result.scalars().all()

        # 格式化记录
        record_list = []
        for r in records:
            record_list.append({
                "email": r.used_by_email or "-",
                "code": r.code,
                "code_type": r.code_type or "team",
                "used_at": r.used_at.strftime("%Y-%m-%d %H:%M:%S") if r.used_at else "-"
            })

        return templates.TemplateResponse(
            "admin/records/index.html",
            {
                "request": request,
                "user": current_user,
                "active_page": "records",
                "records": record_list,
                "stats": stats,
                "filters": {
                    "email": email,
                    "code": code
                },
                "pagination": {
                    "current_page": page_int,
                    "total_pages": total_pages,
                    "total": total_records,
                    "per_page": PER_PAGE
                }
            }
        )

    except Exception as e:
        logger.error(f"获取使用记录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取使用记录失败: {str(e)}"
        )
