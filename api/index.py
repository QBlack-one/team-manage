"""
Vercel Serverless Function Entry Point
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

# 导入 FastAPI 应用
from app.main import app

# Vercel 需要的 handler
handler = app
