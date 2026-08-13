"""
LLM辅助诊断智能体
调用DeepSeek API实现：病历实体抽取、诊断建议生成、文献摘要、患者问答
"""
from openai import OpenAI
from config.settings import settings

# LLM 调用失败时返回的固定前缀，调用方据此识别并做降级兜底（不把异常字符串当业务内容）
LLM_FAILURE_PREFIX = "[LLM调用异常]"

# 初始化DeepSeek客户端
# timeout：单次请求超时（长文本生成/影像综合诊断设 60s）
# max_retries：网络抖动/限流时自动重试 1 次，避免瞬时错误直接写库
client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    timeout=60.0,
    max_retries=1
)

def is_llm_failure(text) -> bool:
    """判断 LLM 返回是否已是失败兜底串（避免把异常信息存库/展示给用户）"""
    return isinstance(text, str) and text.startswith(LLM_FAILURE_PREFIX)

# 通用LLM调用
def call_llm(system_prompt: str, user_prompt: str, temperature=0.3, max_tokens=2048) -> str:
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"{LLM_FAILURE_PREFIX} {str(e)}"


# ========== 1. 病历实体智能抽取 ==========
SYSTEM_EXTRACT = """你是一名资深的电子病历结构化专家。
请从病历文本中提取以下实体，以JSON格式返回（不要包含其他解释文字）：
{
  "symptom": ["症状1", "症状2", ...],
  "past_history": ["既往病史1", ...],
  "diagnosis": ["诊断1", ...],
  "medicine": ["用药1", ...]
}
未找到的字段返回空数组。"""

def llm_extract_entity(record_text: str) -> dict:
    """使用LLM抽取病历实体"""
    import json
    raw = call_llm(SYSTEM_EXTRACT, record_text, temperature=0.1)
    # 尝试提取JSON部分
    try:
        # 查找第一个 { 和最后一个 }
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        # 回退：空结构
        return {"symptom": [], "past_history": [], "diagnosis": [], "medicine": []}


# ========== 2. AI辅助诊断生成 ==========
SYSTEM_DIAGNOSIS = """你是一名经验丰富的临床辅助诊断专家。
根据病历信息、结构化实体和参考指南，给出专业、清晰的辅助诊断建议。
请以段落形式输出，包含：病情分析、可能的诊断、建议的检查项目。"""

def llm_generate_diagnosis(record_text: str, structured_data: dict, reference_knowledge: list,
                           image_analysis: str = "") -> str:
    """生成AI辅助诊断建议（可选结合影像分析结果）"""
    ref_text = "\n".join(reference_knowledge) if reference_knowledge else "暂无匹配指南"
    img_section = f"\n【影像分析结果】\n{image_analysis}\n" if image_analysis else ""
    user_prompt = f"""
【病历原文】
{record_text[:2000]}

【结构化实体】
{structured_data}

【临床参考指南】
{ref_text}
{img_section}
请给出辅助诊断建议。"""
    return call_llm(SYSTEM_DIAGNOSIS, user_prompt, temperature=0.3, max_tokens=2048)


# ========== 3. 医学文献智能摘要 ==========
SYSTEM_PAPER = """你是一名医学文献研究助理。
请根据文献内容生成：
1. 文献摘要（200字以内，概括研究目的、方法、结果）
2. 核心结论（100字以内，提炼主要发现和临床意义）
以JSON格式返回：
{
  "ai_summary": "...",
  "core_conclusion": "..."
}"""

def llm_summarize_paper(paper_name: str, paper_text: str) -> dict:
    """生成文献摘要和结论"""
    import json
    user_prompt = f"文献标题：{paper_name}\n\n文献正文：{paper_text[:3000]}"
    raw = call_llm(SYSTEM_PAPER, user_prompt, temperature=0.3, max_tokens=1024)
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {
            "ai_summary": paper_text[:200] + "......",
            "core_conclusion": "待LLM深度解析"
        }


# ========== 4. 患者问诊智能问答 ==========
SYSTEM_CHAT = """你是一名在线问诊的智能医疗助手。
请基于以下临床参考知识，用通俗易懂的语言回答患者的问题。
注意：你仅提供参考信息，不能替代医生诊断，建议患者及时就医。"""

def llm_patient_chat(question: str, reference_knowledge: list) -> str:
    """患者问诊智能回答"""
    ref_text = "\n".join(reference_knowledge) if reference_knowledge else "暂无匹配知识"
    user_prompt = f"""
【临床参考知识】
{ref_text}

【患者问题】
{question}

请回答患者的问题。"""
    return call_llm(SYSTEM_CHAT, user_prompt, temperature=0.7, max_tokens=1024)


# ========== 5. 多模态综合分析（病历文本 + 影像） ==========
SYSTEM_MULTIMODAL = """你是一名经验丰富的临床诊断专家，擅长结合病历文本和医学影像进行综合分析。
请根据以下信息给出综合诊断意见：

1. 首先分析病历文本和已提取的结构化实体
2. 然后结合影像分析结果（如有）
3. 给出综合诊断意见，包括：
   - 病情总结与分析
   - 影像与临床症状的关联判断
   - 最终诊断意见或鉴别诊断
   - 建议的进一步检查或治疗方案

请用专业但清晰的段落形式输出。"""

def llm_combined_diagnosis(record_text: str, structured_data: dict, image_analysis: str) -> str:
    """病历文本 + 医学影像的综合诊断分析"""
    user_prompt = f"""
【病历原文】
{record_text[:2000]}

【结构化实体】
{structured_data}

【影像分析结果】
{image_analysis if image_analysis else "无影像数据"}

请综合以上所有信息，给出专业的诊断意见。"""
    return call_llm(SYSTEM_MULTIMODAL, user_prompt, temperature=0.3, max_tokens=2048)
