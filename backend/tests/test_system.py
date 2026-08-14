"""
系统模块测试：审计日志查询（方案 A：解析 logs/backend.log）
依赖本地 MySQL（登录）；main.py 导入即 setup_logging()，登录/注册等操作会真实写入 [审计] 行，
故可确定性断言结构与过滤行为。
"""
import uuid

from conftest import requires_mysql, auth_headers


@requires_mysql
def test_audit_admin_access(client, admin_token):
    """管理员可查审计日志；返回结构与字段合法，且含本次登录的审计行"""
    r = client.get("/api/system/audit", params={"limit": 100},
                   headers=auth_headers(admin_token))
    body = r.json()
    assert body["code"] == 200, body
    data = body["data"]
    assert isinstance(data, dict)
    assert data["total"] >= 1
    assert isinstance(data["items"], list)
    for it in data["items"]:
        assert {"time", "level", "message"} <= set(it)
        assert it["level"] in ("INFO", "WARNING")
    # admin_token 夹具登录成功必写审计行（最新在前）
    assert any("登录成功" in it["message"] for it in data["items"])


@requires_mysql
def test_audit_requires_admin(client):
    """患者 token → 403；匿名 → 401"""
    uname = f"aud_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register/public", data={
        "username": uname, "password": "test1234", "real_name": "审计权限测试"
    })
    assert r.json().get("code") == 200, r.json()
    tok = client.post("/api/auth/login", data={"username": uname, "password": "test1234"})
    assert tok.json()["code"] == 200
    h = auth_headers(tok.json()["data"]["token"])

    assert client.get("/api/system/audit", headers=h).json()["code"] == 403
    assert client.get("/api/system/audit").status_code == 401


@requires_mysql
def test_audit_level_filter(client, admin_token):
    """按级别过滤：触发一条 WARNING 登录失败后，?level=warning 返回全为 WARNING"""
    h = auth_headers(admin_token)
    # 触发一条 WARNING 审计（随机用户名 → 登录失败原因=用户不存在）
    client.post("/api/auth/login",
                data={"username": f"no_{uuid.uuid4().hex[:8]}", "password": "wrong"})
    r = client.get("/api/system/audit", params={"level": "warning", "limit": 100}, headers=h)
    items = r.json()["data"]["items"]
    assert items, "应存在 WARNING 审计行"
    assert all(it["level"] == "WARNING" for it in items)


@requires_mysql
def test_audit_keyword_filter(client, admin_token):
    """按关键字过滤：?keyword=登录成功 全部命中"""
    r = client.get("/api/system/audit", params={"keyword": "登录成功", "limit": 100},
                   headers=auth_headers(admin_token))
    items = r.json()["data"]["items"]
    assert items, "应存在登录成功审计行"
    assert all("登录成功" in it["message"] for it in items)


@requires_mysql
def test_audit_pagination(client, admin_token):
    """分页：skip/limit 的 total 与全量一致、切片正确"""
    h = auth_headers(admin_token)
    full = client.get("/api/system/audit", params={"limit": 500}, headers=h).json()["data"]
    if full["total"] >= 3:
        page = client.get("/api/system/audit", params={"skip": 1, "limit": 2}, headers=h).json()["data"]
        assert page["total"] == full["total"]
        assert page["items"] == full["items"][1:3]


@requires_mysql
def test_audit_missing_file(client, admin_token, monkeypatch):
    """日志文件缺失时兜底返回空列表，不报错"""
    monkeypatch.setattr("api.system_api.get_log_file_path",
                        lambda: "C:/nonexistent_audit_dir/backend.log")
    body = client.get("/api/system/audit", headers=auth_headers(admin_token)).json()
    assert body["code"] == 200
    assert body["data"]["total"] == 0
    assert body["data"]["items"] == []
