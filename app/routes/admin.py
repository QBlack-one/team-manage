"""
管理员路由
聚合所有管理员子路由，处理仪表盘页面
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_admin
from app.services.team import TeamService
from app.services.redemption import RedemptionService

# 导入子路由
from app.routes import admin_teams, admin_codes, admin_records, admin_settings

logger = logging.getLogger(__name__)

# 创建主路由器
router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# 注册子路由
router.include_router(admin_teams.router)
router.include_router(admin_codes.router)
router.include_router(admin_records.router)
router.include_router(admin_settings.router)

# 服务实例
team_service = TeamService()
redemption_service = RedemptionService()


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    管理员面板首页

    Args:
        request: FastAPI Request 对象
        db: 数据库会话
        current_user: 当前用户（需要登录）

    Returns:
        管理员面板首页 HTML
    """
    try:
        from app.main import templates

        logger.info("管理员访问控制台")

        # 获取所有 Team 列表
        teams_result = await team_service.get_all_teams(db)
        teams = teams_result.get("teams", [])

        # 获取兑换码统计
        codes_result = await redemption_service.get_all_codes(db)
        all_codes = codes_result.get("codes", [])

        # 计算统计数据
        stats = {
            "total_teams": len(teams),
            "available_teams": len([t for t in teams if t["status"] == "active" and t["current_members"] < t["max_members"]]),
            "total_codes": len(all_codes),
            "used_codes": len([c for c in all_codes if c["status"] == "used"])
        }

        return templates.TemplateResponse(
            "admin/index.html",
            {
                "request": request,
                "user": current_user,
                "active_page": "dashboard",
                "teams": teams,
                "stats": stats
            }
        )

    except Exception as e:
        logger.error(f"加载管理员面板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加载管理员面板失败: {str(e)}"
        )
