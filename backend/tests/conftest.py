"""
pytest 公共夹具
- client: FastAPI TestClient（真实后端，不 mock）
- db: SQLAlchemy 会话
- admin_token: 管理员登录令牌（MySQL 不可用则 skip）

外部服务（MySQL / Neo4j / Milvus / DeepSeek）不可用时按模块 skip，不阻塞其余用例。
"""
import pytest
from fastapi.testclient import TestClient


def _mysql_available() -> bool:
    try:
        from sqlalchemy import text
        from db.session import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _neo4j_available() -> bool:
    try:
        from medical_business.knowledge_graph import get_driver
        with get_driver().session() as s:
            s.run("RETURN 1").single()
        return True
    except Exception:
        return False


requires_mysql = pytest.mark.skipif(not _mysql_available(), reason="MySQL 不可用，跳过")
requires_neo4j = pytest.mark.skipif(not _neo4j_available(), reason="Neo4j 不可用，跳过")


@pytest.fixture(scope="session")
def client():
    """FastAPI 测试客户端（整个会话复用一次 app 实例）"""
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    from db.session import SessionLocal
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def admin_token(client):
    """管理员登录令牌；MySQL 不可用时跳过"""
    if not _mysql_available():
        pytest.skip("MySQL 不可用，跳过")
    resp = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    body = resp.json()
    assert body.get("code") == 200, f"管理员登录失败: {body}"
    return body["data"]["token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
