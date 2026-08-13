"""
RAG知识库检索模块
使用向量检索从Milvus中查找相似医疗指南
当Milvus/模型不可用时降级返回空结果
"""
from utils.text_clean import clean_medical_text
from core.logger import get_logger

logger = get_logger(__name__)


def rag_search_medical_knowledge(query: str, top_k=3) -> list:
    """
    根据病历/问题检索相似医疗指南
    降级策略：向量库/模型不可用时返回空列表，不阻塞主流程
    """
    clean_q = clean_medical_text(query)
    if not clean_q:
        return []

    # 尝试向量检索
    query_vec = _safe_get_embedding(clean_q)
    if query_vec is None:
        return []  # 模型不可用，跳过RAG

    try:
        from core.vector_store import search_vector
        search_res = search_vector(query_vec, top_k=top_k)
        match_texts = []
        for hits in search_res:
            for hit in hits:
                text = hit.entity.get("text")
                if text:
                    match_texts.append(text)
        return match_texts
    except Exception as e:
        logger.warning("[RAG搜索跳过] %s", e)
        return []


def _safe_get_embedding(text: str):
    """安全获取向量，不可用时返回None"""
    try:
        from core.entity_extract import get_text_embedding
        return get_text_embedding(text)
    except Exception as e:
        logger.warning("[向量生成跳过] %s", e)
        return None
