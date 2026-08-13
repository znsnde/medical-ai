from sqlalchemy.orm import Session
from db.models import User
from datetime import datetime

# 根据用户名查询用户
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

# 根据ID查询用户
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# 创建用户（已在外层做密码哈希）
def create_user(
    db: Session,
    username: str,
    password_hash: str,
    real_name: str = "",
    role: str = "doctor",
    department: str = ""
):
    db_obj = User(
        username=username,
        password_hash=password_hash,
        real_name=real_name,
        role=role,
        department=department,
        is_active=1,
        create_time=datetime.now()
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 分页查询用户列表（排除密码哈希）
def get_user_list(db: Session, skip: int = 0, limit: int = 20):
    users = db.query(User).offset(skip).limit(limit).all()
    # 不返回密码哈希
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "real_name": u.real_name,
            "role": u.role,
            "department": u.department,
            "is_active": u.is_active,
            "create_time": str(u.create_time)[:19] if u.create_time else ""
        })
    return result

# 删除用户
def delete_user(db: Session, user_id: int):
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True

# 更新用户信息
def update_user(
    db: Session,
    user_id: int,
    real_name: str = None,
    role: str = None,
    department: str = None,
    is_active: int = None,
    password_hash: str = None
):
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    if real_name is not None:
        user.real_name = real_name
    if role is not None:
        user.role = role
    if department is not None:
        user.department = department
    if is_active is not None:
        user.is_active = is_active
    if password_hash is not None:
        user.password_hash = password_hash
    db.commit()
    db.refresh(user)
    return user
