"""
AI 诊断核心链路冒烟测试（依赖本地 MySQL）
LLM / RAG 打桩，验证：病历入库 → 生成诊断 → 报告返回 → 关联知识字段
"""
import pytest
from conftest import requires_mysql, auth_headers


@requires_mysql
def test_diagnosis_generate_flow(client, db, admin_token, monkeypatch):
    from db.crud import patient_crud, record_crud, report_crud

    # ── 造测试数据 ──
    pat = patient_crud.create_patient(db, name="冒烟患者", age=50, gender="男", phone="13800000000")
    rec = record_crud.create_record(
        db=db,
        patient_id=pat.id,
        raw_text="患者高血压伴头晕乏力三日，血压150/95。",
        structured_data={
            "symptom": ["头晕", "乏力"],
            "past_history": ["高血压"],
            "diagnosis": ["高血压"],
            "medicine": ["硝苯地平"],
        },
    )

    try:
        # ── 打桩 LLM 与 RAG（避免真实调用 DeepSeek / Milvus） ──
        monkeypatch.setattr(
            "medical_business.assist_diagnosis.llm_generate_diagnosis",
            lambda record_text, structured_data, reference_knowledge, image_analysis="": "AI诊断建议：考虑高血压病，建议监测血压并低盐饮食。",
        )
        monkeypatch.setattr(
            "medical_business.assist_diagnosis.rag_search_medical_knowledge",
            lambda query, top_k=3: ["高血压诊疗指南参考"],
        )

        # ── 调生成诊断接口 ──
        r = client.post(f"/api/diagnosis/generate?record_id={rec.id}",
                        headers=auth_headers(admin_token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["code"] == 200, body
        data = body["data"]
        assert data["record_id"] == rec.id
        assert data["patient_name"] == "冒烟患者"
        assert "高血压" in data["diagnosis_suggest"]

        # ── 关联知识字段（知识图谱接入诊断流程） ──
        assert isinstance(data.get("knowledge"), dict)
        assert set(data["knowledge"].keys()) >= {"related_info", "drug_warnings", "complications"}

        # ── 报告详情接口同样携带知识 ──
        r2 = client.get(f"/api/diagnosis/{data['id']}", headers=auth_headers(admin_token))
        assert r2.status_code == 200
        assert isinstance(r2.json()["data"].get("knowledge"), dict)
    finally:
        # ── 清理测试数据（purge 物理删除，不留软删残留） ──
        report = report_crud.get_report_by_record(db, rec.id)
        for rep in report:
            report_crud.purge_report(db, rep.id)
        record_crud.purge_record(db, rec.id)
        patient_crud.purge_patient(db, pat.id)
