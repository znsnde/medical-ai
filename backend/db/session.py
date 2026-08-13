from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

# 约束/索引命名规范：让新库 DDL（create_all / Alembic autogenerate）产出的
# FK/索引名与存量库及 migrate_fk 的显式命名完全一致（ix_patient_phone / fk_patient_user_id_user 等）。
# 不加此约定时 MySQL 会给 FK 起自动名（patient_ibfk_1），migrate_fk 的幂等存在性检查
# 按 fk_* 名查不到，会在新库上重复加外键（create_all 流程下已存在的隐患）。
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

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
Base = declarative_base(metadata=MetaData(naming_convention=NAMING_CONVENTION))

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()