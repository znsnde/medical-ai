"""
多模态影像分析模块
支持DICOM/通用医学影像的基础分析与报告生成
优先使用DeepSeek基于影像元数据+基础像素特征+临床病历生成影像解读，
LLM/解析不可用时降级为基础影像特征描述（不再使用"待专业模型分析"占位文案）
"""
import os
from core.logger import get_logger
from core.diagnosis_agent import call_llm

logger = get_logger(__name__)

# 影像AI解读系统提示词：强制诚实，区分影像事实与临床推断
SYSTEM_IMAGE_ANALYSIS = """你是一名影像科辅助诊断专家。
请基于影像元数据、基础影像特征和临床病历文本，生成影像分析报告，包含三个部分：
1. 影像所见：客观描述影像参数与特征（如CT值/HU范围、图像尺寸、窗宽窗位等可获得的信息）
2. 影像提示：结合临床病历，给出可能相关的影像学提示或需要重点关注的方面
3. 建议：建议的进一步检查或随访
要求：
- 专业、简洁、段落化，使用中文
- 严格区分"影像提供的信息"与"临床推断"，临床推断标注为"初步提示"
- 如果影像信息不足（例如只有元数据、没有像素数据），如实说明局限性，不得编造影像表现
- 本报告为基于影像元数据与临床资料的初步分析，不代表像素级AI模型结论
"""


def _is_dicom_path(image_path: str) -> bool:
    return os.path.splitext(image_path)[-1].lower() in (".dcm", ".dicom")


def _extract_pixel_features(image_path: str) -> dict:
    """
    从DICOM提取基础像素特征（纯数值统计，非AI模型）
    失败（压缩传输语法无解码器/多帧/非像素文件等）返回 {}，LLM仍可用元数据解读
    """
    try:
        import pydicom
        import numpy as np
        ds = pydicom.dcmread(image_path, force=True)
        if not hasattr(ds, "pixel_array"):
            return {}
        arr = ds.pixel_array
        features = {
            "图像尺寸": f"{arr.shape[0]}x{arr.shape[1]}",
            "像素值范围": f"{int(arr.min())}~{int(arr.max())}",
            "像素均值": f"{round(float(arr.mean()), 2)}",
            "像素标准差": f"{round(float(arr.std()), 2)}",
            "光度解释": str(getattr(ds, "PhotometricInterpretation", "未知")),
            "位深": str(getattr(ds, "BitsAllocated", "未知")),
        }
        # CT 有 rescale 时给出 HU 范围（临床更可读）
        if hasattr(ds, "RescaleIntercept"):
            slope = float(getattr(ds, "RescaleSlope", 1.0))
            intercept = float(ds.RescaleIntercept)
            hu = arr.astype(np.float64) * slope + intercept
            features["HU范围"] = f"{int(hu.min())}~{int(hu.max())} HU"
            features["HU均值"] = f"{round(float(hu.mean()), 2)} HU"
        return features
    except Exception as e:
        logger.debug("像素特征提取跳过: %s", e)
        return {}


def _image_basic_info(image_path: str) -> dict:
    """通用影像（JPG/PNG等）基础信息"""
    try:
        from PIL import Image
        with Image.open(image_path) as im:
            return {
                "图像格式": im.format or "未知",
                "图像尺寸": f"{im.width}x{im.height}",
                "色彩模式": im.mode,
            }
    except Exception as e:
        logger.debug("通用影像信息提取跳过: %s", e)
        return {}


def analyze_medical_image(image_path: str) -> dict:
    """
    医学影像基础分析
    返回影像元信息和基础分析结果
    （实际生产应接入专用影像AI模型）
    """
    if not image_path or not os.path.exists(image_path):
        return {
            "error": "影像文件不存在",
            "analysis": "暂无影像分析结果"
        }

    file_size = os.path.getsize(image_path)
    file_ext = os.path.splitext(image_path)[-1].lower()

    # 基础信息
    result = {
        "file_path": image_path,
        "file_size_kb": round(file_size / 1024, 2),
        "file_type": file_ext,
        "analysis": "",
        "abnormal_findings": []
    }

    # DICOM文件调用专用解析
    if file_ext in [".dcm", ".dicom"]:
        try:
            from dcmtk_handler.dcm_parse import parse_dicom_basic
            dcm_info = parse_dicom_basic(image_path)
            result.update(dcm_info)
        except Exception as e:
            result["analysis"] = f"DICOM解析异常: {str(e)}"
    else:
        # 通用影像（JPG/PNG等）基础信息
        result["modality"] = "通用影像"
        result["analysis"] = "影像文件已接收，待专业AI模型分析"

    return result


def _build_base_lines(analysis: dict) -> list:
    """基础信息行（元数据层，降级展示与LLM输入共用）"""
    lines = [
        f"影像类型：{analysis.get('modality', analysis.get('file_type', '未知'))}",
        f"影像文件大小：{analysis.get('file_size_kb', '未知')}KB",
    ]
    if analysis.get("patient_name"):
        lines.append(f"患者：{analysis['patient_name']}")
    if analysis.get("study_date"):
        lines.append(f"检查日期：{analysis['study_date']}")
    if analysis.get("series_description"):
        lines.append(f"检查部位：{analysis['series_description']}")
    if analysis.get("rows") and analysis.get("columns"):
        lines.append(f"图像矩阵：{analysis['rows']}×{analysis['columns']}")
    if analysis.get("pixel_spacing"):
        lines.append(f"像素间距：{analysis['pixel_spacing']}")
    return lines


def _generate_llm_analysis(analysis: dict, features: dict, record_text: str) -> str:
    """调DeepSeek生成影像解读；失败（空串/异常前缀）返回空串，由调用方降级"""
    # 元数据行：剔除内部字段与"未知"占位
    meta_items = [
        f"{k}：{v}"
        for k, v in analysis.items()
        if k not in ("error", "analysis", "abnormal_findings", "file_path")
        and v not in ("", "未知", None)
    ]
    feature_lines = "\n".join(f"  {k}：{v}" for k, v in features.items()) or "  无（仅元数据，未获取像素数据）"
    clean_record = (record_text or "").strip()
    record_section = clean_record[:1500] if clean_record else "无临床病历文本提供"

    user_prompt = f"""【影像信息】
{chr(10).join(meta_items)}

【基础影像特征】
{feature_lines}

【临床病历文本】
{record_section}

请生成影像分析报告。"""
    raw = call_llm(SYSTEM_IMAGE_ANALYSIS, user_prompt, temperature=0.2, max_tokens=1024)
    if not raw or raw.startswith("[LLM调用异常]"):
        return ""
    return raw


def generate_image_analysis_report(image_path: str, record_text: str = "") -> str:
    """
    生成影像分析文本描述（供诊断报告使用）
    优先LLM：影像元数据 + 基础像素特征 + 临床病历 → DeepSeek 三段式影像解读；
    降级：LLM/解析不可用时返回基础影像特征描述，建议影像科医生判读。
    """
    analysis = analyze_medical_image(image_path)
    if analysis.get("error"):
        return f"影像分析不可用：{analysis['error']}"

    # 像素/内容特征（轻量数值统计，非AI）
    features = _extract_pixel_features(image_path) if _is_dicom_path(image_path) else _image_basic_info(image_path)

    # 1. 优先LLM解读
    llm_text = _generate_llm_analysis(analysis, features, record_text)
    if llm_text:
        return llm_text

    # 2. 降级：基础信息 + 像素特征
    lines = _build_base_lines(analysis)
    if features:
        lines.append("基础影像特征：")
        lines.extend(f"  {k}：{v}" for k, v in features.items())
    lines.append("影像AI解读暂不可用。以上为影像基础信息与特征，建议结合临床资料由影像科医生进一步判读。")
    return "\n".join(lines)
