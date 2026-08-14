"""
多轮问诊对话流程测试（依赖本地 MySQL）
覆盖：新会话创建与续聊（消息数 2→4）、空消息拒绝、他人会话 403（IDOR）、会话列表/消息/删除、_parse_json_reply 单元
LLM 调用打桩：api.consultation_api.diagnostic_interview
"""
import uuid

import pytest

from medical_business.consultation import _parse_json_reply
from conftest import requires_mysql, auth_headers


@pytest.fixture()
def tok_patient_a(client):
    """一个患者 token；MySQL 不可用时跳过"""
    from conftest import _mysql_available
    if not _mysql_available():
        pytest.skip("MySQL 不可用，跳过")
    return _register_and_login(client, "fix")


def _register_and_login(client, tag):
    """自助注册患者并登录，返回 (token)"""
    uname = f"cons_{tag}_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register/public", data={
        "username": uname, "password": "test1234", "real_name": "问诊测试患者"
    })
    assert r.json().get("code") == 200, r.json()
    tok = client.post("/api/auth/login", data={"username": uname, "password": "test1234"})
    assert tok.json()["code"] == 200
    return tok.json()["data"]["token"]


def _fake_interview(messages):
    return {"reply": "好的，请告诉我哪里不舒服？", "stage": "collecting",
            "suggestions": ["头痛", "腹痛", "发热"]}


@requires_mysql
def test_consultation_new_session_and_continue(client, monkeypatch):
    """新会话（2 条消息）→ 续聊（4 条：续聊会同时追加用户新消息 + AI 回复）→ 消息内容完整"""
    monkeypatch.setattr("api.consultation_api.diagnostic_interview", _fake_interview)
    tok = _register_and_login(client, "flow")
    h = auth_headers(tok)

    # 新会话
    r = client.post("/api/consultation/chat", json={
        "messages": [{"role": "user", "content": "我最近头晕"}], "department": "神经内科"
    }, headers=h)
    body = r.json()
    assert body["code"] == 200, body
    data = body["data"]
    assert data["reply"] == "好的，请告诉我哪里不舒服？"
    assert data["stage"] == "collecting"
    sid = data["session_id"]
    assert sid

    # 会话列表：message_count == 2（用户首条 + AI 回复）
    sessions = client.get("/api/consultation/sessions", headers=h).json()["data"]
    mine = next(s for s in sessions if s["id"] == sid)
    assert mine["message_count"] == 2
    assert mine["department"] == "神经内科"

    # 会话消息
    msgs = client.get(f"/api/consultation/session/{sid}", headers=h).json()["data"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "我最近头晕"

    # 续聊 → 4 条（用户新消息 + AI 回复各追加一条）
    r2 = client.post("/api/consultation/chat", json={
        "messages": [{"role": "user", "content": "还会恶心"}], "session_id": sid
    }, headers=h)
    assert r2.json()["code"] == 200, r2.json()
    assert r2.json()["data"]["session_id"] == sid

    sessions = client.get("/api/consultation/sessions", headers=h).json()["data"]
    assert next(s for s in sessions if s["id"] == sid)["message_count"] == 4

    msgs = client.get(f"/api/consultation/session/{sid}", headers=h).json()["data"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[2]["content"] == "还会恶心"

    # 清理
    client.delete(f"/api/consultation/session/{sid}", headers=h)


@requires_mysql
def test_consultation_empty_messages(client, tok_patient_a):
    r = client.post("/api/consultation/chat", json={"messages": []},
                    headers=auth_headers(tok_patient_a))
    body = r.json()
    assert body["code"] != 200
    assert "请提供对话消息" in body["msg"]


@requires_mysql
def test_consultation_other_users_session_403(client):
    """IDOR：他人会话不可读/写/删（403）"""
    tok_a = _register_and_login(client, "a")
    tok_b = _register_and_login(client, "b")
    h_a = auth_headers(tok_a)
    h_b = auth_headers(tok_b)

    # A 建会话
    sid = client.post("/api/consultation/chat", json={
        "messages": [{"role": "user", "content": "A 的问题"}]
    }, headers=h_a).json()["data"]["session_id"]

    # B 读 → 403
    assert client.get(f"/api/consultation/session/{sid}", headers=h_b).status_code == 403
    # B 续聊 → 403
    assert client.post("/api/consultation/chat", json={
        "messages": [{"role": "user", "content": "B 插话"}], "session_id": sid
    }, headers=h_b).status_code == 403
    # B 删 → 403
    assert client.delete(f"/api/consultation/session/{sid}", headers=h_b).status_code == 403
    # 不存在 → 404
    assert client.get("/api/consultation/session/999999999", headers=h_a).status_code == 404

    # 清理
    client.delete(f"/api/consultation/session/{sid}", headers=h_a)


@requires_mysql
def test_consultation_delete_and_empty_list(client, tok_patient_a):
    h = auth_headers(tok_patient_a)
    sid = client.post("/api/consultation/chat", json={
        "messages": [{"role": "user", "content": "删除我"}]
    }, headers=h).json()["data"]["session_id"]

    assert client.delete(f"/api/consultation/session/{sid}", headers=h).json()["code"] == 200
    assert client.get(f"/api/consultation/session/{sid}", headers=h).status_code == 404
    # 删除后列表不再出现
    sessions = client.get("/api/consultation/sessions", headers=h).json()["data"]
    assert all(s["id"] != sid for s in sessions)


# ── _parse_json_reply 单元测试（不依赖 MySQL）──
def test_parse_json_reply_direct():
    raw = '{"reply": "今天感觉如何", "stage": "collecting", "suggestions": ["还行", "不好"]}'
    assert _parse_json_reply(raw)["stage"] == "collecting"


def test_parse_json_reply_fenced():
    raw = "好的\n```json\n{\"reply\": \"注意休息\", \"stage\": \"done\", \"suggestions\": [\"谢谢\"]}\n```\n"
    d = _parse_json_reply(raw)
    assert d["reply"] == "注意休息" and d["stage"] == "done"


def test_parse_json_reply_brace_extract():
    raw = "回复如下：{\"reply\": \"多喝水\", \"stage\": \"done\", \"suggestions\": []}"
    assert _parse_json_reply(raw)["reply"] == "多喝水"


def test_parse_json_reply_fallback():
    d = _parse_json_reply("医生说了些非 JSON 的话")
    assert d["reply"] == "医生说了些非 JSON 的话"
    assert d["stage"] == "collecting"
    assert len(d["suggestions"]) == 3
