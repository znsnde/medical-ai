"""
软删除 + 回收站测试（依赖本地 MySQL）
覆盖：软删隐藏/级联/文件保留、级联恢复、purge 物理删除、回收站列表/清空、统计排除、幂等/绑定防护

注意：API 调用走 app 的独立会话，`db` 夹具（另一会话）在 MySQL REPEATABLE READ 下持有旧快照，
验证前需 `_refresh(db)`（rollback 关掉旧事务，下次查询重建快照）才能读到 API 会话的提交。
teardown 一律用 purge_* 物理删除，不留软删残留。
"""
import uuid
from pathlib import Path

from config.settings import settings
from db.models import Patient, MedicalRecord, DiagnosisReport
from db.crud import patient_crud, record_crud, report_crud
from conftest import requires_mysql, auth_headers

MIN_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _refresh(db):
    """关闭当前事务使下次查询用最新快照（规避 REPEATABLE READ 旧快照读不到 API 会话的提交）"""
    db.rollback()


def _make_files():
    """落一个真实 DICOM（绝对路径）+ 真实 PDF（相对路径），返回 (dicom_abs, pdf_rel)"""
    dicom_dir = Path(settings.UPLOAD_PATH) / "dicom"
    report_dir = Path(settings.UPLOAD_PATH) / "report"
    dicom_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    dname = f"sd_{uuid.uuid4().hex}.dcm"
    fname = f"sd_{uuid.uuid4().hex}.pdf"
    dicom_abs = str(dicom_dir / dname)
    pdf_rel = f"static/upload/report/{fname}"
    Path(dicom_abs).write_bytes(b"DICM" + b"\x00" * 64)
    (report_dir / fname).write_bytes(MIN_PDF)
    return dicom_abs, pdf_rel


def _make_chain(db, with_files=False):
    """建 patient + record + report（with_files=True 时落真实 DICOM/PDF）；
    返回 (pat_id, rec_id, rep_id, pdf_rel)"""
    pat = patient_crud.create_patient(db, name="软删测试患者", age=42, gender="男",
                                      phone=f"199{uuid.uuid4().hex[:8]}")
    if with_files:
        dicom_abs, pdf_rel = _make_files()
        rec = record_crud.create_record(db, pat.id, "患者咳嗽咳痰三日",
                                        {"symptom": ["咳嗽"], "diagnosis": ["肺炎"]},
                                        dicom_file_path=dicom_abs)
    else:
        pdf_rel = None
        rec = record_crud.create_record(db, pat.id, "患者咳嗽咳痰三日",
                                        {"symptom": ["咳嗽"], "diagnosis": ["肺炎"]})
    rep = report_crud.create_report(db, rec.id, "影像分析", "诊断建议", pdf_path=pdf_rel or "")
    return pat.id, rec.id, rep.id, pdf_rel


# ── 1. 软删隐藏 ──
@requires_mysql
def test_soft_delete_patient_hides(client, db, admin_token):
    pat_id, rec_id, _, _ = _make_chain(db)
    h = auth_headers(admin_token)

    # 删除前可见
    assert client.get(f"/api/patient/{pat_id}", headers=h).json()["code"] == 200

    r = client.delete(f"/api/patient/{pat_id}", headers=h)
    assert r.json()["code"] == 200
    assert "回收站" in r.json()["msg"]

    # 详情 / 列表 / crud 均不可见
    assert client.get(f"/api/patient/{pat_id}", headers=h).json()["code"] != 200
    list_data = client.get("/api/patient/list/all", headers=h).json()["data"]
    assert all(p["id"] != pat_id for p in list_data)
    _refresh(db)
    assert patient_crud.get_patient_by_id(db, pat_id) is None

    # DB 直查：行仍存在且标记软删
    row = db.query(Patient).filter(Patient.id == pat_id).first()
    assert row is not None and row.is_deleted == 1 and row.deleted_at is not None

    patient_crud.purge_patient(db, pat_id)


# ── 2. 软删 record 级联 report、软删 report 仅自身 ──
@requires_mysql
def test_soft_delete_record_and_report(client, db, admin_token):
    pat_id, rec_id, rep_id, _ = _make_chain(db)
    h = auth_headers(admin_token)

    assert client.delete(f"/api/record/{rec_id}", headers=h).json()["code"] == 200
    _refresh(db)
    assert db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first().is_deleted == 1
    assert db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first().is_deleted == 1
    assert db.query(Patient).filter(Patient.id == pat_id).first().is_deleted == 0

    # 恢复病历 → 级联恢复 report
    assert client.post(f"/api/recycle/record/{rec_id}/restore", headers=h).json()["code"] == 200
    _refresh(db)
    assert db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first().is_deleted == 0
    assert db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first().is_deleted == 0

    # 软删报告 → 仅该 report
    assert client.delete(f"/api/diagnosis/{rep_id}", headers=h).json()["code"] == 200
    _refresh(db)
    assert db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first().is_deleted == 1
    assert db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first().is_deleted == 0

    report_crud.purge_report(db, rep_id)
    record_crud.purge_record(db, rec_id)
    patient_crud.purge_patient(db, pat_id)


# ── 3. 级联软删 patient 后文件保留 ──
@requires_mysql
def test_cascade_soft_delete_patient_files_preserved(client, db, admin_token):
    pat_id, rec_id, rep_id, pdf_rel = _make_chain(db, with_files=True)
    rec = db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first()
    dicom_abs = rec.dicom_file_path
    h = auth_headers(admin_token)

    assert client.delete(f"/api/patient/{pat_id}", headers=h).json()["code"] == 200
    _refresh(db)
    assert db.query(Patient).filter(Patient.id == pat_id).first().is_deleted == 1
    assert db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first().is_deleted == 1
    assert db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first().is_deleted == 1

    # 磁盘文件仍存在（软删不清文件）
    assert Path(dicom_abs).is_file()
    assert Path(pdf_rel).is_file()

    patient_crud.purge_patient(db, pat_id)


# ── 4. 恢复单条报告 ──
@requires_mysql
def test_restore_single_report(client, db, admin_token):
    pat_id, rec_id, rep_id, _ = _make_chain(db)
    h = auth_headers(admin_token)

    report_crud.delete_report(db, rep_id)
    r = client.post(f"/api/recycle/report/{rep_id}/restore", headers=h)
    assert r.json()["code"] == 200
    _refresh(db)
    row = db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first()
    assert row.is_deleted == 0 and row.deleted_at is None

    # 报告列表接口可见（不依赖 Neo4j）
    list_data = client.get("/api/diagnosis/list/all", headers=h).json()["data"]
    assert any(item["id"] == rep_id for item in list_data)

    record_crud.purge_record(db, rec_id)
    patient_crud.purge_patient(db, pat_id)


# ── 5. 级联恢复 patient ──
@requires_mysql
def test_restore_patient_cascade(client, db, admin_token):
    pat_id, rec_id, rep_id, _ = _make_chain(db)
    h = auth_headers(admin_token)

    patient_crud.delete_patient(db, pat_id)
    assert client.post(f"/api/recycle/patient/{pat_id}/restore", headers=h).json()["code"] == 200
    _refresh(db)
    assert db.query(Patient).filter(Patient.id == pat_id).first().is_deleted == 0
    assert db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first().is_deleted == 0
    assert db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first().is_deleted == 0

    record_crud.purge_record(db, rec_id)
    patient_crud.purge_patient(db, pat_id)


# ── 6. purge patient：行与文件都消失 ──
@requires_mysql
def test_purge_patient_files_and_rows(client, db, admin_token):
    pat_id, rec_id, rep_id, pdf_rel = _make_chain(db, with_files=True)
    rec = db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first()
    dicom_abs = rec.dicom_file_path
    h = auth_headers(admin_token)

    assert client.delete(f"/api/patient/{pat_id}", headers=h).json()["code"] == 200
    assert client.delete(f"/api/recycle/patient/{pat_id}/purge", headers=h).json()["code"] == 200
    _refresh(db)
    assert db.query(Patient).filter(Patient.id == pat_id).first() is None
    assert db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first() is None
    assert db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first() is None
    assert not Path(dicom_abs).exists()
    assert not Path(pdf_rel).exists()


# ── 7. purge record / report 同样清行 + 清文件 ──
@requires_mysql
def test_purge_record_and_report(client, db, admin_token):
    pat_id, rec_id, rep_id, pdf_rel = _make_chain(db, with_files=True)
    rec = db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first()
    dicom_abs = rec.dicom_file_path
    h = auth_headers(admin_token)

    # purge report：物理删 report 行 + pdf
    assert client.delete(f"/api/diagnosis/{rep_id}", headers=h).json()["code"] == 200
    assert client.delete(f"/api/recycle/report/{rep_id}/purge", headers=h).json()["code"] == 200
    _refresh(db)
    assert db.query(DiagnosisReport).filter(DiagnosisReport.id == rep_id).first() is None
    assert not Path(pdf_rel).exists()

    # purge record：物理删 record 行 + dicom
    assert client.delete(f"/api/record/{rec_id}", headers=h).json()["code"] == 200
    assert client.delete(f"/api/recycle/record/{rec_id}/purge", headers=h).json()["code"] == 200
    _refresh(db)
    assert db.query(MedicalRecord).filter(MedicalRecord.id == rec_id).first() is None
    assert not Path(dicom_abs).exists()

    patient_crud.purge_patient(db, pat_id)


# ── 8. 回收站列表只含已删项 ──
@requires_mysql
def test_recycle_bin_lists(client, db, admin_token):
    p1, r1, _, _ = _make_chain(db)
    p2, r2, _, _ = _make_chain(db)
    h = auth_headers(admin_token)

    patient_crud.delete_patient(db, p1)
    data = client.get("/api/recycle/patients", headers=h).json()["data"]
    assert any(p["id"] == p1 for p in data)
    assert all(p["id"] != p2 for p in data)

    record_crud.purge_record(db, r1)
    patient_crud.purge_patient(db, p1)
    record_crud.purge_record(db, r2)
    patient_crud.purge_patient(db, p2)


# ── 9. 清空回收站 ──
@requires_mysql
def test_clear_recycle_bin(client, db, admin_token):
    p1, r1, rep1, pdf_rel = _make_chain(db, with_files=True)
    rec1 = db.query(MedicalRecord).filter(MedicalRecord.id == r1).first()
    dicom_abs = rec1.dicom_file_path
    p2, r2, _, _ = _make_chain(db)
    h = auth_headers(admin_token)

    patient_crud.delete_patient(db, p1)   # 软删 p1（级联 r1/rep1）
    record_crud.delete_record(db, r2)     # 软删 r2（患者 p2 本身存活，不清）

    r = client.delete("/api/recycle/clear", headers=h)
    assert r.json()["code"] == 200
    counts = r.json()["data"]
    assert counts["patients"] >= 1
    assert counts["records"] >= 2
    assert counts["reports"] >= 1

    _refresh(db)
    assert db.query(Patient).filter(Patient.id == p1).first() is None        # p1 已物理清除
    assert db.query(Patient).filter(Patient.id == p2).first() is not None    # p2 未软删，保留
    assert db.query(MedicalRecord).filter(MedicalRecord.id == r1).first() is None
    assert db.query(MedicalRecord).filter(MedicalRecord.id == r2).first() is None
    assert db.query(DiagnosisReport).filter(DiagnosisReport.id == rep1).first() is None
    assert not Path(dicom_abs).exists()
    assert not Path(pdf_rel).exists()

    # alive 行保留
    p3, r3, _, _ = _make_chain(db)
    _refresh(db)
    assert db.query(Patient).filter(Patient.id == p3).first() is not None
    record_crud.purge_record(db, r3)
    patient_crud.purge_patient(db, p3)


# ── 10. 统计排除软删行 ──
@requires_mysql
def test_stats_exclude_deleted(client, db, admin_token):
    pat_id, rec_id, _, _ = _make_chain(db)
    h = auth_headers(admin_token)

    before = client.get("/api/dashboard/stats", headers=h).json()["data"]
    record_crud.delete_record(db, rec_id)   # 软删今天新建的病历
    after = client.get("/api/dashboard/stats", headers=h).json()["data"]

    assert after["total_records"] == before["total_records"] - 1
    assert after["today_records"] == before["today_records"] - 1

    record_crud.purge_record(db, rec_id)
    patient_crud.purge_patient(db, pat_id)


# ── 11. 二次软删失败 ──
@requires_mysql
def test_double_delete_fails(client, db, admin_token):
    pat_id, rec_id, _, _ = _make_chain(db)
    h = auth_headers(admin_token)

    assert client.delete(f"/api/patient/{pat_id}", headers=h).json()["code"] == 200
    assert client.delete(f"/api/patient/{pat_id}", headers=h).json()["code"] != 200

    record_crud.purge_record(db, rec_id)
    patient_crud.purge_patient(db, pat_id)


# ── 12. 软删患者不可被手机号认领 ──
@requires_mysql
def test_soft_deleted_patient_not_bindable(client, db):
    phone = f"199{uuid.uuid4().hex[:8]}"
    pat = patient_crud.create_patient(db, "绑定测试患者", 30, "女", phone)
    uname = f"bind_{uuid.uuid4().hex[:8]}"
    client.post("/api/auth/register/public",
                data={"username": uname, "password": "test1234", "real_name": "绑定用户"})
    tok = client.post("/api/auth/login", data={"username": uname, "password": "test1234"})\
        .json()["data"]["token"]
    h = auth_headers(tok)

    patient_crud.delete_patient(db, pat.id)   # 软删带手机号的档案
    r = client.post("/api/patient/bind", data={"phone": phone}, headers=h)
    assert r.json()["code"] != 200

    patient_crud.purge_patient(db, pat.id)
