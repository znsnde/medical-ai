"""Alembic 环境：同步模式，DB_URL 从 settings.DB_URL（.env / 环境变量）注入。

DB_URL 不写在 alembic.ini（避免硬编码密钥），统一由 backend/config/settings.py 提供，
与主应用 engine 同源，保证迁移与运行时连同一套库。
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import db.models  # noqa: F401  必须优先导入，让全部模型注册到 Base.metadata
from db.session import Base
from config.settings import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据：models.py 定义的全部表
target_metadata = Base.metadata

# DB_URL 注入（须在 engine_from_config 之前）
if not settings.DB_URL:
    raise RuntimeError("DB_URL 未配置（backend/.env 或环境变量）")
config.set_main_option("sqlalchemy.url", settings.DB_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (纯 SQL 输出，不连库)。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode（真实连接执行 DDL）。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 字段类型变化能被 autogenerate 感知
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
