"""
应用启动与路由冒烟测试
不依赖任何外部服务（仅验证 app 能启动、路由注册、鉴权中间件生效）
"""
from conftest import auth_headers


def test_health_check(client):
    """根路径健康检查"""
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "启动成功" in body["msg"]
    assert body["server_port"] == 8000


def test_critical_routes_registered(client):
    """核心模块路由均已注册（直接请求，非 404 即已挂载）"""
    endpoints = [
        ("POST", "/api/auth/login"),
        ("GET", "/api/auth/me"),
        ("POST", "/api/record/struct"),
        ("POST", "/api/diagnosis/generate"),
        ("POST", "/api/patient/add"),
        ("GET", "/api/kg/graph"),
        ("GET", "/api/dashboard/stats"),
        ("POST", "/api/consultation/chat"),
    ]
    for method, url in endpoints:
        r = client.request(method, url)
        assert r.status_code != 404, f"路由未注册: {method} {url}"


def test_protected_endpoint_no_token_401(client):
    """无 token 访问受保护接口 → HTTP 401 + 统一 JSON"""
    r = client.get("/api/kg/graph")
    assert r.status_code == 401
    body = r.json()
    assert body.get("code") == 401
    assert body.get("detail")


def test_invalid_token_401(client):
    """伪造 token → HTTP 401"""
    r = client.get("/api/kg/graph", headers=auth_headers("fake.token.value"))
    assert r.status_code == 401
    assert r.json().get("code") == 401
