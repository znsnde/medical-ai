import re

def clean_medical_text(raw_text: str) -> str:
    """清洗病历、文献文本，去除多余符号、换行、空格"""
    if not raw_text:
        return ""
    # 替换多个换行/空格为单个空格
    text = re.sub(r"\s+", " ", raw_text)
    # 过滤特殊杂乱符号
    text = re.sub(r"[#$%^&*_~`]+", "", text)
    # 去除首尾空格
    text = text.strip()
    return text