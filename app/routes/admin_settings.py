"""
系统设置路由
处理系统配置的查看和修改
"""
import logging
import time
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from curl_cffi.requests import AsyncSession as CurlAsyncSession

from app.database import get_db
from app.dependencies.auth import require_admin


logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(tags=["admin-settings"])


# 请求模型
class ProxyConfigRequest(BaseModel):
    """代理配置请求"""
    enabled: bool = Field(..., description="是否启用代理")
    proxy: str = Field("", description="代理地址")


class ProxyTestRequest(BaseModel):
    """代理测试请求"""
    proxies: str = Field("", description="代理地址列表")


class LogLevelRequest(BaseModel):
    """日志级别请求"""
    level: str = Field(..., description="日志级别")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """系统设置页面"""
    try:
        from app.main import templates
        from app.services.settings import settings_service

        logger.info("管理员访问系统设置页面")

        proxy_config = await settings_service.get_proxy_config(db)
        log_level = await settings_service.get_log_level(db)

        return templates.TemplateResponse(
            "admin/settings/index.html",
            {
                "request": request,
                "user": current_user,
                "active_page": "settings",
                "proxy_enabled": proxy_config["enabled"],
                "proxy": proxy_config["proxy"],
                "log_level": log_level
            }
        )

    except Exception as e:
        logger.error(f"获取系统设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统设置失败: {str(e)}"
        )


@router.post("/settings/proxy")
async def update_proxy_config(
    proxy_data: ProxyConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """更新代理配置"""
    try:
        from app.services.settings import settings_service

        logger.info(f"管理员更新代理配置: enabled={proxy_data.enabled}, proxy={proxy_data.proxy}")

        # 验证代理地址格式
        if proxy_data.enabled and proxy_data.proxy:
            proxy = proxy_data.proxy.strip()
            if not (proxy.startswith("http://") or proxy.startswith("https://") or proxy.startswith("socks5://")):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "success": False,
                        "error": "代理地址格式错误,应为 http://host:port 或 socks5://host:port"
                    }
                )

        success = await settings_service.update_proxy_config(
            db,
            proxy_data.enabled,
            proxy_data.proxy.strip() if proxy_data.proxy else ""
        )

        if success:
            return JSONResponse(content={"success": True, "message": "代理配置已保存"})
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"success": False, "error": "保存失败"}
            )

    except Exception as e:
        logger.error(f"更新代理配置失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"更新失败: {str(e)}"}
        )


@router.post("/settings/log-level")
async def update_log_level(
    log_data: LogLevelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """更新日志级别"""
    try:
        from app.services.settings import settings_service

        logger.info(f"管理员更新日志级别: {log_data.level}")

        success = await settings_service.update_log_level(db, log_data.level)

        if success:
            return JSONResponse(content={"success": True, "message": "日志级别已保存"})
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "无效的日志级别"}
            )

    except Exception as e:
        logger.error(f"更新日志级别失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"更新失败: {str(e)}"}
        )


@router.post("/settings/proxy/test")
async def test_proxies(
    request: ProxyTestRequest,
    current_user: dict = Depends(require_admin)
):
    """测试代理连通性"""
    try:
        proxies_text = request.proxies
        proxy_list = [
            p.strip() for p in proxies_text.replace(',', '\n').split('\n') if p.strip()
        ]
        
        if not proxy_list:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "没有提供可测试的代理地址"}
            )

        async def check_proxy(proxy: str):
            start_time = time.time()
            try:
                # 设定8秒超时，尝试访问 ChatGPT 以确认连通性
                async with CurlAsyncSession(
                    impersonate="chrome", 
                    proxies={"http": proxy, "https": proxy}, 
                    timeout=8
                ) as s:
                    # 获取主页，任何 HTTP 状态码（比如 403 / 401 / 200）都说明能连上目标服务器
                    resp = await s.get("https://chatgpt.com/")
                    latency = int((time.time() - start_time) * 1000)
                    return {
                        "proxy": proxy, 
                        "status": "success", 
                        "latency": latency, 
                        "http_status": resp.status_code
                    }
            except Exception as e:
                err_msg = str(e)
                if len(err_msg) > 50:
                    err_msg = err_msg[:47] + "..."
                return {
                    "proxy": proxy, 
                    "status": "error", 
                    "error": err_msg or "Timeout or connection error"
                }

        # 并发测试所有代理
        tasks = [check_proxy(p) for p in proxy_list]
        check_results = await asyncio.gather(*tasks)
        
        return JSONResponse(content={"success": True, "results": check_results})

    except Exception as e:
        logger.error(f"测试代理失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"测试异常: {str(e)}"}
        )


# ============ 定时任务调度器 ============

class SchedulerConfigRequest(BaseModel):
    """调度器配置请求"""
    sync_enabled: bool = Field(True, description="是否启用自动同步")
    sync_hours: int = Field(6, description="同步间隔（小时）", ge=1, le=168)
    backup_enabled: bool = Field(True, description="是否启用自动备份")
    backup_hours: int = Field(24, description="备份间隔（小时）", ge=1, le=168)


@router.get("/settings/scheduler/status")
async def scheduler_status(
    current_user: dict = Depends(require_admin)
):
    """获取调度器运行状态"""
    try:
        from app.services.scheduler import scheduler_service
        return JSONResponse(content={
            "success": True,
            **scheduler_service.get_status()
        })
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.post("/settings/scheduler")
async def update_scheduler_config(
    config: SchedulerConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """更新调度器配置并重启"""
    try:
        from app.services.settings import settings_service
        from app.services.scheduler import scheduler_service

        logger.info(f"管理员更新调度器配置: sync={config.sync_enabled}/{config.sync_hours}h, backup={config.backup_enabled}/{config.backup_hours}h")

        settings_dict = {
            "scheduler_sync_enabled": str(config.sync_enabled).lower(),
            "scheduler_sync_hours": str(config.sync_hours),
            "scheduler_backup_enabled": str(config.backup_enabled).lower(),
            "scheduler_backup_hours": str(config.backup_hours),
        }
        success = await settings_service.update_settings(db, settings_dict)

        if success:
            await scheduler_service.reload_config()
            return JSONResponse(content={"success": True, "message": "调度器配置已更新并重启"})
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"success": False, "error": "保存配置失败"}
            )

    except Exception as e:
        logger.error(f"更新调度器配置失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"更新失败: {str(e)}"}
        )


# ============ 数据库备份 ============

@router.get("/settings/backups")
async def list_backups(
    current_user: dict = Depends(require_admin)
):
    """列出所有数据库备份"""
    try:
        from app.services.backup import backup_service
        result = backup_service.list_backups()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.post("/settings/backup/create")
async def create_backup(
    current_user: dict = Depends(require_admin)
):
    """手动创建数据库备份"""
    try:
        from app.services.backup import backup_service

        logger.info("管理员手动创建数据库备份")
        result = backup_service.create_backup()

        if result["success"]:
            backup_service.cleanup_old_backups(keep=10)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"创建备份失败: {str(e)}"}
        )


class RestoreBackupRequest(BaseModel):
    """恢复备份请求"""
    filename: str = Field(..., description="备份文件名")


@router.post("/settings/backup/restore")
async def restore_backup(
    data: RestoreBackupRequest,
    current_user: dict = Depends(require_admin)
):
    """恢复指定数据库备份"""
    try:
        from app.services.backup import backup_service

        logger.info(f"管理员恢复数据库备份: {data.filename}")
        result = backup_service.restore_backup(data.filename)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"恢复失败: {str(e)}"}
        )
