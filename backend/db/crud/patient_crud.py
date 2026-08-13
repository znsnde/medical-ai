from sqlalchemy.orm import Session
from db.models import Patient
from datetime import datetime

# 新增患者
def create_patient(
    db: Session,
    name: str,
    age: int,
    gender: str,
    phone: str
):
    db_obj = Patient(
        name=name,
        age=age,
        gender=gender,
        phone=phone,
        create_time=datetime.now()
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 根据id单条查询患者
def get_patient_by_id(db: Session, patient_id: int):
    return db.query(Patient).filter(Patient.id == patient_id).first()

# 分页查询所有患者
def get_patient_list(db: Session, skip: int = 0, limit: int = 20):
    return db.query(Patient).offset(skip).limit(limit).all()

# 修改患者信息
def update_patient(
    db: Session,
    patient_id: int,
    name: str = None,
    age: int = None,
    gender: str = None,
    phone: str = None
):
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return None
    if name is not None:
        patient.name = name
    if age is not None:
        patient.age = age
    if gender is not None:
        patient.gender = gender
    if phone is not None:
        patient.phone = phone
    db.commit()
    db.refresh(patient)
    return patient

# 删除患者
def delete_patient(db: Session, patient_id: int):
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return False
    db.delete(patient)
    db.commit()
    return True

# 获取患者总数
def get_patient_count(db: Session) -> int:
    return db.query(Patient).count()
