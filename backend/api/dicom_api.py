"""
DICOM 医学影像在线预览 API
提供 DICOM → PNG 图像转换和元数据查询
"""
import os
from io import BytesIO

import numpy as np
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from pydicom import dcmread
from PIL import Image

from db.session import get_db
from db.crud import record_crud
from core.security import get_current_user, require_roles

router = APIRouter(dependencies=[Depends(require_roles(["admin", "doctor"]))])


def _dicom_to_png_bytes(dcm_path: str, window_width: float = None,
                        window_center: float = None) -> bytes:
    """
    将 DICOM 文件像素数据转换为 PNG 字节流
    支持窗宽/窗位调整
    """
    if not os.path.exists(dcm_path):
        raise HTTPException(status_code=404, detail="DICOM 文件不存在")

    ds = dcmread(dcm_path, force=True)

    # 尝试获取像素数据
    try:
        pixel_array = ds.pixel_array
    except Exception as e:
        # 生成一个提示图片代替
        img = Image.new("L", (512, 512), color=40)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((100, 220), "DICOM Pixel Data", fill=200)
        draw.text((100, 250), "Not Available", fill=180)
        draw.text((100, 280), f"({type(e).__name__})", fill=140)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    # 多帧 DICOM – 只取第一帧
    if pixel_array.ndim > 2:
        pixel_array = pixel_array[0]

    # 获取窗宽窗位
    if window_width is None or window_center is None:
        try:
            window_center = float(ds.WindowCenter)
        except (AttributeError, ValueError, TypeError):
            window_center = pixel_array.mean()
        try:
            window_width = float(ds.WindowWidth)
        except (AttributeError, ValueError, TypeError):
            window_width = pixel_array.max() - pixel_array.min()
        if window_width <= 0:
            window_width = pixel_array.max() - pixel_array.min() or 1

    # 应用窗宽窗位
    img_min = window_center - window_width / 2
    img_max = window_center + window_width / 2
    pixel_array = np.clip(pixel_array, img_min, img_max)

    # 归一化到 0-255
    pixel_range = img_max - img_min
    if pixel_range > 0:
        pixel_array = ((pixel_array - img_min) / pixel_range * 255).astype(np.uint8)
    else:
        pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)

    # 转为 PIL Image → PNG 字节流
    img = Image.fromarray(pixel_array)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ── 预览接口：返回 PNG 图片流 ──
@router.get("/preview/{record_id}", summary="获取 DICOM 影像预览图")
def dicom_preview(
    record_id: int,
    window_width: float = Query(None, description="窗宽"),
    window_center: float = Query(None, description="窗位"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    record = record_crud.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="病历不存在")
    if not record.dicom_file_path or not os.path.exists(record.dicom_file_path):
        raise HTTPException(status_code=404, detail="该病历无关联的 DICOM 影像文件")

    png_bytes = _dicom_to_png_bytes(record.dicom_file_path, window_width, window_center)
    return Response(content=png_bytes, media_type="image/png")


# ── 元数据接口：返回 DICOM 标签信息 ──
@router.get("/metadata/{record_id}", summary="获取 DICOM 影像元数据")
def dicom_metadata(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    record = record_crud.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="病历不存在")
    if not record.dicom_file_path or not os.path.exists(record.dicom_file_path):
        raise HTTPException(status_code=404, detail="该病历无关联的 DICOM 影像文件")

    ds = dcmread(record.dicom_file_path, force=True)

    # 提取常见标签
    metadata = {
        "patient_name": str(getattr(ds, "PatientName", "未知")),
        "patient_id": str(getattr(ds, "PatientID", "未知")),
        "patient_sex": str(getattr(ds, "PatientSex", "未知")),
        "patient_age": str(getattr(ds, "PatientAge", "未知")),
        "study_date": str(getattr(ds, "StudyDate", "未知")),
        "study_time": str(getattr(ds, "StudyTime", "未知")),
        "modality": str(getattr(ds, "Modality", "未知")),
        "study_description": str(getattr(ds, "StudyDescription", "未知")),
        "series_description": str(getattr(ds, "SeriesDescription", "未知")),
        "body_part": str(getattr(ds, "BodyPartExamined", "未知")),
        "rows": int(getattr(ds, "Rows", 0)),
        "columns": int(getattr(ds, "Columns", 0)),
        "bits_allocated": int(getattr(ds, "BitsAllocated", 0)),
        "pixel_spacing": str(getattr(ds, "PixelSpacing", "未知")),
        "window_center": str(getattr(ds, "WindowCenter", "未知")),
        "window_width": str(getattr(ds, "WindowWidth", "未知")),
        "institution": str(getattr(ds, "InstitutionName", "未知")),
        "manufacturer": str(getattr(ds, "Manufacturer", "未知")),
    }
    return JSONResponse(content=metadata)
