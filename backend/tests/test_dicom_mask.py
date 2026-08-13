"""
DICOM 患者标识脱敏测试（纯单元，不依赖 MySQL/DICOM 文件）
覆盖：真实姓名/ID → ***；空值与占位 → 原样返回
"""
from api.dicom_api import _mask_patient_id


def test_real_patient_id_masked():
    """真实内嵌姓名/ID → 脱敏为 ***"""
    assert _mask_patient_id("张三") == "***"
    assert _mask_patient_id("M1110220") == "***"


def test_unknown_value_kept():
    """占位/缺失值 → 原样返回，不误伤"""
    assert _mask_patient_id("未知") == "未知"
    assert _mask_patient_id(None) is None


def test_empty_string_masked():
    """空字符串（存在但为空的标签）→ 也掩码，保持确定性"""
    assert _mask_patient_id("") == "***"
