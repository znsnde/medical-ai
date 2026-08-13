from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import report_crud, record_crud, patient_crud
from medical_business import report_generator
from core.security import require_roles, get_current_user
from config.settings import settings
from utils.common import resp_success, resp_fail

router = APIRouter()


def _require_doctor(user):
    """医生侧操作（生成/查询/连通）：仅 admin/doctor，否则 HTTP 403"""
    if user.role not in ("admin", "doctor"):
        raise HTTPException(status_code=403, detail="需要 admin/doctor 角色")


def _patient_owns_report(db: Session, report, user) -> bool:
    """患者是否本人报告：report → record → patient.user_id == user.id"""
    if not report:
        return False
    record = record_crud.get_record_by_id(db, report.record_id)
    if not record:
        return False
    patient = patient_crud.get_patient_by_id(db, record.patient_id)
    return bool(patient and patient.user_id == user.id)

# 根据报告ID生成PDF诊断报告
@router.post("/pdf/generate")
def build_report_pdf(
    report_id: int = Query(..., description="诊断报告ID"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_doctor(user)
    report, pdf_path = report_generator.create_diagnosis_pdf_report(db, report_id)
    if not report:
        return resp_fail(pdf_path)
    # PDF 一律经受控下载接口访问（带鉴权），不再暴露公开 /static 路径
    return resp_success(
        data={
            "report_info": report,
            "pdf_file_path": pdf_path,
            "pdf_url": f"/api/report/pdf/download/{report_id}"
        },
        msg="PDF诊断报告生成完成"
    )

# 获取报告PDF访问路径（返回受控下载接口，前端经此带 token 获取）
@router.get("/pdf/{report_id}")
def get_report_pdf(report_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _require_doctor(user)
    report = report_crud.get_report_by_id(db, report_id)
    if not report:
        return resp_fail("报告不存在")
    if not report.pdf_path:
        return resp_fail("该报告尚未生成PDF文件")
    return resp_success(data={"pdf_url": f"/api/report/pdf/download/{report_id}"})

# 受控下载：报告PDF
# 权限：admin/doctor 直接放行；患者仅可下载本人报告（report→record→patient.user_id==当前用户），
# 其余（他人报告/未绑定）→ HTTP 403；匿名 → 401（get_current_user 拦截）
@router.get("/pdf/download/{report_id}")
def download_report_pdf(report_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    report = report_crud.get_report_by_id(db, report_id)
    if not report or not report.pdf_path:
        return resp_fail("报告或PDF不存在")
    if user.role not in ("admin", "doctor"):
        if not _patient_owns_report(db, report, user):
            raise HTTPException(status_code=403, detail="无权访问该报告")
    # 从存库路径安全重建：取 parent 子目录名 + 文件名（兼容旧绝对路径/相对路径，防路径穿越）
    p = Path(report.pdf_path)
    file_path = Path(settings.UPLOAD_PATH) / p.parent.name / p.name
    if not file_path.is_file():
        return resp_fail("PDF文件不存在")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"诊断报告_{report_id}.pdf"
    )

# 模块连通测试接口
@router.get("/test")
def report_test(user=Depends(get_current_user)):
    _require_doctor(user)
    return resp_success(msg="诊断报告生成模块接口可用")