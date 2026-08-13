from sqlalchemy.orm import Session
from db.models import DiagnosisReport
from datetime import datetime
from utils.file_util import safe_unlink

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
    return db.query(DiagnosisReport).filter(
        DiagnosisReport.id == report_id, DiagnosisReport.is_deleted == 0).first()

# 根据病历ID查询对应报告
def get_report_by_record(db: Session, record_id: int):
    return db.query(DiagnosisReport).filter(
        DiagnosisReport.record_id == record_id,
        DiagnosisReport.is_deleted == 0).all()

# 分页查询所有报告
def get_report_list(db: Session, skip: int = 0, limit: int = 20):
    return db.query(DiagnosisReport).filter(DiagnosisReport.is_deleted == 0)\
        .offset(skip).limit(limit).all()

# 更新报告PDF路径
def update_report_pdf(db: Session, report_id: int, pdf_path: str):
    report = get_report_by_id(db, report_id)
    if not report:
        return None
    report.pdf_path = pdf_path
    db.commit()
    db.refresh(report)
    return report

# 软删除报告（文件保留以便恢复），单事务
def delete_report(db: Session, report_id: int):
    report = db.query(DiagnosisReport).filter(
        DiagnosisReport.id == report_id, DiagnosisReport.is_deleted == 0).first()
    if not report:
        return False
    report.soft_delete()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True

# 恢复单条报告
def restore_report(db: Session, report_id: int):
    report = db.query(DiagnosisReport).filter(
        DiagnosisReport.id == report_id, DiagnosisReport.is_deleted == 1).first()
    if not report:
        return None
    report.restore()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(report)
    return report

# 彻底删除报告（回收站 purge）：连带清理物理 PDF，避免文件泄露/磁盘膨胀
def purge_report(db: Session, report_id: int):
    report = db.query(DiagnosisReport).filter(DiagnosisReport.id == report_id).first()
    if not report:
        return False
    if report.pdf_path:
        safe_unlink(report.pdf_path)
    db.delete(report)
    db.commit()
    return True

# 回收站：分页查询已删除报告
def list_deleted_reports(db: Session, skip: int = 0, limit: int = 20):
    return db.query(DiagnosisReport).filter(DiagnosisReport.is_deleted == 1)\
        .order_by(DiagnosisReport.deleted_at.desc(), DiagnosisReport.id.desc())\
        .offset(skip).limit(limit).all()

# 获取报告总数
def get_report_count(db: Session) -> int:
    return db.query(DiagnosisReport).filter(DiagnosisReport.is_deleted == 0).count()

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