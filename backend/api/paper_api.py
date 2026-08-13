from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import paper_crud
from medical_business import paper_reader
from utils.file_util import get_unique_save_path
from core.security import require_roles
from utils.common import resp_success, resp_fail

router = APIRouter(dependencies=[Depends(require_roles(["admin", "doctor"]))])

# 分页查询所有文献（静态路由必须在动态之前）
@router.get("/list/all")
def list_paper(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    data = paper_crud.get_paper_list(db, skip, limit)
    return resp_success(data=data)

# 搜索文献（按关键词匹配标题、摘要、结论）
@router.get("/search")
def search_paper(keyword: str, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    data = paper_crud.search_papers(db, keyword, skip, limit)
    return resp_success(data=data)

# 模块连通测试接口
@router.get("/test")
def paper_test():
    return resp_success(msg="医学文献速读模块接口可用")

# 上传文献PDF并解析入库（自动提取文字，无需手动输入全文）
@router.post("/upload")
async def upload_paper(
    paper_name: str = Form(...),
    file: UploadFile = File(...),
    paper_content: str = Form(""),
    db: Session = Depends(get_db)
):
    # 保存PDF文件
    full_path, rel_path = get_unique_save_path("paper", file.filename)
    with open(full_path, "wb") as f:
        f.write(await file.read())
    # 业务层：自动从PDF提取文字 → AI摘要 → 入库
    paper = paper_reader.parse_medical_paper(db, paper_name, full_path, paper_content)
    return resp_success(data=paper, msg="文献上传解析完成")

# 根据文献ID查询详情
@router.get("/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = paper_crud.get_paper_by_id(db, paper_id)
    if not paper:
        return resp_fail("文献不存在")
    return resp_success(data=paper)

# 更新文献AI摘要和结论
@router.put("/analysis/{paper_id}")
def update_paper_analysis(
    paper_id: int,
    ai_summary: str = Form(...),
    core_conclusion: str = Form(...),
    db: Session = Depends(get_db)
):
    paper = paper_crud.update_paper_analysis(db, paper_id, ai_summary, core_conclusion)
    if not paper:
        return resp_fail("文献不存在，更新失败")
    return resp_success(data=paper, msg="文献分析内容更新成功")

# 删除文献记录
@router.delete("/{paper_id}")
def del_paper(paper_id: int, db: Session = Depends(get_db)):
    flag = paper_crud.delete_paper(db, paper_id)
    if not flag:
        return resp_fail("删除失败，文献不存在")
    return resp_success(msg="文献删除成功")
