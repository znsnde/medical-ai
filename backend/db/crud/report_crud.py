from sqlalchemy.orm import Session
from db.models import DiagnosisReport
from datetime import datetime

# 新建诊断报告
def create_report(
    db: Session,
    record_id: int,
    image_analysis: str,
    diagnosis_suggest: str,
    pdf_path: str = ""
):
    db_obj = DiagnosisReport(
        record_id=record_id,
        image_analysis=image_analysis,
        diagnosis_suggest=diagnosis_suggest,
        pdf_path=pdf_path,
        create_time=datetime.now()
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 根据报告ID查询
def get_report_by_id(db: Session, report_id: int):
    return db.query(DiagnosisReport).filter(DiagnosisReport.id == report_id).first()

# 根据病历ID查询对应报告
def get_report_by_record(db: Session, record_id: int):
    return db.query(DiagnosisReport).filter(DiagnosisReport.record_id == record_id).all()

# 分页查询所有报告
def get_report_list(db: Session, skip: int = 0, limit: int = 20):
    return db.query(DiagnosisReport).offset(skip).limit(limit).all()

# 更新报告PDF路径
def update_report_pdf(db: Session, report_id: int, pdf_path: str):
    report = get_report_by_id(db, report_id)
    if not report:
        return None
    report.pdf_path = pdf_path
    db.commit()
    db.refresh(report)
    return report

# 删除报告
def delete_report(db: Session, report_id: int):
    report = get_report_by_id(db, report_id)
    if not report:
        return False
    db.delete(report)
    db.commit()
    return True

# 获取报告总数
def get_report_count(db: Session) -> int:
    return db.query(DiagnosisReport).count()

# 更新报告PDF内容字段（用于 dashboard 展示）
def update_report_content(db: Session, report_id: int,
                          image_analysis: str = None,
                          diagnosis_suggest: str = None):
    report = get_report_by_id(db, report_id)
    if not report:
        return None
    if image_analysis is not None:
        report.image_analysis = image_analysis
    if diagnosis_suggest is not None:
        report.diagnosis_suggest = diagnosis_suggest
    db.commit()
    db.refresh(report)
    return report