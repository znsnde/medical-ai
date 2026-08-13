"""
辅助诊断业务逻辑
使用LLM进行智能诊断，结合影像分析、知识库检索与知识图谱
"""
from sqlalchemy.orm import Session
from db.crud import record_crud, report_crud
from core.medical_rag import rag_search_medical_knowledge
from core.diagnosis_agent import llm_generate_diagnosis
from core.multimodal_model import generate_image_analysis_report
from medical_business.knowledge_graph import search_for_diagnosis
from utils.common import resp_success, resp_fail


def get_assist_diagnosis(db: Session, record_id: int):
    """
    完整诊断流程：
    1. 读取病历 + 影像
    2. RAG检索相似临床指南
    3. LLM生成诊断建议
    4. 知识图谱查询关联医学知识
    5. 存入数据库
    返回 (report, msg, knowledge)
    """
    # 1. 读取病历
    record = record_crud.get_record_by_id(db, record_id)
    if not record:
        return None, "未找到该病历"

    # 2. 影像分析（如果有）
    image_analysis = ""
    if record.dicom_file_path:
        image_analysis = generate_image_analysis_report(
            record.dicom_file_path,
            record.raw_text
        )

    # 3. 知识库检索
    match_knowledge = rag_search_medical_knowledge(record.raw_text, top_k=3)

    # 4. LLM生成诊断建议（有影像分析时一并纳入考虑）
    structured = record.structured_data or {}
    suggest = llm_generate_diagnosis(
        record_text=record.raw_text,
        structured_data=structured,
        reference_knowledge=match_knowledge,
        image_analysis=image_analysis
    )

    # 5. 知识图谱查询关联医学知识（相关疾病/用药相互作用/并发症）
    medicines = structured.get("medicine", []) if isinstance(structured, dict) else []
    knowledge = search_for_diagnosis(suggest, medicines=medicines)

    # 6. 保存诊断报告
    report = report_crud.create_report(
        db=db,
        record_id=record_id,
        image_analysis=image_analysis or "暂无影像分析",
        diagnosis_suggest=suggest
    )
    return report, "诊断生成成功", knowledge
