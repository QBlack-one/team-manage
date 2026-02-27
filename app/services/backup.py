"""
数据库备份服务
定时或手动备份 SQLite 数据库到本地目录
"""
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from app.config import settings

logger = logging.getLogger(__name__)

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# 备份目录
BACKUP_DIR = BASE_DIR / "data" / "backups"


class BackupService:
    """数据库备份服务类"""

    def __init__(self):
        """初始化备份服务"""
        # 确保备份目录存在
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def _get_db_path(self) -> Path:
        """
        从数据库 URL 中提取 SQLite 文件路径

        Returns:
            数据库文件 Path 对象
        """
        # sqlite+aiosqlite:///./data/team_manage.db
        db_url = settings.database_url
        if "sqlite" not in db_url:
            raise RuntimeError("自动备份仅支持 SQLite 数据库")
        db_file = db_url.split("///")[-1]
        return Path(db_file).resolve()

    def create_backup(self) -> Dict[str, Any]:
        """
        创建数据库备份

        Returns:
            结果字典，包含 success, filename, size, message, error
        """
        try:
            db_path = self._get_db_path()

            if not db_path.exists():
                return {
                    "success": False,
                    "filename": None,
                    "size": 0,
                    "message": None,
                    "error": f"数据库文件不存在: {db_path}"
                }

            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"team_manage_{timestamp}.db"
            backup_path = BACKUP_DIR / backup_filename

            # 复制数据库文件
            shutil.copy2(str(db_path), str(backup_path))

            file_size = backup_path.stat().st_size

            logger.info(f"数据库备份成功: {backup_filename} ({file_size} bytes)")

            return {
                "success": True,
                "filename": backup_filename,
                "size": file_size,
                "message": f"备份成功: {backup_filename}",
                "error": None
            }

        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return {
                "success": False,
                "filename": None,
                "size": 0,
                "message": None,
                "error": f"备份失败: {str(e)}"
            }

    def cleanup_old_backups(self, keep: int = 10) -> Dict[str, Any]:
        """
        清理旧备份，保留最近 N 个

        Args:
            keep: 保留的备份数量

        Returns:
            结果字典
        """
        try:
            backups = sorted(
                BACKUP_DIR.glob("team_manage_*.db"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            deleted_count = 0
            for old_backup in backups[keep:]:
                old_backup.unlink()
                deleted_count += 1

            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个旧备份，保留最近 {keep} 个")

            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"清理了 {deleted_count} 个旧备份"
            }

        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
            return {"success": False, "deleted_count": 0, "error": str(e)}

    def list_backups(self) -> Dict[str, Any]:
        """
        列出所有备份文件

        Returns:
            结果字典，包含 success, backups (备份列表), error
        """
        try:
            backups = sorted(
                BACKUP_DIR.glob("team_manage_*.db"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            backup_list = []
            for f in backups:
                stat = f.stat()
                # 文件大小转为可读格式
                size_mb = stat.st_size / (1024 * 1024)
                backup_list.append({
                    "filename": f.name,
                    "size": stat.st_size,
                    "size_display": f"{size_mb:.2f} MB",
                    "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })

            return {
                "success": True,
                "backups": backup_list,
                "total": len(backup_list),
                "error": None
            }

        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return {"success": False, "backups": [], "total": 0, "error": str(e)}

    def restore_backup(self, filename: str) -> Dict[str, Any]:
        """
        恢复指定备份

        Args:
            filename: 备份文件名

        Returns:
            结果字典
        """
        try:
            backup_path = BACKUP_DIR / filename

            if not backup_path.exists():
                return {
                    "success": False,
                    "message": None,
                    "error": f"备份文件不存在: {filename}"
                }

            db_path = self._get_db_path()

            # 先备份当前数据库（防止恢复失败丢失数据）
            safety_backup = BACKUP_DIR / f"before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(str(db_path), str(safety_backup))

            # 恢复备份
            shutil.copy2(str(backup_path), str(db_path))

            logger.info(f"数据库已恢复到备份: {filename}")

            return {
                "success": True,
                "message": f"数据库已恢复到备份: {filename}（恢复前的数据已自动备份为 {safety_backup.name}）",
                "error": None
            }

        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return {"success": False, "message": None, "error": f"恢复失败: {str(e)}"}


# 创建全局实例
backup_service = BackupService()
