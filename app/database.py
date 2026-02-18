"""
数据库连接模块
SQLite 异步连接配置和会话管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from app.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # 开发环境打印 SQL
    future=True,
    # SQLite 并发保护配置
    connect_args={"timeout": 30},  # 等待锁释放的超时时间（秒）
    pool_size=1,          # SQLite 单文件锁，限制为单连接
    max_overflow=0,       # 不允许额外连接
    pool_pre_ping=True,   # 自动检测失效连接
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """启用 WAL 模式，允许读写并发"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 创建 Base 类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    获取数据库会话
    用于 FastAPI 依赖注入
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库
    创建所有表
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
