"""
Plus 账号管理服务
用于管理 Plus 账号的导入、分配等功能
"""
import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PlusAccount
from app.utils.time_utils import get_now

logger = logging.getLogger(__name__)


def _parse_plus_line(line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    智能解析一行 Plus 账号数据，支持多种格式：
    1. Tab 分隔 (Excel 粘贴)
    2. ---- 分隔
    3. 无分隔符的拼接文本 (通过 email 和 URL 模式智能识别)

    Returns:
        (email, password, verify_url) 或 (None, None, None) 解析失败
    """
    line = line.strip()
    if not line:
        return None, None, None

    # 1. Tab 分隔
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) >= 4:
            return parts[1], parts[2], parts[3]
        elif len(parts) == 3:
            return parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            return parts[0], parts[1], ""
        return None, None, None

    # 2. ---- 分隔
    if "----" in line:
        parts = [p.strip() for p in line.split("----") if p.strip()]
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            return parts[0], parts[1], ""
        return None, None, None

    # 3. 智能正则解析 (无分隔符的拼接文本)
    # 提取 email: 匹配 xxx@xxx.com/net/org 等
    email_match = re.match(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,})', line)
    if not email_match:
        return None, None, None

    email = email_match.group(1)
    rest = line[email_match.end():]

    # 在剩余部分中查找 URL (www. 或 http 开头)
    url_match = re.search(r'((?:https?://|www\.)\S+)', rest)
    if url_match:
        password = rest[:url_match.start()].strip()
        verify_url = url_match.group(1)
    else:
        # 没有 URL，剩余全部当作密码
        password = rest.strip()
        verify_url = ""

    if not password:
        return None, None, None

    return email, password, verify_url


class PlusService:
    """Plus 账号管理服务类"""

    async def import_plus_single(
        self,
        email: str,
        password: str,
        db_session: AsyncSession,
        verify_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        单个导入 Plus 账号

        Args:
            email: 账号邮箱
            password: 账号密码
            db_session: 数据库会话
            verify_url: 接码链接 (可选)

        Returns:
            结果字典
        """
        try:
            # 检查是否已存在
            stmt = select(PlusAccount).where(PlusAccount.email == email)
            result = await db_session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                return {
                    "success": False,
                    "error": f"该 Plus 账号已存在 (ID: {existing.id})"
                }

            plus_account = PlusAccount(
                email=email,
                password=password,
                verify_url=verify_url or "",
                status="unused"
            )

            db_session.add(plus_account)
            await db_session.commit()

            logger.info(f"Plus 导入成功: {email}")

            return {
                "success": True,
                "plus_id": plus_account.id,
                "message": "Plus 导入成功"
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(f"Plus 导入失败: {e}")
            return {"success": False, "error": f"导入失败: {str(e)}"}

    async def import_plus_batch(
        self,
        text: str,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        批量导入 Plus 账号
        每行格式: 邮箱----密码----接码链接

        Args:
            text: 批量导入文本
            db_session: 数据库会话

        Returns:
            结果字典
        """
        try:
            lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

            if not lines:
                return {
                    "success": False,
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "results": [],
                    "error": "未找到有效内容"
                }

            results = []
            success_count = 0
            failed_count = 0

            for line in lines:
                # 使用智能解析函数
                email, password, verify_url = _parse_plus_line(line)

                if email is None:
                    failed_count += 1
                    results.append({
                        "email": line[:50],
                        "success": False,
                        "error": "格式错误，无法解析邮箱和密码"
                    })
                    continue

                if not email or not password:
                    failed_count += 1
                    results.append({
                        "email": email or "空",
                        "success": False,
                        "error": "邮箱或密码为空"
                    })
                    continue

                result = await self.import_plus_single(
                    email=email,
                    password=password,
                    db_session=db_session,
                    verify_url=verify_url
                )

                results.append({
                    "email": email,
                    "success": result["success"],
                    "message": result.get("message"),
                    "error": result.get("error")
                })

                if result["success"]:
                    success_count += 1
                else:
                    failed_count += 1

            logger.info(f"批量导入完成: 总数 {len(lines)}, 成功 {success_count}, 失败 {failed_count}")

            return {
                "success": True,
                "total": len(lines),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
                "error": None
            }

        except Exception as e:
            logger.error(f"批量导入失败: {e}")
            return {
                "success": False,
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
                "results": [],
                "error": f"批量导入失败: {str(e)}"
            }

    async def allocate_plus(
        self,
        code: str,
        user_email: str,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        分配一个未使用的 Plus 账号（兑换时调用）

        Args:
            code: 兑换码
            user_email: 使用者邮箱
            db_session: 数据库会话

        Returns:
            结果字典，包含 Plus 账号信息
        """
        try:
            # 查找未使用的 Plus 账号（按创建时间排序，先进先出）
            stmt = select(PlusAccount).where(
                PlusAccount.status == "unused"
            ).order_by(PlusAccount.id.asc()).limit(1)
            result = await db_session.execute(stmt)
            plus_account = result.scalar_one_or_none()

            if not plus_account:
                return {
                    "success": False,
                    "error": "没有可用的 Plus 账号"
                }

            # 标记为已使用
            plus_account.status = "used"
            plus_account.used_by_code = code
            plus_account.used_by_email = user_email
            plus_account.used_at = get_now()

            logger.info(f"Plus 分配成功: {plus_account.email} -> 兑换码 {code}")

            return {
                "success": True,
                "plus_id": plus_account.id,
                "plus_info": {
                    "email": plus_account.email,
                    "password": plus_account.password,
                    "verify_url": plus_account.verify_url
                },
                "message": "Plus 账号分配成功"
            }

        except Exception as e:
            logger.error(f"Plus 分配失败: {e}")
            return {"success": False, "error": f"分配失败: {str(e)}"}

    async def get_all_plus(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """获取所有 Plus 账号列表"""
        try:
            stmt = select(PlusAccount).order_by(PlusAccount.created_at.desc())
            result = await db_session.execute(stmt)
            accounts = result.scalars().all()

            account_list = []
            for account in accounts:
                account_list.append({
                    "id": account.id,
                    "email": account.email,
                    "password": account.password,
                    "verify_url": account.verify_url,
                    "status": account.status,
                    "used_by_code": account.used_by_code,
                    "used_by_email": account.used_by_email,
                    "used_at": account.used_at.isoformat() if account.used_at else None,
                    "created_at": account.created_at.isoformat() if account.created_at else None
                })

            return {
                "success": True,
                "accounts": account_list,
                "error": None
            }

        except Exception as e:
            logger.error(f"获取 Plus 列表失败: {e}")
            return {"success": False, "accounts": [], "error": str(e)}

    async def delete_plus(
        self,
        plus_id: int,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """删除单个 Plus 账号"""
        try:
            stmt = select(PlusAccount).where(PlusAccount.id == plus_id)
            result = await db_session.execute(stmt)
            plus_account = result.scalar_one_or_none()

            if not plus_account:
                return {"success": False, "error": f"Plus 账号 ID {plus_id} 不存在"}

            await db_session.delete(plus_account)
            await db_session.commit()

            logger.info(f"删除 Plus {plus_id} 成功")
            return {"success": True, "message": "Plus 账号已删除"}

        except Exception as e:
            await db_session.rollback()
            logger.error(f"删除 Plus 失败: {e}")
            return {"success": False, "error": f"删除失败: {str(e)}"}

    async def delete_used_plus(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """批量删除所有已使用的 Plus 账号"""
        try:
            stmt = select(PlusAccount).where(PlusAccount.status == "used")
            result = await db_session.execute(stmt)
            used_accounts = result.scalars().all()

            if not used_accounts:
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": "没有已使用的 Plus 账号"
                }

            deleted_count = len(used_accounts)
            for account in used_accounts:
                await db_session.delete(account)

            await db_session.commit()

            logger.info(f"批量删除 {deleted_count} 个已使用 Plus 成功")
            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"已删除 {deleted_count} 个已使用的 Plus 账号"
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(f"批量删除已使用 Plus 失败: {e}")
            return {"success": False, "error": f"批量删除失败: {str(e)}"}


# 创建全局 Plus 服务实例
plus_service = PlusService()
