"""
外键约束 + 核心索引 迁移脚本（幂等，可重复执行）

背景：项目早期 schema 无 ForeignKey/Index，删除流缺子行清理导致两库产生孤儿数据。
本脚本一次性 backfill 现有库：
  Phase A  孤儿清理（报告/病历/消息/会话引用父行不存在 → 删除）
  Phase B  测试残留全清（无绑定患者 + 无绑定测试账号；用户已批准一次性全清）
  Phase C  核心索引（高频查询列）
  Phase D  外键约束（ON DELETE 与 models.py 声明一致）

用法（同一脚本覆盖容器内 mysql:3306 与宿主 127.0.0.1:3306）：
    cd backend && venv/Scripts/python.exe -m db.migrate_fk
    # Docker 容器内：cd /app && python -m db.migrate_fk

幂等保证：所有 DDL 以 information_schema 存在性检查为前提，重复执行全跳过；
DELETE 天然幂等。清完孤儿后再加 FK，漏网孤儿会让 ALTER 大声失败（比静默带脏约束好），
故不关闭 FOREIGN_KEY_CHECKS。

本脚本只承担本次 backfill，不负责未来 schema 演进（那是 Alembic 的职责）。
"""
import sys

from sqlalchemy import text
from db.session import engine, SessionLocal

# ── 索引：表, 索引名, 列 ──
INDEXES = [
    ("patient", "ix_patient_phone", "phone"),
    ("patient", "ix_patient_user_id", "user_id"),
    ("medical_record", "ix_medical_record_patient_id", "patient_id"),
    ("diagnosis_report", "ix_diagnosis_report_record_id", "record_id"),
    ("consult_session", "ix_consult_session_user_id", "user_id"),
    ("consult_message", "ix_consult_message_session_id", "session_id"),
]

# ── 外键：表, 约束名, 子列, 父表, 父列, ondelete ──
FKS = [
    ("patient", "fk_patient_user_id_user", "user_id", "user", "id", "SET NULL"),
    ("medical_record", "fk_medical_record_patient_id_patient", "patient_id", "patient", "id", "CASCADE"),
    ("diagnosis_report", "fk_diagnosis_report_record_id_medical_record", "record_id", "medical_record", "id", "CASCADE"),
    ("consult_session", "fk_consult_session_user_id_user", "user_id", "user", "id", "CASCADE"),
    ("consult_message", "fk_consult_message_session_id_consult_session", "session_id", "consult_session", "id", "CASCADE"),
]


def _db_name(conn) -> str:
    return conn.execute(text("SELECT DATABASE()")).scalar()


def phase_orphans(db):
    """Phase A：孤儿清理（引用父行不存在 → 删）。返回清理计数 dict。"""
    counts = {}
    orphans = [
        # (说明, DELETE SQL 表, 子表, 子列, 父表, 父列)
        ("诊断报告", "diagnosis_report", "record_id", "medical_record", "id"),
        ("病历", "medical_record", "patient_id", "patient", "id"),
        ("问诊消息", "consult_message", "session_id", "consult_session", "id"),
        ("问诊会话", "consult_session", "user_id", "user", "id"),
    ]
    for label, table, child_col, parent, parent_col in orphans:
        n = db.execute(text(
            f"DELETE FROM {table} WHERE {child_col} NOT IN (SELECT {parent_col} FROM {parent})"
        )).rowcount
        counts[label] = n
        if n:
            print(f"  [孤儿清理] {label}: 删除 {n} 条")
    db.commit()
    return counts


def phase_residue(db):
    """Phase B：测试残留全清（无绑定患者 + 无绑定测试账号）。返回清理计数 dict。"""
    counts = {}

    # 1. 无绑定患者的病历/报告行（先子后父，避免留孤儿）
    #    收集将删的 record 列表，级联删其 report；patient 删前其 record 已清
    rec_n = db.execute(text(
        "DELETE FROM diagnosis_report WHERE record_id IN "
        "(SELECT id FROM medical_record WHERE patient_id IN "
        "(SELECT id FROM patient WHERE user_id IS NULL))"
    )).rowcount
    rep_n = db.execute(text(
        "DELETE FROM medical_record WHERE patient_id IN "
        "(SELECT id FROM patient WHERE user_id IS NULL)"
    )).rowcount
    counts["无绑定患者病历"] = rep_n
    counts["无绑定患者报告"] = rec_n
    if rec_n or rep_n:
        print(f"  [残留清理] 无绑定患者病历: 删 {rep_n}，报告: 删 {rec_n}")

    # 2. 无绑定患者本体
    pat_n = db.execute(text("DELETE FROM patient WHERE user_id IS NULL")).rowcount
    counts["无绑定患者"] = pat_n
    if pat_n:
        print(f"  [残留清理] 无绑定患者: 删 {pat_n} 条")

    # 3. 未绑定任何档案的测试/患者账号（pat_*/pself_*/securit_* 前缀 或 role='patient'）
    #    已绑定档案的账号一律保留：pat_* 前缀会误伤合法演示账号 patient_demo，
    #    故前缀命中后仍须满足"未绑定档案"才算残留（2026-08-13 Docker 库实测误删过）。
    #    admin/doctor 等角色非 patient 且无测试前缀 → 永不命中。
    usr_n = db.execute(text(
        "DELETE FROM user WHERE "
        "(username LIKE 'pat_%' OR username LIKE 'pself_%' OR username LIKE 'securit_%' "
        "OR role = 'patient') "
        "AND id NOT IN (SELECT COALESCE(user_id, 0) FROM patient)"
    )).rowcount
    counts["无绑定测试账号"] = usr_n
    if usr_n:
        print(f"  [残留清理] 测试账号: 删 {usr_n} 条")

    db.commit()
    return counts


def phase_indexes(db):
    """Phase C：核心索引（存在性检查后创建）。返回新增数。"""
    added = 0
    for table, name, col in INDEXES:
        exists = db.execute(text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :t AND INDEX_NAME = :n"
        ), {"db": _db_name(db.connection()), "t": table, "n": name}).scalar()
        if exists:
            print(f"  [索引] {name} 已存在，跳过")
            continue
        db.execute(text(f"CREATE INDEX {name} ON {table} ({col})"))
        print(f"  [索引] 新增 {name} ({table}.{col})")
        added += 1
    db.commit()
    return added


def phase_break_bad_binds(db):
    """Phase B+：解除 patient.user_id 指向不存在 user 的失效绑定（ON DELETE SET NULL 语义）"""
    # 此步必须在清完残留账号后执行：残留账号被删后，其绑定患者若仍引用则 FK 建立会失败
    n = db.execute(text(
        "UPDATE patient p LEFT JOIN user u ON p.user_id = u.id "
        "SET p.user_id = NULL WHERE p.user_id IS NOT NULL AND u.id IS NULL"
    )).rowcount
    if n:
        print(f"  [残留清理] 解除失效患者绑定: {n} 条 (user_id → NULL)")
    db.commit()


def phase_fks(db):
    """Phase D：外键约束（存在性检查后 ALTER）。返回新增数。"""
    added = 0
    for table, name, child_col, parent, parent_col, ondelete in FKS:
        exists = db.execute(text(
            "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = :db AND TABLE_NAME = :t "
            "AND CONSTRAINT_NAME = :n AND CONSTRAINT_TYPE = 'FOREIGN KEY'"
        ), {"db": _db_name(db.connection()), "t": table, "n": name}).scalar()
        if exists:
            print(f"  [外键] {name} 已存在，跳过")
            continue
        db.execute(text(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} "
            f"FOREIGN KEY ({child_col}) REFERENCES {parent}({parent_col}) "
            f"ON DELETE {ondelete}"
        ))
        print(f"  [外键] 新增 {name} ({table}.{child_col} → {parent}.{parent_col} ON DELETE {ondelete})")
        added += 1
    db.commit()
    return added


def main():
    print("=" * 60)
    print("  外键 + 索引迁移（幂等）")
    print("=" * 60)
    db = SessionLocal()
    try:
        print(f"  连接库: {engine.url.database}")
        phase_orphans(db)
        phase_residue(db)
        phase_break_bad_binds(db)
        idx = phase_indexes(db)
        fks = phase_fks(db)
        print()
        print(f"  完成：索引新增 {idx} 个，外键新增 {fks} 个（重复执行全跳过）")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
