"""
病历结构化 + 多模态影像分析业务逻辑
文本清洗 → AI实体抽取结构化 → 影像分析 → 综合诊断 → 入库
"""
from sqlalchemy.orm import Session
from db.crud import record_crud
from core.entity_extract import extract_medical_entity, insert_knowledge_to_milvus
from core.multimodal_model import analyze_medical_image, generate_image_analysis_report
from core.diagnosis_agent import llm_combined_diagnosis
from utils.text_clean import clean_medical_text


def struct_medical_record(db: Session, patient_id: int, raw_text: str, dicom_path=""):
    """
    完整流程：
    1. 原始病历清洗
    2. AI实体抽取结构化数据
    3. 影像文件分析（如果有）
    4. LLM综合文本+影像给出诊断意见
    5. 存入MySQL
    6. 存入向量库
    """
    # 1. 文本清洗
    clean_txt = clean_medical_text(raw_text)

    # 2. AI抽取症状、病史、诊断实体
    struct_data = extract_medical_entity(clean_txt)

    # 3. 影像分析（如果有）
    image_analysis = ""
    if dicom_path:
        img_report = generate_image_analysis_report(dicom_path, clean_txt)
        image_analysis = img_report
    else:
        image_analysis = ""

    # 4. LLM综合文本 + 影像给出诊断意见
    combined_diagnosis = ""
    if dicom_path and image_analysis:
        combined_diagnosis = llm_combined_diagnosis(
            record_text=clean_txt,
            structured_data=struct_data,
            image_analysis=image_analysis
        )

    # 组装返回数据（extra字段存影像和综合诊断信息）
    result_data = {
        "structured_data": struct_data,
        "image_analysis": image_analysis,
        "combined_diagnosis": combined_diagnosis,
        "dicom_file_path": dicom_path
    }

    # 5. 写入数据库病历表
    record = record_crud.create_record(
        db=db,
        patient_id=patient_id,
        raw_text=raw_text,
        structured_data=struct_data,
        dicom_file_path=dicom_path
    )

    # 6. 将病历文本存入向量库
    insert_knowledge_to_milvus(clean_txt)

    # 返回包含影像分析的完整结果
    return result_data
