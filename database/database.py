"""SQLAlchemy 数据库引擎与会话管理"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base

# 数据库文件路径
DB_PATH = Path(os.getcwd()) / "data" / "edulingua.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

# 引擎（SQLite 需要 check_same_thread=False 以支持 FastAPI 异步）
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库：创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """获取数据库会话（FastAPI 依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """获取数据库会话（非 FastAPI 上下文用）"""
    return SessionLocal()
