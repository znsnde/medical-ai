"""
系统信息与统计 API
"""
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import patient_crud, record_crud, report_crud, user_crud
from core.security import get_current_user
from core.logger import get_log_file_path
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


# 审计日志行：2026-08-12 09:56:02,886 [INFO] audit: [审计] 登录成功 username=admin role=admin
# 注意 logger name 与冒号相连（audit:），故用 \S+: 匹配
_AUDIT_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(\w+)\] \S+: (\[审计\].*)$"
)


def _rot_num(p: Path) -> int:
    """滚动备份编号（backend.log.1 → 1）；无后缀按 0（当前文件）"""
    m = re.search(r"\.(\d+)$", p.name)
    return int(m.group(1)) if m else 0


def _read_audit_lines(level: str = "", keyword: str = "") -> list:
    """读 logs/backend.log（含滚动备份 .N，编号越大越旧）解析审计行，返回最新在前"""
    log_path = Path(get_log_file_path())
    backups = sorted(log_path.parent.glob(log_path.name + ".*"), key=_rot_num, reverse=True)
    files = backups + [log_path]  # 旧 → 新

    lines: list = []
    for f in files:
        if not f.is_file():
            continue
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                lines.extend(fh.readlines())
        except OSError:
            continue

    audit: list = []
    for raw in lines:
        m = _AUDIT_LINE_RE.match(raw.rstrip("\r\n"))
        if not m:
            continue
        time_str, lvl, msg = m.groups()
        if level and lvl.lower() != level.lower():
            continue
        if keyword and keyword not in msg:
            continue
        audit.append({"time": time_str, "level": lvl, "message": msg})
    audit.reverse()  # 最新在前
    return audit


@router.get("/audit", summary="审计日志查询")
def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    level: str = "",
    keyword: str = "",
    current_user=Depends(get_current_user),
):
    # 仅管理员可查看审计日志
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可查看审计日志")

    items = _read_audit_lines(level=level.strip(), keyword=keyword.strip())
    total = len(items)
    skip = max(0, skip)
    limit = max(1, min(limit, 500))
    return resp_success(data={"total": total, "items": items[skip:skip + limit]})
