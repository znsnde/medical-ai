from sqlalchemy.orm import Session
from db.crud import report_crud, record_crud, patient_crud
from utils.pdf_export import generate_diagnosis_pdf

def create_diagnosis_pdf_report(db: Session, report_id: int):
    """读取报告+病历+患者信息，生成PDF文件并更新数据库路径"""
    report = report_crud.get_report_by_id(db, report_id)
    if not report:
        return None, "报告不存在"
    record = record_crud.get_record_by_id(db, report.record_id)
    patient = patient_crud.get_patient_by_id(db, record.patient_id)
    # 组装报告数据
    report_info = {
        "patient_name": patient.name,
        "record_text": record.raw_text,
        "image_analysis": report.image_analysis,
        "diagnosis_suggest": report.diagnosis_suggest
    }
    # 生成PDF
    full_path, rel_path = generate_diagnosis_pdf("report", report_info)
    # 更新数据库PDF存储路径
    updated_report = report_crud.update_report_pdf(db, report_id, rel_path)
    return updated_report, full_path