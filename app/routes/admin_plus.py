"""
Plus 账号管理路由
处理 Plus 账号的导入、删除
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.dependencies.auth import require_admin
from app.services.plus import plus_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(tags=["admin-plus"])


# 请求模型
class PlusImportRequest(BaseModel):
    """Plus 导入请求"""
    import_type: str = Field(..., description="导入类型: single 或 batch")
    email: Optional[str] = Field(None, description="邮箱 (单个导入)")
    password: Optional[str] = Field(None, description="密码 (单个导入)")
    verify_url: Optional[str] = Field(None, description="接码链接 (单个导入)")
    content: Optional[str] = Field(None, description="批量导入内容")


@router.get("/plus", response_class=HTMLResponse)
async def plus_list_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Plus 账号管理页面"""
    try:
        from app.main import templates

        logger.info("管理员访问 Plus 管理页面")

        plus_result = await plus_service.get_all_plus(db)
        accounts = plus_result.get("accounts", [])

        stats = {
            "total": len(accounts),
            "unused": len([a for a in accounts if a["status"] == "unused"]),
            "used": len([a for a in accounts if a["status"] == "used"]),
        }

        return templates.TemplateResponse(
            "admin/plus/index.html",
            {
                "request": request,
                "user": current_user,
                "active_page": "plus",
                "accounts": accounts,
                "stats": stats
            }
        )

    except Exception as e:
        logger.error(f"加载 Plus 管理页面失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加载 Plus 管理页面失败: {str(e)}"
        )


@router.post("/plus/import")
async def plus_import(
    import_data: PlusImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """处理 Plus 账号导入"""
    try:
        logger.info(f"管理员导入 Plus: {import_data.import_type}")

        if import_data.import_type == "single":
            if not import_data.email or not import_data.password:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"success": False, "error": "邮箱和密码不能为空"}
                )

            result = await plus_service.import_plus_single(
                email=import_data.email,
                password=import_data.password,
                db_session=db,
                verify_url=import_data.verify_url
            )

            if not result["success"]:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=result
                )
            return JSONResponse(content=result)

        elif import_data.import_type == "batch":
            if not import_data.content:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"success": False, "error": "批量导入内容不能为空"}
                )

            result = await plus_service.import_plus_batch(
                text=import_data.content,
                db_session=db
            )
            return JSONResponse(content=result)

        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "无效的导入类型"}
            )

    except Exception as e:
        logger.error(f"导入 Plus 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"导入失败: {str(e)}"}
        )


@router.post("/plus/{plus_id}/delete")
async def delete_plus(
    plus_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """删除 Plus 账号"""
    try:
        logger.info(f"管理员删除 Plus: {plus_id}")
        result = await plus_service.delete_plus(plus_id, db)

        if not result["success"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=result
            )
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"删除 Plus 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"删除 Plus 失败: {str(e)}"}
        )


@router.post("/plus/used/delete-all")
async def delete_used_plus(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """批量删除所有已使用的 Plus 账号"""
    try:
        logger.info("管理员批量删除已使用 Plus")
        result = await plus_service.delete_used_plus(db)

        if not result["success"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=result
            )
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"批量删除已使用 Plus 失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"批量删除失败: {str(e)}"}
        )
