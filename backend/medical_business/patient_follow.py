"""
患者随访与智能问答业务逻辑
使用LLM进行患者问诊回答，结合RAG知识库检索
"""
from core.medical_rag import rag_search_medical_knowledge
from core.diagnosis_agent import llm_patient_chat, is_llm_failure


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
    # LLM 调用失败时，向患者返回友好提示（不展示内部异常信息）
    if is_llm_failure(answer):
        answer = "抱歉，智能问答服务暂时不可用。以上为检索到的临床参考知识，供您参考；如有不适请及时前往医院就诊。"
    return answer
