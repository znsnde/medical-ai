from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import record_crud
from medical_business import medical_record_struct
from utils.file_util import get_unique_save_path
from core.security import require_roles
from utils.common import resp_success, resp_fail

router = APIRouter(dependencies=[Depends(require_roles(["admin", "doctor"]))])

# 测试连通接口（静态路由必须在动态之前）
@router.get("/test")
def record_test():
    return resp_success(msg="病历结构化模块接口可用")

# 查询患者全部病历
@router.get("/patient/{patient_id}")
def list_patient_record(patient_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    record_list = record_crud.get_record_by_patient(db, patient_id, skip, limit)
    return resp_success(data=record_list)

# 病历结构化上传接口（支持文本+影像多模态）
@router.post("/struct")
async def upload_struct_record(
    patient_id: int = Form(...),
    raw_text: str = Form(...),
    image_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # 如果有影像文件则保存
    dicom_path = ""
    if image_file and image_file.filename:
        full_path, rel_path = get_unique_save_path("dicom", image_file.filename)
        with open(full_path, "wb") as f:
            f.write(await image_file.read())
        dicom_path = full_path

    record = medical_record_struct.struct_medical_record(
        db, patient_id, raw_text, dicom_path
    )
    return resp_success(data=record, msg="病历结构化完成")

# 删除病历
@router.delete("/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    ok = record_crud.delete_record(db, record_id)
    if not ok:
        return resp_fail("病历不存在或删除失败")
    return resp_success(msg="病历已移入回收站，可在回收站恢复")

# 分页查询全部病历
@router.get("/list/all")
def list_all_record(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    record_list = record_crud.get_record_list(db, skip, limit)
    return resp_success(data=record_list)

# 根据ID查询单条病历
@router.get("/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = record_crud.get_record_by_id(db, record_id)
    if not record:
        return resp_fail("病历不存在")
    return resp_success(data=record)
