from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config.settings import settings
from db.session import get_db
from db.crud import user_crud

# ── 密码加密（直接使用 bcrypt，避免 passlib 兼容问题） ──

def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希值是否一致"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# ── JWT 令牌 ──
# 使用独立随机 JWT_SECRET，禁止复用 LLM_API_KEY（API key 泄露=令牌可伪造）
SECRET_KEY = settings.JWT_SECRET
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET 未配置！请在 .env 中设置独立随机密钥，"
        "例如：openssl rand -hex 32（勿复用 LLM_API_KEY）"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT access_token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ── FastAPI 依赖（Bearer token 提取） ──
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    """从请求头中解析 Bearer token，返回 User 对象"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="令牌无效")
    except JWTError:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

    user = user_crud.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    return user

def require_roles(roles: list):
    """角色校验依赖（用于路由）: require_roles(["admin", "doctor"])"""
    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {roles} 角色权限，当前角色为 {current_user.role}"
            )
        return current_user
    return role_checker
