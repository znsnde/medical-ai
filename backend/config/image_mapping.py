"""
典型病例参考影像映射表
将诊断关键词匹配到对应的参考影像文件
关键词顺序 = 匹配优先级（特异性高的放前面）
"""

DISEASE_IMAGE_MAP = {
    # ═══ 脑部（最高优先级） ═══
    "脑梗死": "brain_infarction.jpg",
    "脑梗塞": "brain_infarction.jpg",
    "小脑梗死": "brain_infarction.jpg",
    "缺血性卒中": "brain_infarction.jpg",
    "脑出血": "brain_hemorrhage.jpg",
    "出血性卒中": "brain_hemorrhage.jpg",
    "颅内出血": "brain_hemorrhage.jpg",

    # ═══ 肺部 ═══
    "肺炎": "chest_pneumonia.jpg",
    "肺部感染": "chest_pneumonia.jpg",
    "慢阻肺": "chest_copd.jpg",
    "肺气肿": "chest_copd.jpg",
    "COPD": "chest_copd.jpg",

    # ═══ 脊柱 ═══
    "腰椎间盘突出": "spine_disc_herniation.jpg",
    "椎间盘突出": "spine_disc_herniation.jpg",
    "腰椎退行性": "spine_disc_herniation.jpg",

    # ═══ 骨折 ═══
    "骨折": "bone_fracture.jpg",
    "骨裂": "bone_fracture.jpg",

    # ═══ 心脏（特异性高的在前） ═══
    "心脏肥大": "heart_hypertrophy.jpg",
    "心影增大": "heart_hypertrophy.jpg",
    "冠心病": "heart_hypertrophy.jpg",
    "心肌缺血": "heart_hypertrophy.jpg",
    "ST段改变": "heart_hypertrophy.jpg",

    # ═══ 高血压（最通用，放最后） ═══
    "高血压": "heart_normal.jpg",

    # ═══ 默认 ═══
    "default": "chest_normal.jpg",
}


def match_disease_image(diagnosis_text: str) -> str:
    """
    根据诊断文本匹配对应的参考影像文件名
    按关键词顺序匹配，返回第一个匹配的影像
    """
    if not diagnosis_text:
        return DISEASE_IMAGE_MAP["default"]

    for keyword, image_name in DISEASE_IMAGE_MAP.items():
        if keyword == "default":
            continue
        if keyword in diagnosis_text:
            return image_name

    return DISEASE_IMAGE_MAP["default"]


IMAGE_DISPLAY_NAME = {
    "chest_normal.jpg": "正常胸部X光",
    "chest_pneumonia.jpg": "肺炎（肺部浸润）",
    "chest_copd.jpg": "慢性阻塞性肺疾病",
    "brain_normal.jpg": "正常头颅CT",
    "brain_infarction.jpg": "脑梗死（缺血性卒中）",
    "brain_hemorrhage.jpg": "脑出血（出血性卒中）",
    "spine_normal.jpg": "正常腰椎",
    "spine_disc_herniation.jpg": "腰椎间盘突出",
    "bone_fracture.jpg": "骨折（骨皮质不连续）",
    "heart_normal.jpg": "正常心影",
    "heart_hypertrophy.jpg": "心脏肥大（心胸比增大）",
}
