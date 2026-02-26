"""
兑换码管理路由
处理兑换码的生成、删除、导出
"""
import logging
from typing import Optional
from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import xlsxwriter

from app.database import get_db
from app.dependencies.auth import require_admin
from app.services.redemption import RedemptionService
from app.utils.time_utils import get_now

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(tags=["admin-codes"])

# 服务实例
redemption_service = RedemptionService()


# 请求模型
class CodeGenerateRequest(BaseModel):
    """兑换码生成请求"""
    type: str = Field(..., description="生成类型: single 或 batch")
    code: Optional[str] = Field(None, description="自定义兑换码 (单个生成)")
    count: Optional[int] = Field(None, description="生成数量 (批量生成)")
    expires_days: Optional[int] = Field(None, description="有效期天数")
    code_type: str = Field("team", description="兑换码类型: team 或 plus")


@router.get("/codes", response_class=HTMLResponse)
async def codes_list_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """兑换码列表页面"""
    try:
        from app.main import templates

        logger.info("管理员访问兑换码列表页面")

        codes_result = await redemption_service.get_all_codes(db)
        all_codes = codes_result.get("codes", [])

        stats = {
            "total": len(all_codes),
            "unused": len([c for c in all_codes if c["status"] == "unused"]),
            "used": len([c for c in all_codes if c["status"] == "used"]),
            "expired": len([c for c in all_codes if c["status"] == "expired"])
        }

        # 格式化日期时间
        for code in all_codes:
            if code.get("created_at"):
                dt = datetime.fromisoformat(code["created_at"])
                code["created_at"] = dt.strftime("%Y-%m-%d %H:%M")
            if code.get("expires_at"):
                dt = datetime.fromisoformat(code["expires_at"])
                code["expires_at"] = dt.strftime("%Y-%m-%d %H:%M")
            if code.get("used_at"):
                dt = datetime.fromisoformat(code["used_at"])
                code["used_at"] = dt.strftime("%Y-%m-%d %H:%M")

        return templates.TemplateResponse(
            "admin/codes/index.html",
            {
                "request": request,
                "user": current_user,
                "active_page": "codes",
                "codes": all_codes,
                "stats": stats
            }
        )

    except Exception as e:
        logger.error(f"加载兑换码列表页面失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加载页面失败: {str(e)}"
        )


@router.post("/codes/generate")
async def generate_codes(
    generate_data: CodeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """处理兑换码生成"""
    try:
        logger.info(f"管理员生成兑换码: {generate_data.type}")

        if generate_data.type == "single":
            result = await redemption_service.generate_code_single(
                db_session=db,
                code=generate_data.code,
                expires_days=generate_data.expires_days,
                code_type=generate_data.code_type
            )

            if not result["success"]:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=result
                )
            return JSONResponse(content=result)

        elif generate_data.type == "batch":
            if not generate_data.count:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"success": False, "error": "生成数量不能为空"}
                )

            result = await redemption_service.generate_code_batch(
                db_session=db,
                count=generate_data.count,
                expires_days=generate_data.expires_days,
                code_type=generate_data.code_type
            )

            if not result["success"]:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=result
                )
            return JSONResponse(content=result)

        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "无效的生成类型"}
            )

    except Exception as e:
        logger.error(f"生成兑换码失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"生成失败: {str(e)}"}
        )


@router.post("/codes/{code}/delete")
async def delete_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """删除兑换码"""
    try:
        logger.info(f"管理员删除兑换码: {code}")
        result = await redemption_service.delete_code(code, db)

        if not result["success"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=result
            )
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"删除兑换码失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": f"删除失败: {str(e)}"}
        )


@router.get("/codes/export")
async def export_codes(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """导出兑换码为Excel文件"""
    try:
        logger.info("管理员导出兑换码为Excel")

        codes_result = await redemption_service.get_all_codes(db)
        all_codes = codes_result.get("codes", [])

        # 创建Excel文件到内存
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('兑换码列表')

        # 定义格式
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#4F46E5',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })

        # 设置列宽
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 18)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 18)

        # 写入表头
        headers = ['兑换码', '状态', '创建时间', '过期时间', '使用者邮箱', '使用时间']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # 写入数据
        for row, code in enumerate(all_codes, start=1):
            status_text = {
                'unused': '未使用',
                'used': '已使用',
                'expired': '已过期'
            }.get(code['status'], code['status'])

            worksheet.write(row, 0, code['code'], cell_format)
            worksheet.write(row, 1, status_text, cell_format)
            worksheet.write(row, 2, code.get('created_at', '-'), cell_format)
            worksheet.write(row, 3, code.get('expires_at', '永久有效'), cell_format)
            worksheet.write(row, 4, code.get('used_by_email', '-'), cell_format)
            worksheet.write(row, 5, code.get('used_at', '-'), cell_format)

        workbook.close()

        excel_data = output.getvalue()
        output.close()

        filename = f"redemption_codes_{get_now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"导出兑换码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出失败: {str(e)}"
        )
