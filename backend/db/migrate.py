"""Alembic 迁移入口：schema 统一由 Alembic 管理（替代 create_all / migrate_fk 的 schema 部分）。

分场景策略（让 entrypoint / CI / 本地 dev 顺序安全，无需手工区分）：
  - 有 alembic_version    → upgrade head（应用增量迁移）
  - 无版本表但有业务表    → 存量基线库：9 张业务表齐全则 stamp head（不动数据）
  - 空库                  → upgrade head（全新建表）
收尾校验：9 张业务表必须全部就位，否则非零退出（拒绝"静默缺表"）。

用法（必须在 backend/ 目录下运行，保证 db/config 可导入）：
    cd backend && venv/Scripts/python.exe -m db.migrate
    # 容器内：cd /app && python -m db.migrate
"""
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from db.session import engine

# backend/ 目录（本文件在 backend/db/migrate.py）
BASE_DIR = Path(__file__).resolve().parents[1]
INI = BASE_DIR / "alembic.ini"

# models.py 定义的全部业务表（用于存量库 stamp 前的完整性校验）
MODEL_TABLES = {
    "patient", "medical_record", "medical_paper", "diagnosis_report",
    "consult_session", "consult_message", "medical_knowledge", "user", "disease_dict",
}


def _tables() -> set:
    return set(inspect(engine).get_table_names())


def run():
    tables = _tables()
    cfg = Config(str(INI))

    if "alembic_version" in tables:
        print("[migrate] 已纳入版本管理 → upgrade head")
        command.upgrade(cfg, "head")
    elif tables:
        missing = MODEL_TABLES - tables
        if missing:
            raise SystemExit(
                f"[migrate] 存量库缺业务表 {sorted(missing)}，拒绝 stamp（库既非空也非完整基线）"
            )
        print("[migrate] 存量库（无 alembic_version）→ stamp head（不动数据）")
        command.stamp(cfg, "head")
    else:
        print("[migrate] 空库 → upgrade head 全新建表")
        command.upgrade(cfg, "head")

    # 收尾校验：9 张业务表必须就位
    missing = MODEL_TABLES - _tables()
    if missing:
        raise SystemExit(f"[migrate] schema 校验失败：缺表 {sorted(missing)}")
    print("[migrate] schema 校验通过（9 张业务表就位）")


def main():
    try:
        run()
        return 0
    except Exception as e:  # noqa: BLE001 迁移失败必须大声报错，由调用方决定是否阻塞
        print(f"[migrate] 失败：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
