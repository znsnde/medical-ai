"""
影像分析模块冒烟测试（纯单元，不依赖 MySQL/Neo4j/DeepSeek）
覆盖：缺失文件、LLM失败降级、LLM成功直出、真实DICOM像素特征提取
"""
import os
from pathlib import Path

import pytest

from core.multimodal_model import generate_image_analysis_report, _extract_pixel_features

# 仓库内置的真实 DICOM（test_synthetic_ct.dcm 已确认为 512x512 CT）
_DCM_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "static" / "upload" / "dicom" / "test_synthetic_ct.dcm",
    Path(__file__).resolve().parents[1] / "test_img.dcm",
]
REAL_DCM = next((p for p in _DCM_CANDIDATES if p.exists()), None)


def test_missing_file():
    """不存在的影像路径 → 返回影像分析不可用，不抛异常"""
    out = generate_image_analysis_report(r"Z:\nonexistent\no_such.dcm", "患者高血压头晕")
    assert isinstance(out, str)
    assert "影像分析不可用" in out


def test_llm_failure_degrade(monkeypatch):
    """LLM返回异常前缀 → 降级为基础影像信息 + 像素特征，不泄漏异常原文"""
    monkeypatch.setattr(
        "core.multimodal_model.call_llm",
        lambda *a, **k: "[LLM调用异常] connection timeout",
    )
    if not REAL_DCM:
        pytest.skip("无真实DICOM测试文件")
    out = generate_image_analysis_report(str(REAL_DCM), "患者高血压头晕三日")
    assert "LLM调用异常" not in out
    # 降级内容包含基础影像信息与判读说明
    assert "影像类型" in out
    assert "影像AI解读暂不可用" in out


def test_llm_success_returns_content(monkeypatch):
    """LLM成功 → 直接返回其解读内容"""
    canned = "影像所见：胸部CT未见明显异常。\n影像提示：初步提示，建议结合临床。"
    monkeypatch.setattr("core.multimodal_model.call_llm", lambda *a, **k: canned)
    if not REAL_DCM:
        pytest.skip("无真实DICOM测试文件")
    out = generate_image_analysis_report(str(REAL_DCM), "患者咳嗽一周")
    assert out == canned


@pytest.mark.skipif(REAL_DCM is None, reason="无真实DICOM测试文件")
def test_pixel_features_on_real_dcm():
    """真实DICOM → 像素特征提取成功且含图像尺寸键，不抛异常"""
    feat = _extract_pixel_features(str(REAL_DCM))
    assert isinstance(feat, dict)
    assert "图像尺寸" in feat
    assert "像素值范围" in feat
