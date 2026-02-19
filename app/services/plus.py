"""
Plus 账号管理服务
用于管理 ChatGPT Plus 账号的导入、同步等功能
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PlusAccount
from app.services.chatgpt import ChatGPTService
from app.services.encryption import encryption_service
from app.utils.token_parser import TokenParser
from app.utils.jwt_parser import JWTParser
from app.utils.time_utils import get_now

logger = logging.getLogger(__name__)


class PlusService:
    """Plus 账号管理服务类"""

    def __init__(self):
        """初始化 Plus 账号管理服务"""
        self.chatgpt_service = ChatGPTService()
        self.token_parser = TokenParser()
        self.jwt_parser = JWTParser()

    async def import_plus_single(
        self,
        access_token: str,
        db_session: AsyncSession,
        email: Optional[str] = None,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        单个导入 Plus 账号

        Args:
            access_token: AT Token
            db_session: 数据库会话
            email: 邮箱 (可选,如果不提供则从 Token 中提取)
            account_id: Account ID (可选,如果不提供则从 API 获取)

        Returns:
            结果字典,包含 success, plus_id, message, error
        """
        try:
            # 1. 如果没有提供邮箱,从 Token 中提取
            if not email:
                email = self.jwt_parser.extract_email(access_token)
                if not email:
                    return {
                        "success": False,
                        "plus_id": None,
                        "message": None,
                        "error": "无法从 Token 中提取邮箱,请手动提供邮箱"
                    }

            # 2. 调用 ChatGPT API 获取账户信息
            account_result = await self.chatgpt_service.get_plus_account_info(
                access_token,
                db_session
            )

            if not account_result["success"]:
                return {
                    "success": False,
                    "plus_id": None,
                    "message": None,
                    "error": f"获取账户信息失败: {account_result['error']}"
                }

            plus_accounts = account_result["accounts"]
            all_plan_types = account_result.get("all_plan_types", [])

            if not plus_accounts:
                if all_plan_types:
                    return {
                        "success": False,
                        "plus_id": None,
                        "message": None,
                        "error": f"该 Token 没有关联任何 Plus 账户 (发现的账户类型: {', '.join(all_plan_types)})"
                    }
                return {
                    "success": False,
                    "plus_id": None,
                    "message": None,
                    "error": "该 Token 没有关联任何 Plus 账户"
                }

            # 3. 选择要使用的 account_id
            selected_account = None

            if account_id:
                for acc in plus_accounts:
                    if acc["account_id"] == account_id:
                        selected_account = acc
                        break

                if not selected_account:
                    return {
                        "success": False,
                        "plus_id": None,
                        "message": None,
                        "error": f"指定的 account_id {account_id} 不存在"
                    }
            else:
                # 默认使用第一个活跃的账户
                for acc in plus_accounts:
                    if acc["has_active_subscription"]:
                        selected_account = acc
                        break

                # 如果没有活跃的,使用第一个
                if not selected_account:
                    selected_account = plus_accounts[0]

            # 4. 解析过期时间
            expires_at = None
            raw_expires = selected_account["expires_at"]
            if raw_expires and isinstance(raw_expires, str):
                try:
                    # 处理各种时区格式: +00:00, Z, 或无时区
                    cleaned = raw_expires.replace("Z", "+00:00").replace("+00:00", "")
                    expires_at = datetime.fromisoformat(cleaned)
                except Exception as e:
                    logger.warning(f"解析过期时间失败 (原始值: {raw_expires}): {e}")

            # 5. 确定状态
            status = "active"
            if expires_at and expires_at < datetime.now():
                status = "expired"

            # 6. 加密 AT Token
            encrypted_token = encryption_service.encrypt_token(access_token)

            # 7. 检查是否已存在 (根据邮箱和 account_id)
            stmt = select(PlusAccount).where(
                PlusAccount.email == email,
                PlusAccount.account_id == selected_account["account_id"]
            )
            result = await db_session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                return {
                    "success": False,
                    "plus_id": existing.id,
                    "message": None,
                    "error": f"该 Plus 账号已存在 (ID: {existing.id})"
                }

            # 8. 创建 PlusAccount 记录
            plus_account = PlusAccount(
                email=email,
                access_token_encrypted=encrypted_token,
                encryption_key_id="default",
                account_id=selected_account["account_id"],
                account_name=selected_account["name"],
                plan_type=selected_account["plan_type"],
                subscription_plan=selected_account["subscription_plan"],
                expires_at=expires_at,
                status=status,
                last_sync=get_now()
            )

            db_session.add(plus_account)
            await db_session.commit()

            logger.info(f"Plus 导入成功: {email} -> {selected_account['account_id']}")

            return {
                "success": True,
                "plus_id": plus_account.id,
                "message": f"Plus 导入成功 (共 {len(plus_accounts)} 个账户)",
                "error": None
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(f"Plus 导入失败: {e}")
            return {
                "success": False,
                "plus_id": None,
                "message": None,
                "error": f"导入失败: {str(e)}"
            }

    async def import_plus_batch(
        self,
        text: str,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        批量导入 Plus 账号（并发执行，信号量限制并发数）

        Args:
            text: 包含 Token、邮箱、Account ID 的文本
            db_session: 数据库会话

        Returns:
            结果字典,包含 success, total, success_count, failed_count, results
        """
        try:
            # 1. 解析文本
            parsed_data = self.token_parser.parse_team_import_text(text)

            if not parsed_data:
                return {
                    "success": False,
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "results": [],
                    "error": "未能从文本中提取任何 Token"
                }

            # 2. 并发导入（信号量限制并发数为 3）
            sem = asyncio.Semaphore(3)

            async def import_one(data: Dict[str, Any]) -> Dict[str, Any]:
                async with sem:
                    result = await self.import_plus_single(
                        access_token=data["token"],
                        db_session=db_session,
                        email=data.get("email"),
                        account_id=data.get("account_id")
                    )
                    return {
                        "email": data.get("email", "未知"),
                        "account_id": data.get("account_id", "未指定"),
                        "success": result["success"],
                        "plus_id": result["plus_id"],
                        "message": result["message"],
                        "error": result["error"]
                    }

            import_results = await asyncio.gather(
                *[import_one(d) for d in parsed_data],
                return_exceptions=True
            )

            # 3. 统计结果
            results = []
            success_count = 0
            failed_count = 0

            for data, res in zip(parsed_data, import_results):
                if isinstance(res, Exception):
                    failed_count += 1
                    results.append({
                        "email": data.get("email", "未知"),
                        "account_id": data.get("account_id", "未指定"),
                        "success": False,
                        "plus_id": None,
                        "message": None,
                        "error": f"导入异常: {str(res)}"
                    })
                else:
                    results.append(res)
                    if res["success"]:
                        success_count += 1
                    else:
                        failed_count += 1

            logger.info(f"批量导入完成: 总数 {len(parsed_data)}, 成功 {success_count}, 失败 {failed_count}")

            return {
                "success": True,
                "total": len(parsed_data),
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

    async def _sync_plus_data(
        self,
        plus_account: PlusAccount,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        同步单个 Plus 账号数据的内部方法 (不提交事务)
        直接修改 plus_account 对象属性,由调用方负责 commit

        Args:
            plus_account: PlusAccount ORM 对象
            db_session: 数据库会话

        Returns:
            结果字典,包含 success, message, error
        """
        try:
            # 1. 解密 AT Token
            try:
                access_token = encryption_service.decrypt_token(plus_account.access_token_encrypted)
            except Exception as e:
                logger.error(f"解密 Token 失败 (Plus {plus_account.id}): {e}")
                plus_account.status = "error"
                plus_account.error_message = f"解密 Token 失败: {str(e)}"
                return {
                    "success": False,
                    "message": None,
                    "error": plus_account.error_message
                }

            # 2. 获取账户信息
            account_result = await self.chatgpt_service.get_plus_account_info(
                access_token, db_session
            )

            if not account_result["success"]:
                plus_account.status = "error"
                plus_account.error_message = f"获取账户信息失败: {account_result['error']}"
                return {
                    "success": False,
                    "message": None,
                    "error": plus_account.error_message
                }

            # 3. 查找当前使用的 account
            accounts = account_result["accounts"]
            current_account = None

            for acc in accounts:
                if acc["account_id"] == plus_account.account_id:
                    current_account = acc
                    break

            if not current_account:
                for acc in accounts:
                    if acc["has_active_subscription"]:
                        current_account = acc
                        break

                if not current_account and accounts:
                    current_account = accounts[0]

            if not current_account:
                all_plan_types = account_result.get("all_plan_types", [])
                plus_account.status = "error"
                plus_account.error_message = f"该 Token 没有关联任何 Plus 账户 (发现的账户类型: {', '.join(all_plan_types)})" if all_plan_types else "该 Token 没有关联任何 Plus 账户"
                return {
                    "success": False,
                    "message": None,
                    "error": plus_account.error_message
                }

            # 4. 解析过期时间
            expires_at = None
            raw_expires = current_account["expires_at"]
            if raw_expires and isinstance(raw_expires, str):
                try:
                    cleaned = raw_expires.replace("Z", "+00:00").replace("+00:00", "")
                    expires_at = datetime.fromisoformat(cleaned)
                except (ValueError, TypeError) as e:
                    logger.warning(f"解析过期时间失败 (原始值: {raw_expires}): {e}")

            # 5. 确定状态
            status = "active"
            if expires_at and expires_at < datetime.now():
                status = "expired"

            # 6. 更新 Plus 账号信息
            plus_account.account_id = current_account["account_id"]
            plus_account.account_name = current_account["name"]
            plus_account.plan_type = current_account["plan_type"]
            plus_account.subscription_plan = current_account["subscription_plan"]
            plus_account.expires_at = expires_at
            plus_account.status = status
            plus_account.error_message = None  # 成功时清除错误信息
            plus_account.last_sync = get_now()

            logger.info(f"Plus {plus_account.id} 数据同步成功")

            return {
                "success": True,
                "message": "同步成功",
                "error": None
            }

        except Exception as e:
            logger.error(f"Plus {plus_account.id} 数据同步失败: {e}")
            plus_account.status = "error"
            plus_account.error_message = f"同步失败: {str(e)}"
            return {
                "success": False,
                "message": None,
                "error": plus_account.error_message
            }

    async def sync_plus_info(
        self,
        plus_id: int,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        同步单个 Plus 账号的信息

        Args:
            plus_id: Plus 账号 ID
            db_session: 数据库会话

        Returns:
            结果字典,包含 success, message, error
        """
        try:
            stmt = select(PlusAccount).where(PlusAccount.id == plus_id)
            result = await db_session.execute(stmt)
            plus_account = result.scalar_one_or_none()

            if not plus_account:
                return {
                    "success": False,
                    "message": None,
                    "error": f"Plus 账号 ID {plus_id} 不存在"
                }

            sync_result = await self._sync_plus_data(plus_account, db_session)
            await db_session.commit()
            return sync_result

        except Exception as e:
            await db_session.rollback()
            logger.error(f"Plus 同步失败: {e}")
            return {
                "success": False,
                "message": None,
                "error": f"同步失败: {str(e)}"
            }

    async def sync_all_plus(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        并发同步所有 Plus 账号的信息

        Args:
            db_session: 数据库会话

        Returns:
            结果字典,包含 success, total, success_count, failed_count, results
        """
        try:
            # 阶段 1: 加载所有 Plus 账号
            stmt = select(PlusAccount)
            result = await db_session.execute(stmt)
            accounts = result.scalars().all()

            if not accounts:
                return {
                    "success": True,
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "results": [],
                    "error": None
                }

            # 阶段 2: 确保 ChatGPT HTTP 会话已初始化
            if not self.chatgpt_service.session:
                self.chatgpt_service.session = await self.chatgpt_service._create_session(db_session)

            # 阶段 3: 并发执行同步 (信号量限制并发数)
            sem = asyncio.Semaphore(3)

            async def sync_one(account: PlusAccount) -> Dict[str, Any]:
                async with sem:
                    return await self._sync_plus_data(account, db_session)

            sync_results = await asyncio.gather(
                *[sync_one(a) for a in accounts],
                return_exceptions=True
            )

            # 阶段 4: 处理结果并批量提交
            results = []
            success_count = 0
            failed_count = 0

            for account, sync_result in zip(accounts, sync_results):
                if isinstance(sync_result, Exception):
                    account.status = "error"
                    account.error_message = f"同步异常: {str(sync_result)}"
                    failed_count += 1
                    results.append({
                        "plus_id": account.id,
                        "email": account.email,
                        "success": False,
                        "message": None,
                        "error": account.error_message
                    })
                elif sync_result["success"]:
                    success_count += 1
                    results.append({
                        "plus_id": account.id,
                        "email": account.email,
                        "success": True,
                        "message": sync_result["message"],
                        "error": None
                    })
                else:
                    failed_count += 1
                    results.append({
                        "plus_id": account.id,
                        "email": account.email,
                        "success": False,
                        "message": None,
                        "error": sync_result["error"]
                    })

            await db_session.commit()

            logger.info(f"批量同步完成: 总数 {len(accounts)}, 成功 {success_count}, 失败 {failed_count}")

            return {
                "success": True,
                "total": len(accounts),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
                "error": None
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(f"批量同步失败: {e}")
            return {
                "success": False,
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
                "results": [],
                "error": f"批量同步失败: {str(e)}"
            }

    async def retry_error_plus(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        重试所有异常状态的 Plus 账号 (重新同步)

        Args:
            db_session: 数据库会话

        Returns:
            结果字典,包含 success, total, success_count, failed_count, results
        """
        try:
            # 1. 查询所有 error 状态的 Plus 账号
            stmt = select(PlusAccount).where(PlusAccount.status == "error")
            result = await db_session.execute(stmt)
            error_accounts = result.scalars().all()

            if not error_accounts:
                return {
                    "success": True,
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "results": [],
                    "error": None
                }

            # 2. 确保 HTTP 会话已初始化
            if not self.chatgpt_service.session:
                self.chatgpt_service.session = await self.chatgpt_service._create_session(db_session)

            # 3. 并发重试
            sem = asyncio.Semaphore(3)

            async def retry_one(account: PlusAccount) -> Dict[str, Any]:
                async with sem:
                    return await self._sync_plus_data(account, db_session)

            sync_results = await asyncio.gather(
                *[retry_one(a) for a in error_accounts],
                return_exceptions=True
            )

            # 4. 处理结果
            results = []
            success_count = 0
            failed_count = 0

            for account, sync_result in zip(error_accounts, sync_results):
                if isinstance(sync_result, Exception):
                    account.status = "error"
                    account.error_message = f"重试异常: {str(sync_result)}"
                    failed_count += 1
                    results.append({
                        "plus_id": account.id,
                        "email": account.email,
                        "success": False,
                        "message": None,
                        "error": account.error_message
                    })
                elif sync_result["success"]:
                    success_count += 1
                    results.append({
                        "plus_id": account.id,
                        "email": account.email,
                        "success": True,
                        "message": sync_result["message"],
                        "error": None
                    })
                else:
                    failed_count += 1
                    results.append({
                        "plus_id": account.id,
                        "email": account.email,
                        "success": False,
                        "message": None,
                        "error": sync_result["error"]
                    })

            await db_session.commit()

            logger.info(f"重试异常 Plus 完成: 总数 {len(error_accounts)}, 成功 {success_count}, 失败 {failed_count}")

            return {
                "success": True,
                "total": len(error_accounts),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
                "error": None
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(f"重试异常 Plus 失败: {e}")
            return {
                "success": False,
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
                "results": [],
                "error": f"重试异常 Plus 失败: {str(e)}"
            }

    async def get_all_plus(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        获取所有 Plus 账号列表 (用于管理员页面)

        Args:
            db_session: 数据库会话

        Returns:
            结果字典,包含 success, accounts, error
        """
        try:
            stmt = select(PlusAccount).order_by(PlusAccount.created_at.desc())
            result = await db_session.execute(stmt)
            accounts = result.scalars().all()

            account_list = []
            for account in accounts:
                account_list.append({
                    "id": account.id,
                    "email": account.email,
                    "account_id": account.account_id,
                    "account_name": account.account_name,
                    "plan_type": account.plan_type,
                    "subscription_plan": account.subscription_plan,
                    "expires_at": account.expires_at.isoformat() if account.expires_at else None,
                    "status": account.status,
                    "error_message": account.error_message,
                    "last_sync": account.last_sync.isoformat() if account.last_sync else None,
                    "created_at": account.created_at.isoformat() if account.created_at else None
                })

            logger.info(f"获取所有 Plus 列表成功: 共 {len(account_list)} 个")

            return {
                "success": True,
                "accounts": account_list,
                "error": None
            }

        except Exception as e:
            logger.error(f"获取所有 Plus 列表失败: {e}")
            return {
                "success": False,
                "accounts": [],
                "error": f"获取所有 Plus 列表失败: {str(e)}"
            }

    async def delete_plus(
        self,
        plus_id: int,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        删除 Plus 账号

        Args:
            plus_id: Plus 账号 ID
            db_session: 数据库会话

        Returns:
            结果字典,包含 success, message, error
        """
        try:
            stmt = select(PlusAccount).where(PlusAccount.id == plus_id)
            result = await db_session.execute(stmt)
            plus_account = result.scalar_one_or_none()

            if not plus_account:
                return {
                    "success": False,
                    "message": None,
                    "error": f"Plus 账号 ID {plus_id} 不存在"
                }

            await db_session.delete(plus_account)
            await db_session.commit()

            logger.info(f"删除 Plus {plus_id} 成功")

            return {
                "success": True,
                "message": "Plus 账号已删除",
                "error": None
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(f"删除 Plus 失败: {e}")
            return {
                "success": False,
                "message": None,
                "error": f"删除 Plus 失败: {str(e)}"
            }

    async def delete_error_plus(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        批量删除所有异常状态的 Plus 账号

        Args:
            db_session: 数据库会话

        Returns:
            结果字典,包含 success, deleted_count, message, error
        """
        try:
            stmt = select(PlusAccount).where(PlusAccount.status == "error")
            result = await db_session.execute(stmt)
            error_accounts = result.scalars().all()

            if not error_accounts:
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": "没有异常状态的 Plus 账号",
                    "error": None
                }

            deleted_count = len(error_accounts)
            for account in error_accounts:
                await db_session.delete(account)

            await db_session.commit()

            logger.info(f"批量删除 {deleted_count} 个异常 Plus 成功")

            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"已删除 {deleted_count} 个异常 Plus 账号",
                "error": None
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(f"批量删除异常 Plus 失败: {e}")
            return {
                "success": False,
                "deleted_count": 0,
                "message": None,
                "error": f"批量删除异常 Plus 失败: {str(e)}"
            }


# 创建全局 Plus 服务实例
plus_service = PlusService()
