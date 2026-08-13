from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import patient_crud, record_crud, report_crud
from medical_business import patient_follow
from core.security import require_roles, get_current_user
from utils.common import resp_success, resp_fail

# 公开路由（无需角色限制）
router = APIRouter()

# 受保护路由（仅 admin/doctor）
protected = APIRouter(dependencies=[Depends(require_roles(["admin", "doctor"]))])

@router.get("/test")
def patient_test():
    return resp_success(msg="患者随访&问答模块接口可用")

# ── 患者个人信息（患者本人可查） ──
@router.get("/my-profile")
def my_profile(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != "patient":
        return resp_fail("仅患者可访问")
    patients = patient_crud.get_patient_list(db, 0, 9999)
    my = [p for p in patients if p.user_id == user.id]
    if not my:
        return resp_success(data=None, msg="未找到关联的患者信息")
    return resp_success(data=my[0])

# ── 患者本人病历（患者可查自己的病历） ──
@router.get("/my-records")
def my_records(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != "patient":
        return resp_fail("仅患者可访问")
    patients = patient_crud.get_patient_list(db, 0, 9999)
    my_patient = next((p for p in patients if p.user_id == user.id), None)
    if not my_patient:
        return resp_success(data=[], msg="未找到关联信息")
    records = record_crud.get_record_by_patient(db, my_patient.id, 0, 50)
    result = []
    for r in records:
        result.append({"id": r.id, "raw_text": r.raw_text, "structured_data": r.structured_data,
                       "create_time": str(r.create_time)[:19] if r.create_time else ""})
    return resp_success(data=result)

@router.post("/chat")
def patient_chat(question: str = Form(...)):
    answer = patient_follow.patient_qa_chat(question)
    return resp_success(data={"answer": answer}, msg="问答检索完成")

@protected.get("/list/all")
def list_patient(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    data = patient_crud.get_patient_list(db, skip, limit)
    return resp_success(data=data)

@protected.post("/add")
def add_patient(
    name: str = Form(...), age: int = Form(...),
    gender: str = Form(...), phone: str = Form(...),
    db: Session = Depends(get_db)
):
    patient = patient_crud.create_patient(db, name, age, gender, phone)
    return resp_success(data=patient, msg="患者新增成功")

@protected.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = patient_crud.get_patient_by_id(db, patient_id)
    if not patient:
        return resp_fail("患者不存在")
    return resp_success(data=patient)

@protected.put("/update/{patient_id}")
def update_patient_info(
    patient_id: int, name: str = Form(None), age: int = Form(None),
    gender: str = Form(None), phone: str = Form(None),
    db: Session = Depends(get_db)
):
    patient = patient_crud.update_patient(db, patient_id, name, age, gender, phone)
    if not patient:
        return resp_fail("患者不存在，修改失败")
    return resp_success(data=patient, msg="患者信息更新成功")

@protected.delete("/{patient_id}")
def del_patient(patient_id: int, db: Session = Depends(get_db)):
    flag = patient_crud.delete_patient(db, patient_id)
    if not flag:
        return resp_fail("删除失败，患者不存在")
    return resp_success(msg="患者删除成功")
