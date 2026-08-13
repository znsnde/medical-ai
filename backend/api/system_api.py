"""
系统信息与统计 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import patient_crud, record_crud, report_crud, user_crud
from core.security import get_current_user
from utils.common import resp_success

router = APIRouter()


@router.get("/info", summary="获取系统信息")
def get_system_info(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 仅管理员可查看
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可查看系统信息")

    total_patients = patient_crud.get_patient_count(db)
    total_records = record_crud.get_record_count(db)
    total_reports = report_crud.get_report_count(db)
    total_users = len(user_crud.get_user_list(db, 0, 9999))

    return resp_success(data={
        "version": "1.0.0",
        "system_name": "智慧医疗辅助诊断与电子病历结构化系统",
        "database": {
            "patients": total_patients,
            "records": total_records,
            "reports": total_reports,
            "users": total_users,
        },
        "current_user": {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role
        }
    })
