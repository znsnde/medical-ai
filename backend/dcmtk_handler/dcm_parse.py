"""
DICOM医学影像文件解析模块
使用pydicom库读取DICOM文件的标签信息
"""
import os

try:
    import pydicom
    HAS_PYDICOM = True
except ImportError:
    HAS_PYDICOM = False


def parse_dicom_basic(dcm_path: str) -> dict:
    """
    解析DICOM文件基础标签信息
    返回患者信息、检查信息、影像参数等
    """
    if not HAS_PYDICOM:
        return {
            "modality": "DICOM",
            "analysis": "未安装pydicom库，无法解析DICOM标签",
            "abnormal_findings": []
        }

    if not os.path.exists(dcm_path):
        return {"error": f"DICOM文件不存在: {dcm_path}"}

    try:
        ds = pydicom.dcmread(dcm_path, force=True)
        result = {
            "modality": str(getattr(ds, "Modality", "未知")),
            "patient_name": str(getattr(ds, "PatientName", "未知")),
            "patient_id": str(getattr(ds, "PatientID", "未知")),
            "patient_sex": str(getattr(ds, "PatientSex", "未知")),
            "patient_age": str(getattr(ds, "PatientAge", "未知")),
            "study_date": str(getattr(ds, "StudyDate", "未知")),
            "study_description": str(getattr(ds, "StudyDescription", "未知")),
            "series_description": str(getattr(ds, "SeriesDescription", "未知")),
            "rows": str(getattr(ds, "Rows", "未知")),
            "columns": str(getattr(ds, "Columns", "未知")),
            "pixel_spacing": str(getattr(ds, "PixelSpacing", "未知")),
            "analysis": "DICOM标签解析完成",
            "abnormal_findings": []
        }
        return result
    except Exception as e:
        return {
            "modality": "DICOM",
            "error": f"DICOM解析失败: {str(e)}",
            "analysis": "DICOM文件解析异常",
            "abnormal_findings": []
        }
