from sqlalchemy.orm import Session
from db.models import MedicalPaper
from datetime import datetime

# 新增上传文献
def create_paper(
    db: Session,
    paper_name: str,
    file_path: str,
    full_text: str = "",
    ai_summary: str = "",
    core_conclusion: str = ""
):
    db_obj = MedicalPaper(
        paper_name=paper_name,
        file_path=file_path,
        full_text=full_text,
        ai_summary=ai_summary,
        core_conclusion=core_conclusion,
        create_time=datetime.now()
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 根据文献ID查询
def get_paper_by_id(db: Session, paper_id: int):
    return db.query(MedicalPaper).filter(MedicalPaper.id == paper_id).first()

# 分页查询全部文献
def get_paper_list(db: Session, skip: int = 0, limit: int = 20):
    return db.query(MedicalPaper).offset(skip).limit(limit).all()

# 更新AI摘要、结论
def update_paper_analysis(
    db: Session,
    paper_id: int,
    ai_summary: str,
    core_conclusion: str
):
    paper = get_paper_by_id(db, paper_id)
    if not paper:
        return None
    paper.ai_summary = ai_summary
    paper.core_conclusion = core_conclusion
    db.commit()
    db.refresh(paper)
    return paper

# 删除文献记录
def delete_paper(db: Session, paper_id: int):
    paper = get_paper_by_id(db, paper_id)
    if not paper:
        return False
    db.delete(paper)
    db.commit()
    return True

# 搜索文献（按标题、摘要、结论模糊匹配）
def search_papers(db: Session, keyword: str, skip: int = 0, limit: int = 20):
    from sqlalchemy import or_
    like = f"%{keyword}%"
    return db.query(MedicalPaper).filter(
        or_(
            MedicalPaper.paper_name.like(like),
            MedicalPaper.ai_summary.like(like),
            MedicalPaper.core_conclusion.like(like)
        )
    ).offset(skip).limit(limit).all()
