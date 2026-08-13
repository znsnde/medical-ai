"""
多轮诊断式问询业务逻辑
AI 模拟医生进行症状采集 -> 鉴别诊断 -> 建议
"""
import json
import re
from core.diagnosis_agent import client

SYSTEM_PROMPT = """你是一名经验丰富的临床医生，正在进行患者问诊。你需要：

## 问诊流程
1. **采集阶段**：询问患者的主要症状、持续时间、部位、性质、诱因等
2. **追问阶段**：根据患者回答追问关键细节（伴随症状、既往史、用药史等）
3. **诊断阶段**：当信息足够时，给出初步判断和鉴别诊断
4. **建议阶段**：给出就诊建议、检查建议和生活指导

## 行为准则
- 每次只问 1-2 个问题，不要一次问太多
- 用通俗易懂的语言，避免过多专业术语
- 表现出共情和关切
- 必须严格以 JSON 格式输出，不要包含其他文字

## 输出格式（必须严格遵循）
{"reply": "你对患者说的话", "stage": "collecting", "suggestions": ["短回复1", "短回复2", "短回复3"]}

stage 说明：
- "collecting": 正在采集症状信息，继续追问
- "diagnosing": 已收集足够信息，给出初步诊断分析
- "done": 问诊结束，给出最终建议

suggestions: 3 个供患者点击的快捷回复，每个不超过 10 个字。diagnosing/done 阶段可以是"谢谢医生"、"我知道了"等。
"""


def diagnostic_interview(messages: list) -> dict:
    """
    多轮诊断式问询
    :param messages: [{"role": "user"|"assistant", "content": "..."}]
    :return: {"reply": "...", "stage": "...", "suggestions": [...]}
    """
    # 构建完整对话历史
    chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        role = msg.get("role", "user")
        chat_messages.append({"role": role, "content": msg.get("content", "")})

    # 如果是新对话，添加一个开场白
    if len(messages) <= 1:
        user_content = messages[-1]["content"] if messages else "我最近身体不太舒服"
        chat_messages.append({"role": "user", "content": user_content})

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=chat_messages,
            temperature=0.5,
            max_tokens=1024
        )
        raw = resp.choices[0].message.content.strip()
    except Exception as e:
        return {
            "reply": f"问诊服务暂时不可用，请稍后再试。",
            "stage": "done",
            "suggestions": ["重新开始", "我知道了"]
        }

    return _parse_json_reply(raw)


def _parse_json_reply(raw: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    # 尝试直接解析
    raw_clean = raw.strip()
    if raw_clean.startswith("{"):
        try:
            return json.loads(raw_clean)
        except json.JSONDecodeError:
            pass

    # 尝试提取 ```json ... ``` 块
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取 { 到 } 之间的内容
    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # 回退
    return {
        "reply": raw.strip(),
        "stage": "collecting",
        "suggestions": ["能详细说说吗", "还有其他症状吗", "这种情况多久了"]
    }
