"""
登录与权限冒烟测试（依赖本地 MySQL）
"""
from conftest import requires_mysql, auth_headers


@requires_mysql
def test_login_success(client):
    """管理员正确登录 → token + 用户信息"""
    r = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["token"]
    assert body["data"]["user"]["role"] == "admin"


@requires_mysql
def test_login_wrong_password(client):
    """密码错误 → body.code 401（项目旧约定：HTTP 200 + body 状态码）"""
    r = client.post("/api/auth/login", data={"username": "admin", "password": "definitely-wrong"})
    assert r.status_code == 200
    assert r.json()["code"] == 401


@requires_mysql
def test_login_inactive_user(client):
    """不存在的用户 → 401"""
    r = client.post("/api/auth/login", data={"username": "no_such_user_xyz", "password": "x"})
    assert r.status_code == 200
    assert r.json()["code"] == 401


@requires_mysql
def test_role_forbidden_patient_access_admin(client, admin_token):
    """患者访问管理员接口 → HTTP 403"""
    uname = "smoke_pat_403"
    # 注册患者
    reg = client.post("/api/auth/register/public", data={
        "username": uname, "password": "test1234", "real_name": "冒烟测试患者"
    })
    assert reg.json()["code"] == 200, reg.json()

    # 患者登录拿 token
    login = client.post("/api/auth/login", data={"username": uname, "password": "test1234"})
    ptoken = login.json()["data"]["token"]
    puser_id = login.json()["data"]["user"]["id"]

    # 患者访问管理员接口 → 403
    r = client.get("/api/auth/users", headers=auth_headers(ptoken))
    assert r.status_code == 403
    assert r.json()["code"] == 403

    # 清理测试用户
    cleanup = client.delete(f"/api/auth/users/{puser_id}", headers=auth_headers(admin_token))
    assert cleanup.json()["code"] == 200, cleanup.json()


@requires_mysql
def test_admin_token_works(client, admin_token):
    """管理员 token 访问受保护接口 → 200"""
    r = client.get("/api/auth/me", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["data"]["username"] == "admin"


@requires_mysql
def test_register_rejects_weak_password(client):
    """密码强度：过短 / 无字母 / 无数字 → 拒绝注册"""
    # 过短
    r = client.post("/api/auth/register/public", data={
        "username": "weak_short_xx", "password": "abc123"
    })
    assert r.json()["code"] != 200
    assert "8" in r.json()["msg"]
    # 只有字母无数字
    r = client.post("/api/auth/register/public", data={
        "username": "weak_letter_xx", "password": "abcdefgh"
    })
    assert r.json()["code"] != 200
    assert "数字" in r.json()["msg"]
    # 只有数字无字母
    r = client.post("/api/auth/register/public", data={
        "username": "weak_digit_xx", "password": "12345678"
    })
    assert r.json()["code"] != 200
    assert "字母" in r.json()["msg"]


@requires_mysql
def test_login_brute_force_lockout(client):
    """同一用户名连续失败 5 次 → 第 6 次被锁定（code 429）"""
    uname = "bf_lock_test_zzz"  # 不存在的用户，只消耗失败计数
    for _ in range(5):
        r = client.post("/api/auth/login", data={"username": uname, "password": "wrong-pwd-1"})
        assert r.json()["code"] == 401
    # 第 6 次：锁定拦截
    r = client.post("/api/auth/login", data={"username": uname, "password": "wrong-pwd-1"})
    assert r.json()["code"] == 429
    assert "稍后再试" in r.json()["msg"]
