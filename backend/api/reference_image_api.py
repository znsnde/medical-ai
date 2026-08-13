"""
典型病例参考影像查询 API
根据诊断关键词匹配展示对应的参考影像
"""
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from db.session import get_db
from db.crud import record_crud, report_crud
from core.security import get_current_user
from config.image_mapping import match_disease_image, DISEASE_IMAGE_MAP, IMAGE_DISPLAY_NAME

router = APIRouter()

# 参考影像存放目录
REF_IMAGE_DIR = Path(__file__).resolve().parent.parent / "static" / "reference_images"


@router.get("/list", summary="列出所有可用参考影像")
def list_reference_images(current_user=Depends(get_current_user)):
    """返回所有可用的参考影像列表"""
    images = []
    for filename, display_name in IMAGE_DISPLAY_NAME.items():
        filepath = REF_IMAGE_DIR / filename
        if filepath.exists():
            images.append({
                "filename": filename,
                "display_name": display_name,
                "size_kb": round(os.path.getsize(filepath) / 1024, 1)
            })
    return JSONResponse(content={
        "code": 200,
        "data": images
    })


@router.get("/by-record/{record_id}", summary="根据病历ID返回匹配的参考影像")
def get_reference_by_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    根据病历ID:
    1. 查找该病历关联的诊断报告中的诊断建议
    2. 匹配关键词 → 找到对应参考影像
    3. 返回影像文件和诊断信息
    """
    record = record_crud.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="病历不存在")

    # 从病历的结构化数据中提取诊断
    diagnosis_text = ""
    if record.structured_data:
        if isinstance(record.structured_data, dict):
            diag_list = record.structured_data.get("diagnosis", [])
            if diag_list and isinstance(diag_list, list):
                diagnosis_text = "、".join(diag_list)

    # 如果病历的结构化数据没有诊断，尝试从诊断报告中获取
    if not diagnosis_text:
        reports = report_crud.get_report_by_record(db, record_id)
        if reports:
            diagnosis_text = reports[0].diagnosis_suggest or ""

    # 匹配影像 - 自动适配 jpg/png 格式
    matched_file = match_disease_image(diagnosis_text)
    filepath = REF_IMAGE_DIR / matched_file

    # 如果 .jpg 不存在，尝试 .png
    if not filepath.exists():
        alt_file = matched_file.rsplit(".", 1)[0] + ".png"
        filepath = REF_IMAGE_DIR / alt_file
        if filepath.exists():
            matched_file = alt_file

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="参考影像文件不存在")

    display_name = IMAGE_DISPLAY_NAME.get(matched_file,
                    IMAGE_DISPLAY_NAME.get(matched_file.rsplit(".", 1)[0] + ".jpg",
                    IMAGE_DISPLAY_NAME.get(matched_file.rsplit(".", 1)[0] + ".png", matched_file)))

    # 返回影像文件 + 自定义 header（中文需URL编码）
    return FileResponse(
        path=str(filepath),
        media_type="image/png",
        headers={
            "X-Image-Diagnosis": quote(diagnosis_text[:200] or "no_diagnosis"),
            "X-Image-Display-Name": quote(display_name),
            "X-Image-Matched-File": quote(matched_file),
            "Access-Control-Expose-Headers": "X-Image-Diagnosis,X-Image-Display-Name,X-Image-Matched-File"
        }
    )
