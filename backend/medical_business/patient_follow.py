"""
患者随访与智能问答业务逻辑
使用LLM进行患者问诊回答，结合RAG知识库检索
"""
from core.medical_rag import rag_search_medical_knowledge
from core.diagnosis_agent import llm_patient_chat


def patient_qa_chat(user_question: str) -> str:
    """
    患者问诊问答流程：
    1. RAG检索相关临床知识
    2. LLM结合知识生成通俗回答
    """
    # 1. 知识库检索
    match_knowledge = rag_search_medical_knowledge(user_question, top_k=3)
    if not match_knowledge:
        match_knowledge = ["（未检索到精确匹配知识，以下为通用建议）"]

    # 2. LLM生成回答
    answer = llm_patient_chat(user_question, match_knowledge)
    return answer
