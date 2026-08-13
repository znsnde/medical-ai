"""
医学文献速读业务逻辑
使用LLM生成文献摘要和核心结论
支持自动从 PDF 提取文字
"""
import os
from sqlalchemy.orm import Session
from db.crud import paper_crud
from utils.text_clean import clean_medical_text
from core.entity_extract import insert_knowledge_to_milvus
from core.diagnosis_agent import llm_summarize_paper


def extract_text_from_pdf(file_path: str) -> str:
    """使用 pdfplumber 提取 PDF 文件中的文字"""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)
    except Exception as e:
        return f"[PDF文字提取失败] {str(e)}"


def parse_medical_paper(db: Session, paper_name: str, file_path: str, paper_content: str = ""):
    """
    完整文献解析流程：
    1. 优先从 PDF 文件提取文字（如果 paper_content 为空）
    2. 文本清洗
    3. LLM生成摘要和结论
    4. 存入数据库
    5. 存入向量库供检索
    """
    # 1. 提取文字（优先从 PDF 提取）
    if not paper_content and file_path and os.path.exists(file_path):
        paper_content = extract_text_from_pdf(file_path)

    # 2. 文本清洗
    clean_content = clean_medical_text(paper_content) if paper_content else ""
    if not clean_content:
        clean_content = "（未能从PDF提取到文字内容，请检查文件是否可读）"

    # 3. LLM智能摘要
    result = llm_summarize_paper(paper_name, clean_content)
    ai_summary = result.get("ai_summary", clean_content[:200] + "......")
    core_conclusion = result.get("core_conclusion", "待深度解析")

    # 4. 数据库保存（含全文）
    paper = paper_crud.create_paper(
        db=db,
        paper_name=paper_name,
        file_path=file_path,
        full_text=clean_content,
        ai_summary=ai_summary,
        core_conclusion=core_conclusion
    )

    # 5. 存入向量库
    insert_knowledge_to_milvus(f"{paper_name}：{clean_content}")

    return paper
