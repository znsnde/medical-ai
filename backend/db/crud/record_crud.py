from sqlalchemy.orm import Session
from db.models import MedicalRecord
from datetime import datetime

# 新建病历
def create_record(
    db: Session,
    patient_id: int,
    raw_text: str,
    structured_data: dict,
    dicom_file_path: str = ""
):
    db_obj = MedicalRecord(
        patient_id=patient_id,
        raw_text=raw_text,
        structured_data=structured_data,
        dicom_file_path=dicom_file_path,
        create_time=datetime.now()
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 根据病历ID查询
def get_record_by_id(db: Session, record_id: int):
    return db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()

# 根据患者ID查询该患者所有病历
def get_record_by_patient(db: Session, patient_id: int, skip: int = 0, limit: int = 20):
    return db.query(MedicalRecord)\
        .filter(MedicalRecord.patient_id == patient_id)\
        .offset(skip).limit(limit).all()

# 分页查全部病历
def get_record_list(db: Session, skip: int = 0, limit: int = 20):
    return db.query(MedicalRecord).offset(skip).limit(limit).all()

# 更新病历结构化数据/影像路径
def update_record_struct(
    db: Session,
    record_id: int,
    structured_data: dict = None,
    dicom_file_path: str = None
):
    record = get_record_by_id(db, record_id)
    if not record:
        return None
    if structured_data is not None:
        record.structured_data = structured_data
    if dicom_file_path is not None:
        record.dicom_file_path = dicom_file_path
    db.commit()
    db.refresh(record)
    return record

# 删除病历
def delete_record(db: Session, record_id: int):
    record = get_record_by_id(db, record_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True

# ── 统计方法 ──

# 获取病历总数
def get_record_count(db: Session) -> int:
    return db.query(MedicalRecord).count()

# 获取今日新增病历数
def get_today_record_count(db: Session) -> int:
    from datetime import date
    today = date.today()
    return db.query(MedicalRecord).filter(
        MedicalRecord.create_time >= str(today)
    ).count()

# 获取最近 N 天的每日病历数
def get_recent_record_stats(db: Session, days: int = 7):
    from datetime import datetime, timedelta
    from sqlalchemy import func
    start_date = datetime.now() - timedelta(days=days - 1)
    results = db.query(
        func.date(MedicalRecord.create_time).label("date"),
        func.count(MedicalRecord.id).label("count")
    ).filter(MedicalRecord.create_time >= start_date).group_by(
        func.date(MedicalRecord.create_time)
    ).all()
    return [{"date": str(r.date), "count": r.count} for r in results]

# 提取疾病分布（从结构化数据的 diagnosis 字段）
def get_disease_distribution(db: Session, top_n: int = 5):
    from sqlalchemy import func
    from datetime import datetime
    import json
    from db.models import DiseaseDict

    # 获取所有病历的结构化数据
    records = db.query(MedicalRecord.structured_data).all()
    disease_count = {}

    for (structured_data,) in records:
        if not structured_data:
            continue
        # 兼容 dict 和 str 类型
        if isinstance(structured_data, str):
            try:
                structured_data = json.loads(structured_data)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(structured_data, dict):
            continue
        diagnoses = structured_data.get("diagnosis", [])
        if not diagnoses or not isinstance(diagnoses, list):
            continue
        for d in diagnoses:
            d = d.strip()
            if d:
                # 尝试通过疾病字典标准化
                standardized = d
                disease_dict = db.query(DiseaseDict).filter(
                    DiseaseDict.keyword == d
                ).first()
                if disease_dict:
                    standardized = disease_dict.disease_name
                disease_count[standardized] = disease_count.get(standardized, 0) + 1

    # 排序取 top_n
    sorted_diseases = sorted(disease_count.items(), key=lambda x: -x[1])[:top_n]
    return [{"name": name, "count": count} for name, count in sorted_diseases]