"""
医疗实体抽取模块
优先使用LLM抽取，LLM不可用时降级为关键词匹配
"""
from utils.text_clean import clean_medical_text
from core.vector_store import create_medical_collection
from core.diagnosis_agent import llm_extract_entity, call_llm
from core.logger import get_logger
import json

logger = get_logger(__name__)

# 懒加载——首次使用时初始化（避免SSL/网络问题阻塞导入）
_model = None
def _get_model():
    global _model
    if _model is None:
        import os
        # 跳过SSL验证（Windows企业网络常见，HuggingFace下载用）
        os.environ.setdefault("CURL_CA_BUNDLE", "")
        os.environ.setdefault("REQUESTS_CA_BUNDLE", "")
        os.environ.setdefault("HF_HUB_DISABLE_SSL_VERIFY", "1")
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning("[WARNING] 向量模型加载失败: %s", e)
            _model = None
    return _model


def get_text_embedding(text: str):
    """文本转向量（懒加载模型）"""
    clean_txt = clean_medical_text(text)
    model = _get_model()
    vec = model.encode(clean_txt)
    return vec.tolist()


def extract_medical_entity(raw_record: str) -> dict:
    """
    病历实体抽取：优先LLM，降级关键词匹配
    返回结构化字典：症状、既往史、诊断、用药
    """
    clean_txt = clean_medical_text(raw_record)
    if not clean_txt:
        return {"symptom": [], "past_history": [], "diagnosis": [], "medicine": []}

    # 优先使用LLM抽取
    llm_result = llm_extract_entity(clean_txt)
    # 检查是否包含有效字段
    if any(v for v in llm_result.values()):
        return llm_result

    # 降级：关键词匹配
    entity = {"symptom": [], "past_history": [], "diagnosis": [], "medicine": []}

    symptom_words = [
        "头痛", "咳嗽", "胸闷", "发热", "乏力", "腹痛", "恶心", "呕吐",
        "头晕", "心悸", "气短", "水肿", "疼痛", "麻木", "失眠", "食欲不振"
    ]
    for word in symptom_words:
        if word in clean_txt:
            entity["symptom"].append(word)

    history_words = [
        "高血压", "糖尿病", "心脏病", "手术史", "过敏史", "冠心病",
        "脑梗死", "肝炎", "结核", "哮喘", "风湿", "肿瘤"
    ]
    for word in history_words:
        if word in clean_txt:
            entity["past_history"].append(word)

    diagnosis_words = [
        "诊断", "确诊", "考虑", "疑似", "肺炎", "骨折", "感染",
        "炎症", "综合征", "肿瘤", "结节", "溃疡"
    ]
    for word in diagnosis_words:
        if word in clean_txt:
            entity["diagnosis"].append(word)

    medicine_words = [
        "阿司匹林", "降压药", "抗生素", "胰岛素", "他汀",
        "输液", "口服", "注射", "用药", "处方"
    ]
    for word in medicine_words:
        if word in clean_txt:
            entity["medicine"].append(word)

    return entity


def insert_knowledge_to_milvus(knowledge_text: str):
    """医疗知识库文本插入Milvus向量库"""
    try:
        coll = create_medical_collection()
        vec = get_text_embedding(knowledge_text)
        data = [
            [knowledge_text],
            [vec]
        ]
        res = coll.insert(data)
        coll.flush()
        return res
    except Exception as e:
        logger.warning("[Milvus插入跳过] %s", e)
        return None
