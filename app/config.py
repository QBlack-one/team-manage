"""
应用配置模块
使用 Pydantic Settings 管理配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    app_name: str = "GPT Team 管理系统"
    app_version: str = "0.1.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8008
    debug: bool = False  # 默认关闭调试模式

    # 数据库配置
    # 本地开发使用 SQLite，生产环境使用 PostgreSQL (Supabase)
    # Vercel 部署时通过环境变量设置 DATABASE_URL
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/team_manage.db"

    # 安全配置
    # 必须通过 .env 文件设置 SECRET_KEY，否则加密的 Token 和 Session 在重启后失效
    secret_key: str = ""
    admin_password: str = "admin123"  # 首次运行后应立即修改

    # HTTPS 配置
    https_only: bool = False  # 生产环境应设为 True

    # 日志配置
    log_level: str = "INFO"

    # 代理配置
    proxy: str = ""
    proxy_enabled: bool = False

    # JWT 配置
    jwt_verify_signature: bool = False

    # 时区配置
    timezone: str = "Asia/Shanghai"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# 创建全局配置实例
settings = Settings()

# 启动校验: secret_key 不能为空
if not settings.secret_key:
    raise RuntimeError(
        "SECRET_KEY 未配置！请在 .env 文件中设置 SECRET_KEY，"
        "否则加密的 Token 和 Session 在重启后会失效。\n"
        "生成方法: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

