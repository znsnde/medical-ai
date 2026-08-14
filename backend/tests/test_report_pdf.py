"""
诊断报告 PDF 导出测试（依赖本地 MySQL）
覆盖：生成 PDF 主流程（真实落盘+DB回写+受控下载）、报告不存在、未生成 PDF 查询、非医生角色 403
生成 PDF 为纯本地 reportlab，无需打桩。
"""
import uuid
from pathlib import Path

from config.settings import settings
from db.crud import patient_crud, record_crud, report_crud
from db.models import DiagnosisReport
from conftest import requires_mysql, auth_headers


def _make_chain(db):
    """patient → record → report（pdf_path 为空），返回 (pat_id, rec_id, rep_id)"""
    pat = patient_crud.create_patient(db, "PDF测试患者", 40, "男",
                                      phone=f"199{uuid.uuid4().hex[:8]}")
    rec = record_crud.create_record(db, pat.id, "患者发热咳嗽两日",
                                    {"symptom": ["发热"], "diagnosis": ["感冒"]})
    rep = report_crud.create_report(db, rec.id, "影像分析", "诊断建议")
    return pat.id, rec.id, rep.id


@requires_mysql
def test_report_pdf_generate_and_download(client, db, admin_token):
    pat_id, rec_id, rep_id = _make_chain(db)
    h = auth_headers(admin_token)

    # 生成 PDF（纯本地 reportlab，真实落盘）
    r = client.post(f"/api/report/pdf/generate?report_id={rep_id}", headers=h)
    body = r.json()
    assert body["code"] == 200, body
    data = body["data"]
    assert data["pdf_url"] == f"/api/report/pdf/download/{rep_id}"
    assert data["pdf_file_path"]
    assert data["report_info"]["id"] == rep_id

    # DB 已回写相对路径 static/upload/report/<uuid>.pdf，且文件真实存在
    db.rollback()
    row = db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first()
    assert row.pdf_path and row.pdf_path.startswith("static/upload/report/")
    pdf_abs = Path(settings.UPLOAD_PATH) / "report" / Path(row.pdf_path).name
    assert pdf_abs.is_file()

    # 查询 PDF 路径（未生成分支见 test_report_pdf_not_generated）
    r2 = client.get(f"/api/report/pdf/{rep_id}", headers=h)
    assert r2.json()["code"] == 200
    assert r2.json()["data"]["pdf_url"].endswith(f"/download/{rep_id}")

    # 受控下载 → 返回真实 PDF
    r3 = client.get(f"/api/report/pdf/download/{rep_id}", headers=h)
    assert r3.status_code == 200
    assert r3.headers["content-type"] == "application/pdf"
    assert r3.content.startswith(b"%PDF")

    # 清理：purge 行 + 删除落盘文件
    report_crud.purge_report(db, rep_id)
    record_crud.purge_record(db, rec_id)
    patient_crud.purge_patient(db, pat_id)
    pdf_abs.unlink(missing_ok=True)


@requires_mysql
def test_report_pdf_generate_missing_report(client, admin_token):
    """报告不存在 → resp_fail"""
    r = client.post("/api/report/pdf/generate?report_id=999999999",
                    headers=auth_headers(admin_token))
    body = r.json()
    assert body["code"] != 200
    assert "报告不存在" in body["msg"]


@requires_mysql
def test_report_pdf_not_generated(client, db, admin_token):
    """报告存在但未生成 PDF → 查询报「尚未生成」"""
    pat_id, rec_id, rep_id = _make_chain(db)
    r = client.get(f"/api/report/pdf/{rep_id}", headers=auth_headers(admin_token))
    body = r.json()
    assert body["code"] != 200
    assert "尚未生成" in body["msg"]

    report_crud.purge_report(db, rep_id)
    record_crud.purge_record(db, rec_id)
    patient_crud.purge_patient(db, pat_id)


@requires_mysql
def test_report_pdf_generate_requires_doctor(client):
    """患者 token → 403（_require_doctor 拦截）"""
    uname = f"pdf_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register/public", data={
        "username": uname, "password": "test1234", "real_name": "PDF测试患者账号"
    })
    assert r.json().get("code") == 200, r.json()
    tok = client.post("/api/auth/login", data={"username": uname, "password": "test1234"})
    assert tok.json()["code"] == 200

    r = client.post("/api/report/pdf/generate?report_id=1",
                    headers=auth_headers(tok.json()["data"]["token"]))
    assert r.status_code == 403


@requires_mysql
def test_report_test_endpoint(client, admin_token):
    assert client.get("/api/report/test",
                      headers=auth_headers(admin_token)).json()["code"] == 200
