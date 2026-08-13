"""
演示数据种子脚本
1. 初始化/重置 Neo4j 知识图谱（基于 knowledge_graph.SEED_DATA，含20种疾病）
2. 向 Milvus 灌入医疗指南文本（让 RAG 诊断时能召回真实"临床参考指南"）

用法：
    f:/Python/Project/backend/venv/Scripts/python.exe scripts/seed_demo_data.py
（settings 会自行加载 backend/.env）
"""
import os
import sys

# 使 backend 模块可导入（config/medical_business/core 均为 backend 内包）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

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
    verify()
