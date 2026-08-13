from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

# MySQL引擎
# pool_recycle: 需小于 MySQL wait_timeout（默认8h），空闲连接被服务端回收前主动重建，
#   否则僵尸连接残留，高并发时队列耗尽导致随机 500
# pool_size / max_overflow: 单实例基础连接数 + 峰值溢出上限
# pool_timeout: 连接池耗尽时等待秒数，超时报错而非无限挂起
engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    echo=False
)
# expire_on_commit=False：commit 后不自动 expire 实例属性，
#   避免 FastAPI 依赖关闭 session 后响应序列化访问 ORM 属性时触发 DetachedInstanceError
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
Base = declarative_base()

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()