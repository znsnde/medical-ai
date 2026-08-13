"""
演示数据种子脚本
1. 初始化/重置 Neo4j 知识图谱（基于 knowledge_graph.SEED_DATA，含20种疾病）
2. 向 Milvus 灌入医疗指南文本（让 RAG 诊断时能召回真实"临床参考指南"）
3. 建演示患者账号 + 档案 + 病历 + 诊断报告（含PDF，供患者自助查看演示）

用法：
    f:/Python/Project/backend/venv/Scripts/python.exe scripts/seed_demo_data.py
（settings 会自行加载 backend/.env）
"""
import os
import sys

# 使 backend 模块可导入（config/medical_business/core 均为 backend 内包）
# 兼容两种布局：宿主仓库 scripts/../backend 与容器 /app/scripts/..（容器 /app 即 backend 根）
_script_dir = os.path.dirname(os.path.abspath(__file__))
_candidates = [
    os.path.join(_script_dir, "..", "backend"),
    os.path.join(_script_dir, ".."),
]
for _p in _candidates:
    if os.path.isfile(os.path.join(_p, "config", "settings.py")):
        sys.path.insert(0, _p)
        break

# ── Milvus 医疗指南知识库（与知识图谱疾病覆盖重叠，便于演示；数据源在 core/medical_knowledge_data） ──
from core.medical_knowledge_data import MEDICAL_KNOWLEDGE


def seed_neo4j():
    print("=" * 60)
    print("  [1/2] 初始化 Neo4j 知识图谱")
    print("=" * 60)
    from medical_business.knowledge_graph import init_graph
    init_graph()
    print()


def seed_milvus():
    print("=" * 60)
    print("  [2/2] 向 Milvus 灌入医疗指南知识")
    print("=" * 60)
    from core.entity_extract import insert_knowledge_to_milvus
    ok = 0
    for text in MEDICAL_KNOWLEDGE:
        r = insert_knowledge_to_milvus(text)
        if r is not None:
            ok += 1
            print(f"  OK {text[:18]}...")
        else:
            print(f"  FAIL {text[:18]}...")
    print(f"\n共灌入 {ok}/{len(MEDICAL_KNOWLEDGE)} 条")
    print()


# ── 演示患者：自助查看报告流程（手机号认领 → 我的病历/报告 → 下载PDF） ──
DEMO_PATIENT = {
    "username": "patient_demo",
    "password": "demo1234",
    "real_name": "张建国",
    "phone": "13800001111",
    "record_text": "患者张建国，男，58岁，主诉头晕头痛3天，晨起血压偏高，既往有高血压病史5年。",
    "structured_data": {"symptom": ["头晕", "头痛"], "past_history": ["高血压5年"], "diagnosis": ["高血压"], "medicine": []},
    "image_analysis": "颅脑CT未见明显异常；心电图示左室高电压，提示高血压性改变。",
    "diagnosis_suggest": "诊断：原发性高血压（2级）。建议规律口服降压药物，监测血压，低盐饮食，适量运动，定期随访。",
}


def seed_patient_demo():
    """建演示患者账号 + 档案 + 病历 + 报告（含PDF）。幂等：重复执行不报错。"""
    print("=" * 60)
    print("  [3/3] 建演示患者自助数据")
    print("=" * 60)
    from db.session import SessionLocal
    from db.crud import user_crud, patient_crud, record_crud, report_crud
    from core.security import hash_password
    from medical_business.report_generator import create_diagnosis_pdf_report

    p = DEMO_PATIENT
    db = SessionLocal()
    try:
        user = user_crud.get_user_by_username(db, p["username"])
        if user:
            print(f"  账号 {p['username']} 已存在，跳过")
            return
        user = user_crud.create_user(
            db=db, username=p["username"], password_hash=hash_password(p["password"]),
            real_name=p["real_name"], role="patient"
        )
        print(f"  患者账号 {p['username']}/{p['password']} (id={user.id})")

        patient = patient_crud.create_patient(db, p["real_name"], 58, "男", p["phone"])
        patient_crud.bind_patient(db, patient.id, user.id)
        print(f"  患者档案 {p['real_name']} 手机号 {p['phone']} (id={patient.id}) 已绑定账号")

        record = record_crud.create_record(db, patient.id, p["record_text"], p["structured_data"])
        print(f"  病历 (id={record.id}): {p['record_text'][:20]}...")

        report = report_crud.create_report(
            db, record.id, p["image_analysis"], p["diagnosis_suggest"], pdf_path=""
        )
        updated, _ = create_diagnosis_pdf_report(db, report.id)
        print(f"  诊断报告 (id={report.id}) PDF 已生成: {updated.pdf_path}")
        print("\n  演示路径：患者端登录 patient_demo/demo1234 → 我的病历 → 绑定手机号")
    finally:
        db.close()
    print()


def verify():
    print("=" * 60)
    print("  验证")
    print("=" * 60)
    try:
        from medical_business.knowledge_graph import query_graph
        g = query_graph()
        print(f"  Neo4j 全图: {len(g['nodes'])} 节点, {len(g['links'])} 条关系")
    except Exception as e:
        print(f"  Neo4j 查询失败: {e}")
    try:
        from core.medical_rag import rag_search_medical_knowledge
        hits = rag_search_medical_knowledge("高血压患者血压控制目标", top_k=3)
        print(f"  RAG 召回: {len(hits)} 条")
        for t in hits:
            print(f"    - {t[:40]}...")
    except Exception as e:
        print(f"  RAG 查询失败: {e}")


if __name__ == "__main__":
    seed_neo4j()
    seed_milvus()
    seed_patient_demo()
    verify()
