"""回收站聚合操作：清空回收站（purge_all）"""
from sqlalchemy.orm import Session
from db.models import Patient, MedicalRecord, DiagnosisReport
from utils.file_util import safe_unlink


def _collect_record_files(db: Session, rec: MedicalRecord):
    """收集并删除一个病历的物理文件（DICOM + 其全部报告的 PDF）"""
    if rec.dicom_file_path:
        safe_unlink(rec.dicom_file_path)
    for rep in db.query(DiagnosisReport).filter(DiagnosisReport.record_id == rec.id).all():
        if rep.pdf_path:
            safe_unlink(rep.pdf_path)


# 清空回收站：只处理 is_deleted==1 的行，自底向上物理删除，先收集文件路径（避免父行级联删除后子行路径丢失）
def purge_all(db: Session) -> dict:
    patients = db.query(Patient).filter(Patient.is_deleted == 1).all()
    records = db.query(MedicalRecord).filter(MedicalRecord.is_deleted == 1).all()
    reports = db.query(DiagnosisReport).filter(DiagnosisReport.is_deleted == 1).all()

    # 1. 文件清理（幂等：safe_unlink 吞 OSError，重复清理无害）
    for rep in reports:
        if rep.pdf_path:
            safe_unlink(rep.pdf_path)
    for rec in records:
        _collect_record_files(db, rec)
    # 软删患者可能带 alive 子行（级联删除会物理清除它们），补收其文件
    for pat in patients:
        for rec in db.query(MedicalRecord).filter(MedicalRecord.patient_id == pat.id).all():
            _collect_record_files(db, rec)

    # 2. 自底向上物理删除（report → record → patient，FK CASCADE 兜底子行）
    for rep in reports:
        db.delete(rep)
    for rec in records:
        db.delete(rec)
    for pat in patients:
        db.delete(pat)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"patients": len(patients), "records": len(records), "reports": len(reports)}
