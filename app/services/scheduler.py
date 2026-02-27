"""
调度器服务
使用 APScheduler 管理定时任务（Team 自动同步、数据库自动备份）
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import AsyncSessionLocal
from app.utils.time_utils import get_now

logger = logging.getLogger(__name__)


class SchedulerService:
    """调度器服务类"""

    def __init__(self):
        """初始化调度器"""
        self.scheduler = AsyncIOScheduler()
        self._running = False

    async def _sync_all_teams_job(self):
        """定时同步所有 Team 状态（调度器回调）"""
        logger.info("[调度器] 开始自动同步所有 Team...")
        try:
            # 延迟导入避免循环依赖
            from app.services.team import team_service

            async with AsyncSessionLocal() as session:
                result = await team_service.sync_all_teams(session)
                if result["success"]:
                    logger.info(
                        f"[调度器] 自动同步完成: "
                        f"总数 {result['total']}, "
                        f"成功 {result['success_count']}, "
                        f"失败 {result['failed_count']}"
                    )
                else:
                    logger.error(f"[调度器] 自动同步失败: {result['error']}")
        except Exception as e:
            logger.error(f"[调度器] 自动同步异常: {e}")

    async def _backup_db_job(self):
        """定时备份数据库（调度器回调）"""
        logger.info("[调度器] 开始自动备份数据库...")
        try:
            from app.services.backup import backup_service

            result = backup_service.create_backup()
            if result["success"]:
                logger.info(f"[调度器] 自动备份成功: {result['filename']}")
                # 清理旧备份，保留最近 10 个
                backup_service.cleanup_old_backups(keep=10)
            else:
                logger.error(f"[调度器] 自动备份失败: {result['error']}")
        except Exception as e:
            logger.error(f"[调度器] 自动备份异常: {e}")

    async def start(self):
        """
        启动调度器并注册定时任务
        从数据库 settings 表读取配置
        """
        if self._running:
            logger.warning("[调度器] 已在运行中，跳过启动")
            return

        try:
            # 读取配置
            from app.services.settings import settings_service

            async with AsyncSessionLocal() as session:
                sync_enabled = await settings_service.get_setting(session, "scheduler_sync_enabled", "true")
                sync_hours = await settings_service.get_setting(session, "scheduler_sync_hours", "6")
                backup_enabled = await settings_service.get_setting(session, "scheduler_backup_enabled", "true")
                backup_hours = await settings_service.get_setting(session, "scheduler_backup_hours", "24")

            # 注册 Team 自动同步任务
            if sync_enabled.lower() == "true":
                hours = max(1, int(sync_hours))
                self.scheduler.add_job(
                    self._sync_all_teams_job,
                    trigger=IntervalTrigger(hours=hours),
                    id="sync_all_teams",
                    name="自动同步所有 Team",
                    replace_existing=True
                )
                logger.info(f"[调度器] Team 自动同步已启用，间隔 {hours} 小时")
            else:
                logger.info("[调度器] Team 自动同步已禁用")

            # 注册数据库自动备份任务
            if backup_enabled.lower() == "true":
                hours = max(1, int(backup_hours))
                self.scheduler.add_job(
                    self._backup_db_job,
                    trigger=IntervalTrigger(hours=hours),
                    id="backup_db",
                    name="自动备份数据库",
                    replace_existing=True
                )
                logger.info(f"[调度器] 自动备份已启用，间隔 {hours} 小时")
            else:
                logger.info("[调度器] 自动备份已禁用")

            self.scheduler.start()
            self._running = True
            logger.info("[调度器] 启动成功")

        except Exception as e:
            logger.error(f"[调度器] 启动失败: {e}")

    async def stop(self):
        """停止调度器"""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("[调度器] 已停止")

    async def reload_config(self):
        """重新加载配置并重启调度器"""
        await self.stop()
        # 创建新的调度器实例（APScheduler shutdown 后不能直接 restart）
        self.scheduler = AsyncIOScheduler()
        await self.start()

    def get_status(self):
        """
        获取调度器状态

        Returns:
            状态字典
        """
        jobs = []
        if self._running:
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "-",
                    "trigger": str(job.trigger)
                })

        return {
            "running": self._running,
            "jobs": jobs
        }


# 创建全局实例
scheduler_service = SchedulerService()
