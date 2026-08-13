"""回收站模块：列出已软删患者/病历/报告，级联恢复，彻底删除（purge），清空回收站

所有操作仅 admin/doctor 可用（与患者/病历/报告删除权限一致）。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import patient_crud, record_crud, report_crud, recycle_crud
from core.security import require_roles
from utils.common import resp_success, resp_fail

router = APIRouter(dependencies=[Depends(require_roles(["admin", "doctor"]))])

# ── 回收站列表 ──
@router.get("/patients")
def list_deleted_patients(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    data = patient_crud.list_deleted_patients(db, skip, limit)
    return resp_success(data=data)

@router.get("/records")
def list_deleted_records(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    data = record_crud.list_deleted_records(db, skip, limit)
    return resp_success(data=data)

@router.get("/reports")
def list_deleted_reports(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    data = report_crud.list_deleted_reports(db, skip, limit)
    return resp_success(data=data)

# ── 级联恢复 ──
@router.post("/patient/{patient_id}/restore")
def restore_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = patient_crud.restore_patient(db, patient_id)
    if not patient:
        return resp_fail("回收站中不存在该患者")
    return resp_success(data=patient, msg="患者及病历/报告已恢复")

@router.post("/record/{record_id}/restore")
def restore_record(record_id: int, db: Session = Depends(get_db)):
    record = record_crud.restore_record(db, record_id)
    if not record:
        return resp_fail("回收站中不存在该病历")
    return resp_success(data=record, msg="病历及报告已恢复")

@router.post("/report/{report_id}/restore")
def restore_report(report_id: int, db: Session = Depends(get_db)):
    report = report_crud.restore_report(db, report_id)
    if not report:
        return resp_fail("回收站中不存在该报告")
    return resp_success(data=report, msg="报告已恢复")

# ── 彻底删除（purge）──
@router.delete("/patient/{patient_id}/purge")
def purge_patient(patient_id: int, db: Session = Depends(get_db)):
    if not patient_crud.purge_patient(db, patient_id):
        return resp_fail("删除失败，患者不存在")
    return resp_success(msg="患者已彻底删除")

@router.delete("/record/{record_id}/purge")
def purge_record(record_id: int, db: Session = Depends(get_db)):
    if not record_crud.purge_record(db, record_id):
        return resp_fail("删除失败，病历不存在")
    return resp_success(msg="病历已彻底删除")

@router.delete("/report/{report_id}/purge")
def purge_report(report_id: int, db: Session = Depends(get_db)):
    if not report_crud.purge_report(db, report_id):
        return resp_fail("删除失败，报告不存在")
    return resp_success(msg="报告已彻底删除")

# ── 清空回收站 ──
@router.delete("/clear")
def clear_recycle_bin(db: Session = Depends(get_db)):
    counts = recycle_crud.purge_all(db)
    return resp_success(data=counts, msg="回收站已清空")
