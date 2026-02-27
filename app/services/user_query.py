"""
用户自助查询服务
支持用户通过邮箱查询兑换记录和 Team 状态
"""
import logging
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RedemptionRecord, RedemptionCode, Team

logger = logging.getLogger(__name__)


class UserQueryService:
    """用户自助查询服务类"""

    async def query_by_email(
        self,
        email: str,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        根据邮箱查询兑换记录和关联 Team 信息

        Args:
            email: 用户邮箱
            db_session: 数据库会话

        Returns:
            结果字典，包含 success, records, error
        """
        try:
            email = email.strip().lower()

            if not email:
                return {
                    "success": False,
                    "records": [],
                    "total": 0,
                    "error": "邮箱不能为空"
                }

            # 查询兑换记录
            stmt = (
                select(RedemptionRecord)
                .where(RedemptionRecord.email == email)
                .order_by(RedemptionRecord.redeemed_at.desc())
            )
            result = await db_session.execute(stmt)
            records = result.scalars().all()

            if not records:
                return {
                    "success": True,
                    "records": [],
                    "total": 0,
                    "error": None
                }

            # 收集关联的 Team ID 和兑换码
            team_ids = list(set(r.team_id for r in records))
            codes = list(set(r.code for r in records))

            # 批量查询 Team 信息
            teams_stmt = select(Team).where(Team.id.in_(team_ids))
            teams_result = await db_session.execute(teams_stmt)
            teams = {t.id: t for t in teams_result.scalars().all()}

            # 批量查询兑换码信息
            codes_stmt = select(RedemptionCode).where(RedemptionCode.code.in_(codes))
            codes_result = await db_session.execute(codes_stmt)
            code_infos = {c.code: c for c in codes_result.scalars().all()}

            # 组装结果
            record_list = []
            for r in records:
                team = teams.get(r.team_id)
                code_info = code_infos.get(r.code)

                record_list.append({
                    "code": r.code,
                    "code_type": code_info.code_type if code_info else "team",
                    "redeemed_at": r.redeemed_at.strftime("%Y-%m-%d %H:%M") if r.redeemed_at else "-",
                    "team_name": team.team_name if team else "未知",
                    "team_status": team.status if team else "未知",
                    "team_plan": team.subscription_plan if team else "-",
                    "team_expires_at": team.expires_at.strftime("%Y-%m-%d") if team and team.expires_at else "-",
                    "team_members": f"{team.current_members}/{team.max_members}" if team else "-"
                })

            logger.info(f"用户查询成功: {email}, 找到 {len(record_list)} 条记录")

            return {
                "success": True,
                "records": record_list,
                "total": len(record_list),
                "error": None
            }

        except Exception as e:
            logger.error(f"查询失败: {e}")
            return {
                "success": False,
                "records": [],
                "total": 0,
                "error": f"查询失败: {str(e)}"
            }


# 创建全局实例
user_query_service = UserQueryService()
