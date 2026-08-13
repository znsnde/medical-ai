import re
import threading
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import user_crud
from core.security import hash_password, verify_password, create_access_token, get_current_user, require_roles
from core.logger import get_logger
from utils.common import resp_success, resp_fail

logger = get_logger("audit")

router = APIRouter()


# ══════════ 登录防爆破（进程内存，单实例够用） ══════════
# 同一用户名连续失败 5 次 → 锁定 15 分钟；成功登录或锁定期满后自动重置
_LOGIN_FAIL_LIMIT = 5
_LOGIN_LOCK_SECONDS = 15 * 60
_login_fail_count = defaultdict(int)   # username -> 连续失败次数
_login_lock_until = {}                 # username -> 解锁时间戳
_login_lock = threading.Lock()


def _login_remaining_lock(username: str) -> float:
    """返回剩余锁定秒数；未锁定返回 0。仅在确有锁定且锁定期满时清零失败计数。"""
    with _login_lock:
        until = _login_lock_until.get(username, 0)
        if until <= time.time():
            # 有锁但已过期 → 重置整个状态；未锁过（get 默认 0）→ 保留失败计数
            if _login_lock_until.pop(username, None) is not None:
                _login_fail_count.pop(username, None)
            return 0.0
        return until - time.time()


def _record_login_fail(username: str):
    """记录一次失败；达到阈值则触发锁定"""
    with _login_lock:
        _login_fail_count[username] += 1
        if _login_fail_count[username] >= _LOGIN_FAIL_LIMIT:
            _login_lock_until[username] = time.time() + _LOGIN_LOCK_SECONDS


def _reset_login_state(username: str):
    """登录成功后清零失败/锁定状态"""
    with _login_lock:
        _login_fail_count.pop(username, None)
        _login_lock_until.pop(username, None)


# ══════════ 密码强度校验 ══════════
def _check_password_strength(password: str):
    """密码强度：至少 8 位，且同时包含字母和数字（兼容 test1234 / admin123）"""
    if len(password) < 8:
        return "密码至少8个字符"
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "密码需同时包含字母和数字"
    return None

# ── 登录（公开） ──
@router.post("/login", summary="用户登录")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # 防爆破：连续失败达到阈值后先拦截，避免继续做 bcrypt 校验
    remaining = _login_remaining_lock(username)
    if remaining > 0:
        logger.warning("[审计] 登录被锁定 username=%s 剩余=%.0f秒", username, remaining)
        return resp_fail("登录失败次数过多，请稍后再试", code=429)

    user = user_crud.get_user_by_username(db, username)
    if not user:
        _record_login_fail(username)
        logger.warning("[审计] 登录失败 username=%s 原因=用户不存在", username)
        return resp_fail("用户名或密码错误", code=401)
    if not user.is_active:
        logger.warning("[审计] 登录失败 username=%s 原因=账号被禁用", username)
        return resp_fail("该用户已被禁用，请联系管理员", code=403)
    if not verify_password(password, user.password_hash):
        _record_login_fail(username)
        logger.warning("[审计] 登录失败 username=%s 原因=密码错误", username)
        return resp_fail("用户名或密码错误", code=401)

    # 登录成功：清零失败/锁定状态
    _reset_login_state(username)
    token = create_access_token(data={"user_id": user.id})
    logger.info("[审计] 登录成功 username=%s role=%s", user.username, user.role)
    return resp_success(data={
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "role": user.role,
            "department": user.department
        }
    }, msg="登录成功")

# ── 用户自助注册（公开） ──
@router.post("/register/public", summary="用户自助注册")
def register_public(
    username: str = Form(...),
    password: str = Form(...),
    real_name: str = Form(""),
    department: str = Form(""),
    db: Session = Depends(get_db)
):
    if not username or len(username) < 2:
        return resp_fail("用户名至少2个字符")
    weak = _check_password_strength(password)
    if weak:
        return resp_fail(weak)
    exist = user_crud.get_user_by_username(db, username)
    if exist:
        return resp_fail("用户名已存在")
    user = user_crud.create_user(
        db=db,
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        role="patient",
        department=department
    )
    logger.info("[审计] 用户自助注册 username=%s", user.username)
    return resp_success(data={
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role
    }, msg="注册成功，请登录")

# ── 管理员注册 ──
@router.post("/register", summary="管理员注册新用户", dependencies=[Depends(require_roles(["admin"]))])
def register(
    username: str = Form(...),
    password: str = Form(...),
    real_name: str = Form(""),
    role: str = Form("doctor"),
    department: str = Form(""),
    db: Session = Depends(get_db)
):
    # 校验参数
    if not username or len(username) < 2:
        return resp_fail("用户名至少2个字符")
    weak = _check_password_strength(password)
    if weak:
        return resp_fail(weak)
    if role not in ["admin", "doctor", "patient"]:
        return resp_fail("角色无效，可选: admin/doctor/patient")

    # 检查用户名是否已存在
    exist = user_crud.get_user_by_username(db, username)
    if exist:
        return resp_fail("用户名已存在")

    user = user_crud.create_user(
        db=db,
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        role=role,
        department=department
    )
    logger.info("[审计] 管理员创建用户 username=%s role=%s", user.username, user.role)
    return resp_success(data={
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
        "department": user.department
    }, msg="用户注册成功")

# ── 获取当前用户信息 ──
@router.get("/me", summary="获取当前用户信息")
def get_me(current_user=Depends(get_current_user)):
    return resp_success(data={
        "id": current_user.id,
        "username": current_user.username,
        "real_name": current_user.real_name,
        "role": current_user.role,
        "department": current_user.department
    })

# ── 用户列表（管理员） ──
@router.get("/users", summary="用户列表", dependencies=[Depends(require_roles(["admin"]))])
def list_users(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    data = user_crud.get_user_list(db, skip, limit)
    return resp_success(data=data)

# ── 删除用户（管理员） ──
@router.delete("/users/{user_id}", summary="删除用户", dependencies=[Depends(require_roles(["admin"]))])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    ok = user_crud.delete_user(db, user_id)
    if not ok:
        return resp_fail("用户不存在或删除失败")
    logger.info("[审计] 管理员删除用户 user_id=%s", user_id)
    return resp_success(msg="用户已删除")

# ── 更新用户信息（管理员） ──
@router.put("/users/{user_id}", summary="更新用户信息", dependencies=[Depends(require_roles(["admin"]))])
def update_user(
    user_id: int,
    real_name: str = Form(None),
    role: str = Form(None),
    department: str = Form(None),
    is_active: int = Form(None),
    password: str = Form(None),
    db: Session = Depends(get_db)
):
    update_kwargs = {}
    if real_name is not None:
        update_kwargs["real_name"] = real_name
    if role is not None:
        if role not in ["admin", "doctor", "patient"]:
            return resp_fail("角色无效，可选: admin/doctor/patient")
        update_kwargs["role"] = role
    if department is not None:
        update_kwargs["department"] = department
    if is_active is not None:
        update_kwargs["is_active"] = is_active
    if password:
        weak = _check_password_strength(password)
        if weak:
            return resp_fail(weak)
        update_kwargs["password_hash"] = hash_password(password)

    user = user_crud.update_user(db, user_id, **update_kwargs)
    if not user:
        return resp_fail("用户不存在")
    logger.info("[审计] 管理员更新用户 user_id=%s 变更项=%s", user_id, list(update_kwargs.keys()))
    return resp_success(data={
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
        "department": user.department,
        "is_active": user.is_active
    }, msg="用户信息更新成功")
