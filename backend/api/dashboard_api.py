from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import patient_crud, record_crud, report_crud
from core.security import get_current_user
from utils.common import resp_success

router = APIRouter()

@router.get("/stats", summary="获取仪表盘统计数据")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 基础统计
    total_patients = patient_crud.get_patient_count(db)
    total_records = record_crud.get_record_count(db)
    total_reports = report_crud.get_report_count(db)
    today_records = record_crud.get_today_record_count(db)

    # 近期趋势（近7天）
    recent_records = record_crud.get_recent_record_stats(db, days=7)

    # 疾病分布 TOP5
    disease_top = record_crud.get_disease_distribution(db, top_n=5)

    return resp_success(data={
        "total_patients": total_patients,
        "total_records": total_records,
        "total_reports": total_reports,
        "today_records": today_records,
        "recent_records": recent_records,
        "disease_top": disease_top,
        "current_user": {
            "id": current_user.id,
            "username": current_user.username,
            "real_name": current_user.real_name,
            "role": current_user.role,
            "department": current_user.department
        }
    }, msg="获取成功")
