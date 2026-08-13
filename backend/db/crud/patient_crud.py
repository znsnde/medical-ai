from sqlalchemy.orm import Session
from db.models import Patient, MedicalRecord, DiagnosisReport
from datetime import datetime
from utils.file_util import safe_unlink

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

# 根据用户ID查询关联患者（患者自助：账号认领档案后按 user_id 匹配）
def get_patient_by_user_id(db: Session, user_id: int):
    return db.query(Patient).filter(Patient.user_id == user_id).first()

# 根据手机号查询患者（患者认领档案用；空号直接返回 None，避免误匹配全空行）
# 同号多档时按 id 升序取最早建档者，保证绑定结果确定
def get_patient_by_phone(db: Session, phone: str):
    if not phone:
        return None
    return db.query(Patient).filter(Patient.phone == phone).order_by(Patient.id.asc()).first()

# 绑定患者档案到登录账号（认领成功设置 user_id；已绑定的档案不可重复认领）
def bind_patient(db: Session, patient_id: int, user_id: int):
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return None
    patient.user_id = user_id
    db.commit()
    db.refresh(patient)
    return patient

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

# 删除患者（CASCADE 会清其病历/报告行，故删行前先收集整条子链的物理文件路径一并清理）
def delete_patient(db: Session, patient_id: int):
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return False
    for rec in db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).all():
        if rec.dicom_file_path:
            safe_unlink(rec.dicom_file_path)
        for rep in db.query(DiagnosisReport).filter(DiagnosisReport.record_id == rec.id).all():
            if rep.pdf_path:
                safe_unlink(rep.pdf_path)
    db.delete(patient)
    db.commit()
    return True

# 获取患者总数
def get_patient_count(db: Session) -> int:
    return db.query(Patient).count()
