from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import report_crud
from medical_business import report_generator
from core.security import require_roles
from utils.common import resp_success, resp_fail

router = APIRouter(dependencies=[Depends(require_roles(["admin", "doctor"]))])

# 根据报告ID生成PDF诊断报告
@router.post("/pdf/generate")
def build_report_pdf(report_id: int = Query(..., description="诊断报告ID"), db: Session = Depends(get_db)):
    report, pdf_path = report_generator.create_diagnosis_pdf_report(db, report_id)
    if not report:
        return resp_fail(pdf_path)
    # 生成HTTP可访问的PDF链接（相对路径：前端同源经 nginx / 开发代理访问，避免硬编码 127.0.0.1 在容器/局域网失效）
    pdf_rel = report.pdf_path.replace("\\", "/") if report.pdf_path else ""
    pdf_url = f"/{pdf_rel}" if pdf_rel else ""
    return resp_success(
        data={
            "report_info": report,
            "pdf_file_path": pdf_path,
            "pdf_url": pdf_url
        },
        msg="PDF诊断报告生成完成"
    )

# 获取报告PDF访问路径
@router.get("/pdf/{report_id}")
def get_report_pdf(report_id: int, db: Session = Depends(get_db)):
    report = report_crud.get_report_by_id(db, report_id)
    if not report:
        return resp_fail("报告不存在")
    if not report.pdf_path:
        return resp_fail("该报告尚未生成PDF文件")
    pdf_url = report.pdf_path.replace("\\", "/")
    return resp_success(data={"pdf_url": f"/{pdf_url}"})

# 模块连通测试接口
@router.get("/test")
def report_test():
    return resp_success(msg="诊断报告生成模块接口可用")