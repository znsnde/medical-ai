"""
医学文献速读冒烟测试（依赖本地 MySQL）
覆盖：上传（LLM/Milvus 打桩）、列表、搜索、详情、分析更新、PDF 下载、删除、非医生角色 401/403
"""
import uuid
from pathlib import Path

from config.settings import settings
from db.crud import paper_crud
from conftest import requires_mysql, auth_headers

MIN_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _make_paper(db, name=None, summary="摘要", conclusion="结论"):
    return paper_crud.create_paper(db, name or f"文献{uuid.uuid4().hex[:6]}", "",
                                   "", summary, conclusion)


@requires_mysql
def test_paper_upload_flow(client, db, admin_token, monkeypatch):
    """上传 PDF → 自动提取 + LLM 摘要（打桩）→ 入库"""
    monkeypatch.setattr("medical_business.paper_reader.llm_summarize_paper",
                        lambda paper_name, text: {"ai_summary": "测试摘要", "core_conclusion": "测试结论"})
    monkeypatch.setattr("medical_business.paper_reader.insert_knowledge_to_milvus",
                        lambda text: None)

    name = f"测试文献_{uuid.uuid4().hex[:6]}.pdf"
    r = client.post("/api/paper/upload", data={"paper_name": name},
                    files={"file": ("paper.pdf", MIN_PDF, "application/pdf")},
                    headers=auth_headers(admin_token))
    body = r.json()
    assert body["code"] == 200, body
    data = body["data"]
    assert data["paper_name"] == name
    assert data["ai_summary"] == "测试摘要"
    assert data["core_conclusion"] == "测试结论"
    assert data["file_path"]

    # 清理：删行 + 删上传的 PDF 文件
    pid = data["id"]
    fp = Path(data["file_path"])
    if not fp.is_absolute():
        fp = Path(settings.UPLOAD_PATH) / fp.parent.name / fp.name
    paper_crud.delete_paper(db, pid)
    fp.unlink(missing_ok=True)


@requires_mysql
def test_paper_list_search_detail_analysis(client, db, admin_token):
    h = auth_headers(admin_token)
    p = _make_paper(db, "高血压管理指南", "旧摘要", "旧结论")

    # 列表
    lst = client.get("/api/paper/list/all", headers=h).json()["data"]
    assert any(x["id"] == p.id for x in lst)

    # 搜索（标题命中）
    found = client.get("/api/paper/search", params={"keyword": "高血压"}, headers=h).json()["data"]
    assert any(x["id"] == p.id for x in found)

    # 详情
    d = client.get(f"/api/paper/{p.id}", headers=h).json()["data"]
    assert d["paper_name"] == "高血压管理指南"

    # 分析更新（PUT，Form 参数）
    up = client.put(f"/api/paper/analysis/{p.id}",
                    data={"ai_summary": "新摘要", "core_conclusion": "新结论"},
                    headers=h).json()["data"]
    assert up["ai_summary"] == "新摘要" and up["core_conclusion"] == "新结论"

    # 详情不存在 → resp_fail
    assert client.get("/api/paper/999999999", headers=h).json()["code"] != 200

    paper_crud.delete_paper(db, p.id)


@requires_mysql
def test_paper_download_and_delete(client, db, admin_token):
    h = auth_headers(admin_token)
    # 造真实 PDF 文件
    paper_dir = Path(settings.UPLOAD_PATH) / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    fname = f"t_{uuid.uuid4().hex}.pdf"
    abs_path = paper_dir / fname
    abs_path.write_bytes(MIN_PDF)
    p = paper_crud.create_paper(db, "下载测试文献", str(abs_path), "", "摘要", "结论")

    # 下载 → 返回真实 PDF
    r = client.get(f"/api/paper/pdf/download/{p.id}", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")

    # 删除
    assert client.delete(f"/api/paper/{p.id}", headers=h).json()["code"] == 200
    assert client.get(f"/api/paper/{p.id}", headers=h).json()["code"] != 200

    abs_path.unlink(missing_ok=True)


@requires_mysql
def test_paper_requires_doctor(client):
    """router 级 require_roles：匿名 401、患者 403"""
    uname = f"paper_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register/public", data={
        "username": uname, "password": "test1234", "real_name": "文献测试"
    })
    assert r.json().get("code") == 200
    tok = client.post("/api/auth/login", data={"username": uname, "password": "test1234"})
    assert tok.json()["code"] == 200

    assert client.get("/api/paper/list/all").status_code == 401
    assert client.get("/api/paper/list/all",
                      headers=auth_headers(tok.json()["data"]["token"])).status_code == 403
