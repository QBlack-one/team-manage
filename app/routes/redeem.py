"""
兑换路由
处理用户兑换码验证和加入 Team / 获取 Plus 的请求
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.redeem_flow import redeem_flow_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/redeem",
    tags=["redeem"]
)


# 请求模型
class VerifyCodeRequest(BaseModel):
    """验证兑换码请求"""
    code: str = Field(..., description="兑换码", min_length=1)


class RedeemRequest(BaseModel):
    """兑换请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    code: str = Field(..., description="兑换码", min_length=1)
    redeem_type: str = Field("team", description="兑换类型: team 或 plus")
    team_id: Optional[int] = Field(None, description="Team ID (可选，不提供则自动选择)")


# 响应模型
class TeamInfo(BaseModel):
    """Team 信息"""
    id: int
    team_name: str
    current_members: int
    max_members: int
    expires_at: Optional[str]
    subscription_plan: Optional[str]


class VerifyCodeResponse(BaseModel):
    """验证兑换码响应"""
    success: bool
    valid: bool
    reason: Optional[str] = None
    teams: List[TeamInfo] = []
    error: Optional[str] = None


class RedeemResponse(BaseModel):
    """兑换响应"""
    success: bool
    message: Optional[str] = None
    redeem_type: Optional[str] = None
    team_info: Optional[Dict[str, Any]] = None
    plus_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/verify", response_model=VerifyCodeResponse)
async def verify_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """验证兑换码并返回可用 Team 列表"""
    try:
        logger.info(f"验证兑换码请求: {request.code}")

        result = await redeem_flow_service.verify_code_and_get_teams(
            request.code,
            db
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return VerifyCodeResponse(
            success=result["success"],
            valid=result["valid"],
            reason=result["reason"],
            teams=[TeamInfo(**team) for team in result["teams"]],
            error=result["error"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证兑换码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证失败: {str(e)}"
        )


@router.post("/confirm", response_model=RedeemResponse)
async def confirm_redeem(
    request: RedeemRequest,
    db: AsyncSession = Depends(get_db)
):
    """确认兑换 - 支持 Team 和 Plus 两种类型"""
    try:
        logger.info(f"兑换请求: {request.email} -> 类型: {request.redeem_type} (兑换码: {request.code})")

        if request.redeem_type == "plus":
            # Plus 兑换
            result = await redeem_flow_service.redeem_plus(
                request.email,
                request.code,
                db
            )

            if not result["success"]:
                error_msg = result["error"]
                if "不存在" in error_msg or "已使用" in error_msg or "已过期" in error_msg:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
                elif "没有可用" in error_msg:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
                else:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

            return RedeemResponse(
                success=True,
                message=result["message"],
                redeem_type="plus",
                plus_info=result["plus_info"],
                error=None
            )

        else:
            # Team 兑换 (默认)
            result = await redeem_flow_service.redeem_and_join_team(
                request.email,
                request.code,
                request.team_id,
                db
            )

            if not result["success"]:
                error_msg = result["error"]
                if "不存在" in error_msg or "已使用" in error_msg or "已过期" in error_msg:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
                elif "已满" in error_msg:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
                else:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

            return RedeemResponse(
                success=True,
                message=result["message"],
                redeem_type="team",
                team_info=result["team_info"],
                error=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"兑换失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"兑换失败: {str(e)}"
        )
