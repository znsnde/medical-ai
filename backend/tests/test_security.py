"""
P0 安全回归测试：未授权访问与越权封堵
- /static 公开目录已移除（患者报告 PDF / DICOM / 文献不再裸奔）
- 上传文件经受控下载接口（带鉴权）
- 越权点已封堵：reference-image、问诊会话 IDOR、patient/chat 匿名
"""
import uuid
from pathlib import Path

import pytest

from config.settings import settings
from db.session import SessionLocal
from db.crud import patient_crud, record_crud, report_crud, consult_crud, user_crud
from conftest import requires_mysql, auth_headers

MIN_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _new_patient_token(client) -> str:
    """注册 + 登录一个患者账号（用户名用 uuid 保证重复运行不冲突）"""
    uname = f"pat_{uuid.uuid4().hex[:10]}"
    r = client.post("/api/auth/register/public",
                    data={"username": uname, "password": "test1234", "real_name": "测试患者"})
    assert r.json().get("code") == 200, f"注册失败: {r.json()}"
    r = client.post("/api/auth/login", data={"username": uname, "password": "test1234"})
    return r.json()["data"]["token"]


# ── 1. /static 公开目录已移除 ──
@requires_mysql
def test_static_upload_not_served(client):
    """上传目录不再经公开 URL 可达"""
    r = client.get("/static/upload/report/whatever.pdf")
    assert r.status_code == 404


# ── 2. 报告 PDF 下载：受控 + 角色边界 ──
@requires_mysql
def test_report_pdf_download_auth(client, db):
    patient = patient_crud.create_patient(db, "安全测试患者", 30, "男", "13800000000")
    record = record_crud.create_record(db, patient.id, "测试病历文本", {"symptom": ["头痛"]})
    # 落一个真实的最小 PDF 到上传目录
    report_dir = Path(settings.UPLOAD_PATH) / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    fname = f"test_{uuid.uuid4().hex}.pdf"
    (report_dir / fname).write_bytes(MIN_PDF)
    report = report_crud.create_report(db, record.id, "影像分析", "诊断建议",
                                       pdf_path=f"static/upload/report/{fname}")

    # 无 token → 401
    assert client.get(f"/api/report/pdf/download/{report.id}").status_code == 401

    # 患者 token → 403（report 模块仅 admin/doctor）
    pat = _new_patient_token(client)
    assert client.get(f"/api/report/pdf/download/{report.id}",
                      headers=auth_headers(pat)).status_code == 403

    # admin token → 200 且为 PDF
    admin = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    resp = client.get(f"/api/report/pdf/download/{report.id}",
                      headers=auth_headers(admin.json()["data"]["token"]))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")

    # 清理测试数据（purge 物理删除行 + PDF 文件；固定手机号不清理会污染后续软删/绑定用例）
    try:
        report_crud.purge_report(db, report.id)
        record_crud.purge_record(db, record.id)
        patient_crud.purge_patient(db, patient.id)
    except Exception:
        pass


# ── 3. 参考影像：不再允许患者读任意病历诊断 ──
@requires_mysql
def test_reference_image_gated(client):
    # 无 token → 401
    assert client.get("/api/reference-image/by-record/1").status_code == 401
    # 患者 token → 403
    pat = _new_patient_token(client)
    assert client.get("/api/reference-image/by-record/1",
                      headers=auth_headers(pat)).status_code == 403


# ── 4. 问诊会话 IDOR：不能读/删他人会话 ──
@requires_mysql
def test_consultation_session_ownership(client, db):
    admin = user_crud.get_user_by_username(db, "admin")
    session = consult_crud.create_session(db, "内科", admin.id, "测试首条消息")

    pat = _new_patient_token(client)
    h = auth_headers(pat)

    # 患者读 admin 的会话 → 403
    assert client.get(f"/api/consultation/session/{session.id}", headers=h).status_code == 403
    # 患者删 admin 的会话 → 403
    assert client.delete(f"/api/consultation/session/{session.id}", headers=h).status_code == 403
    # 会话仍在（未被误删）
    assert consult_crud.get_session(db, session.id) is not None

    # admin 本人 → 200 可读
    admin_tok = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    assert client.get(f"/api/consultation/session/{session.id}",
                      headers=auth_headers(admin_tok.json()["data"]["token"])).status_code == 200


# ── 5. 患者问答：匿名禁止 ──
@requires_mysql
def test_patient_chat_requires_auth(client, monkeypatch):
    # 打桩避免真实 RAG/LLM 调用
    def fake_qa(question: str) -> str:
        return "模拟回答"
    monkeypatch.setattr("medical_business.patient_follow.patient_qa_chat", fake_qa)

    # 无 token → 401
    assert client.post("/api/patient/chat", data={"question": "高血压"}).status_code == 401
    # 登录后 → 200
    pat = _new_patient_token(client)
    r = client.post("/api/patient/chat", data={"question": "高血压"}, headers=auth_headers(pat))
    assert r.status_code == 200
    assert r.json().get("code") == 200
