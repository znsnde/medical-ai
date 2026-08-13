from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import report_crud, record_crud, patient_crud
from medical_business import assist_diagnosis
from medical_business.knowledge_graph import search_for_diagnosis
from core.security import require_roles, get_current_user
from core.logger import get_logger
from utils.common import resp_success, resp_fail

logger = get_logger("audit")

router = APIRouter(dependencies=[Depends(require_roles(["admin", "doctor"]))])


def _enrich_report(report, db: Session):
    """为报告对象附加患者姓名和 DICOM 路径"""
    if report is None:
        return None
    record = record_crud.get_record_by_id(db, report.record_id) if report.record_id else None
    patient = patient_crud.get_patient_by_id(db, record.patient_id) if record else None
    data = {
        "id": report.id,
        "record_id": report.record_id,
        "image_analysis": report.image_analysis,
        "diagnosis_suggest": report.diagnosis_suggest,
        "pdf_path": report.pdf_path or "",
        "create_time": str(report.create_time)[:19] if report.create_time else "",
        "patient_name": patient.name if patient else "未知",
        "dicom_file_path": record.dicom_file_path if record else ""
    }
    return data


# 分页查询所有诊断报告（静态路由必须在动态之前）
@router.get("/list/all")
def list_all_report(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    reports = report_crud.get_report_list(db, skip, limit)
    data = [_enrich_report(r, db) for r in reports]
    return resp_success(data=data)

# 根据病历ID查询对应诊断报告
@router.get("/list/record/{record_id}")
def list_report_by_record(record_id: int, db: Session = Depends(get_db)):
    reports = report_crud.get_report_by_record(db, record_id)
    data = [_enrich_report(r, db) for r in reports]
    return resp_success(data=data)

# 模块连通测试接口
@router.get("/test")
def diagnosis_test():
    return resp_success(msg="AI辅助诊断模块接口可用")

# 根据病历ID生成AI辅助诊断报告
@router.post("/generate")
def generate_diagnosis(record_id: int = Query(..., description="病历ID"),
                       db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    logger.info("[审计] 生成诊断 record_id=%s operator=%s", record_id, current_user.username)
    report, msg, knowledge = assist_diagnosis.get_assist_diagnosis(db, record_id)
    if not report:
        logger.warning("[审计] 诊断生成失败 record_id=%s operator=%s 原因=%s",
                       record_id, current_user.username, msg)
        return resp_fail(msg)
    enriched = _enrich_report(report, db)
    enriched["knowledge"] = knowledge
    return resp_success(data=enriched, msg=msg)

# 根据报告ID查询诊断详情
@router.get("/{report_id}")
def get_diagnosis_report(report_id: int, db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    report = report_crud.get_report_by_id(db, report_id)
    if not report:
        return resp_fail("诊断报告不存在")
    logger.info("[审计] 查看诊断报告 report_id=%s operator=%s", report_id, current_user.username)
    enriched = _enrich_report(report, db)
    # 详情页附带关联医学知识（按存档诊断文本 + 病历用药实时查询图谱）
    record = record_crud.get_record_by_id(db, report.record_id) if report.record_id else None
    structured = (record.structured_data or {}) if record else {}
    medicines = structured.get("medicine", []) if isinstance(structured, dict) else []
    enriched["knowledge"] = search_for_diagnosis(report.diagnosis_suggest or "", medicines=medicines)
    return resp_success(data=enriched)

# 删除诊断报告
@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    flag = report_crud.delete_report(db, report_id)
    if not flag:
        return resp_fail("删除失败，报告不存在")
    return resp_success(msg="报告已移入回收站，可在回收站恢复")
