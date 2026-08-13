"""
数据库/知识库初始化脚本（容器首次启动与宿主均可用）

schema 已由 Alembic 统一管理（python -m db.migrate），本脚本只负责 seed：
1. init_admin   —— 无 admin 账号则创建 admin/admin123（README 默认账号）
2. init_neo4j   —— Disease 节点数为 0 时重建知识图谱（幂等，避免清空已有数据）
3. init_milvus  —— 医疗指南集合为空时灌入 MEDICAL_KNOWLEDGE（幂等）

用法（须先建表，即先跑 python -m db.migrate）：
    cd backend && venv/Scripts/python.exe -m db.init_db
    # 或容器 entrypoint 内：python -m db.init_db
"""
import sys

from db import models  # noqa: F401  确保全部表模型已注册
from db.session import engine, SessionLocal
from db.crud import user_crud
from core.security import hash_password
from core.medical_knowledge_data import MEDICAL_KNOWLEDGE


def init_admin():
    """确保存在默认管理员 admin / admin123"""
    db = SessionLocal()
    try:
        if user_crud.get_user_by_username(db, "admin") is None:
            user_crud.create_user(
                db,
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="系统管理员",
                role="admin",
                department="系统管理",
            )
            print("  [init] 已创建管理员账号 admin/admin123")
        else:
            print("  [init] 管理员账号 admin 已存在，跳过")
    finally:
        db.close()


def _neo4j_disease_count():
    from medical_business.knowledge_graph import get_driver
    with get_driver().session() as session:
        rec = session.run("MATCH (d:Disease) RETURN count(d) AS c").single()
        return rec["c"] if rec else 0


def init_neo4j():
    """图谱为空时才重建（init_graph 内部会 DETACH DELETE 全清）"""
    from medical_business.knowledge_graph import init_graph
    count = _neo4j_disease_count()
    if count == 0:
        print("  [init] Neo4j 图谱为空，重建 20 种疾病知识图谱...")
        init_graph()
        print(f"  [init] Neo4j 图谱重建完成（重建前疾病数 {count}）")
    else:
        print(f"  [init] Neo4j 图谱已有 {count} 种疾病，跳过重建")


def _milvus_entity_count():
    from pymilvus import utility
    from core.vector_store import connect_milvus, create_medical_collection
    err = connect_milvus()
    if err is not None:
        return None
    if not utility.has_collection("medical_knowledge_coll"):
        return 0
    coll = create_medical_collection()
    return coll.num_entities


def init_milvus():
    """医疗指南向量集合为空时才灌入，避免重复插入"""
    from core.entity_extract import insert_knowledge_to_milvus
    count = _milvus_entity_count()
    if count is None:
        raise RuntimeError("Milvus 连接失败，跳过医疗指南灌入")
    if count > 0:
        print(f"  [init] Milvus 医疗指南已有 {count} 条，跳过灌入")
        return
    ok = 0
    for text in MEDICAL_KNOWLEDGE:
        r = insert_knowledge_to_milvus(text)
        if r is not None:
            ok += 1
    print(f"  [init] Milvus 医疗指南灌入完成 {ok}/{len(MEDICAL_KNOWLEDGE)} 条")


def main():
    # schema 归属 Alembic：空库直接 seed 会产生误导（表没建），给出明确指引而非静默降级
    from sqlalchemy import inspect
    tables = set(inspect(engine).get_table_names())
    if not tables:
        print("[init] 数据库无任何表，请先运行：python -m db.migrate（Alembic 建表）", file=sys.stderr)
        return 1

    steps = [
        ("管理员账号", init_admin),
        ("Neo4j 图谱", init_neo4j),
        ("Milvus 指南", init_milvus),
    ]
    failed = []
    for name, fn in steps:
        try:
            fn()
            print(f"  [OK] {name}")
        except Exception as e:  # noqa: BLE001 逐项降级，不影响整体启动
            failed.append(name)
            print(f"  [跳过] {name}：{e}")
    if failed:
        print(f"初始化完成，失败项：{', '.join(failed)}（系统仍将启动，相关功能降级）")
        return 1
    print("初始化全部完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
