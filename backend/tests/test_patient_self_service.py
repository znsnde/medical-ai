"""
患者自助查看报告冒烟测试（依赖本地 MySQL）
覆盖：手机号认领档案（绑定）、我的病历、我的报告、报告 PDF 下载本人放行/他人拒绝
"""
import uuid
from pathlib import Path

from config.settings import settings
from db.session import SessionLocal
from db.crud import patient_crud, record_crud, report_crud
from db.models import Patient
from conftest import requires_mysql, auth_headers

MIN_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

# 历史失败运行曾用固定手机号，可能残留已绑定的脏行；每次先清理，避免污染本次运行
_LEGACY_TEST_PHONES = ["19911112222", "19933334444", "19955556666"]


def _new_patient_token(client) -> tuple:
    """注册 + 登录一个患者，返回 (token, user_id)"""
    uname = f"pself_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register/public", data={
        "username": uname, "password": "test1234", "real_name": "自助测试患者"
    })
    assert r.json().get("code") == 200, r.json()
    r = client.post("/api/auth/login", data={"username": uname, "password": "test1234"})
    body = r.json()
    return body["data"]["token"], body["data"]["user"]["id"]


def _purge_legacy_patients():
    """物理删除历史失败运行遗留的测试患者（含软删残留），恢复干净数据"""
    db = SessionLocal()
    try:
        for phone in _LEGACY_TEST_PHONES:
            # 直接查任意状态的档案（get_patient_by_phone 已过滤软删行），purge 物理删干净
            pats = db.query(Patient).filter(Patient.phone == phone).all()
            for pat in pats:
                patient_crud.purge_patient(db, pat.id)
    finally:
        db.close()


@requires_mysql
def test_bind_flow(client):
    """未绑定空列表 → 手机号不存在绑定失败 → 绑定成功 → my-records 有病历；他人不可重复绑定"""
    _purge_legacy_patients()
    phone = f"199{uuid.uuid4().hex[:8]}"

    token, uid = _new_patient_token(client)
    token2, uid2 = _new_patient_token(client)
    h, h2 = auth_headers(token), auth_headers(token2)

    # 未绑定 → 空列表
    r = client.get("/api/patient/my-records", headers=h)
    assert r.json()["data"] == []

    # 手机号不存在 → 绑定失败
    r = client.post("/api/patient/bind", data={"phone": "19900000000"}, headers=h)
    assert r.json()["code"] != 200

    # 建档案（医生侧）+ 病历；捕获纯 int ID（session 关闭后 ORM 实例会 detached + expire）
    db = SessionLocal()
    try:
        pat = patient_crud.create_patient(db, "自助绑定患者", 40, "男", phone)
        pat_id = pat.id
        rec = record_crud.create_record(db, pat_id, "患者高血压伴头晕三日",
                                        {"symptom": ["头晕"], "diagnosis": ["高血压"]})
        rec_id = rec.id
    finally:
        db.close()

    try:
        # 绑定成功
        r = client.post("/api/patient/bind", data={"phone": phone}, headers=h)
        assert r.json()["code"] == 200, r.json()
        assert r.json()["data"]["user_id"] == uid

        # 已被他人绑定 → 拒绝（档案唯一性）
        r = client.post("/api/patient/bind", data={"phone": phone}, headers=h2)
        assert r.json()["code"] != 200

        # my-records 返回该病历
        r = client.get("/api/patient/my-records", headers=h)
        data = r.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == rec_id
    finally:
        db = SessionLocal()
        try:
            record_crud.purge_record(db, rec_id)
            patient_crud.purge_patient(db, pat_id)
        finally:
            db.close()


@requires_mysql
def test_my_reports_and_pdf_access(client):
    """我的报告仅本人病历；PDF 下载本人 200、他人 403、未绑定 403"""
    _purge_legacy_patients()
    phoneA = f"199{uuid.uuid4().hex[:8]}"
    phoneB = f"199{uuid.uuid4().hex[:8]}"

    token, uid = _new_patient_token(client)
    token2, uid2 = _new_patient_token(client)
    h, h2 = auth_headers(token), auth_headers(token2)

    db = SessionLocal()
    try:
        pat = patient_crud.create_patient(db, "报告患者A", 50, "女", phoneA)
        pat_id = pat.id
        pat2 = patient_crud.create_patient(db, "报告患者B", 45, "男", phoneB)
        pat2_id = pat2.id
        patient_crud.bind_patient(db, pat_id, uid)
        patient_crud.bind_patient(db, pat2_id, uid2)

        rec = record_crud.create_record(db, pat_id, "A的病历文本", {"symptom": ["头痛"]})
        rec_id = rec.id
        rec2 = record_crud.create_record(db, pat2_id, "B的病历文本", {"symptom": ["咳嗽"]})
        rec2_id = rec2.id

        # A、B 的报告都已生成 PDF（B 的报告用于验证「他人下载」权限拒绝）
        report_dir = Path(settings.UPLOAD_PATH) / "report"
        report_dir.mkdir(parents=True, exist_ok=True)
        fname_a = f"pself_{uuid.uuid4().hex}.pdf"
        fname_b = f"pself_{uuid.uuid4().hex}.pdf"
        (report_dir / fname_a).write_bytes(MIN_PDF)
        (report_dir / fname_b).write_bytes(MIN_PDF)
        rep = report_crud.create_report(db, rec_id, "影像分析A", "诊断建议A",
                                        pdf_path=f"static/upload/report/{fname_a}")
        rep_id = rep.id
        rep2 = report_crud.create_report(db, rec2_id, "影像分析B", "诊断建议B",
                                         pdf_path=f"static/upload/report/{fname_b}")
        rep2_id = rep2.id
    finally:
        db.close()

    try:
        # 我的报告：只含 A，pdf_status 正确
        r = client.get("/api/patient/my-reports", headers=h)
        data = r.json()["data"]
        assert len(data) == 1
        assert data[0]["report_id"] == rep_id
        assert data[0]["pdf_status"] is True

        # 下载本人报告 PDF → 200
        r = client.get(f"/api/report/pdf/download/{rep_id}", headers=h)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")

        # 下载他人报告 → 403
        r = client.get(f"/api/report/pdf/download/{rep2_id}", headers=h)
        assert r.status_code == 403

        # 未绑定账号 my-reports → 空
        token3, _ = _new_patient_token(client)
        r = client.get("/api/patient/my-reports", headers=auth_headers(token3))
        assert r.json()["data"] == []
    finally:
        db = SessionLocal()
        try:
            report_crud.purge_report(db, rep_id)
            report_crud.purge_report(db, rep2_id)
            record_crud.purge_record(db, rec_id)
            record_crud.purge_record(db, rec2_id)
            patient_crud.purge_patient(db, pat_id)
            patient_crud.purge_patient(db, pat2_id)
        finally:
            db.close()
        try:
            (report_dir / fname_a).unlink(missing_ok=True)
            (report_dir / fname_b).unlink(missing_ok=True)
        except (NameError, OSError):
            pass
