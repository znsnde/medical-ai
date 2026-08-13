from sqlalchemy.orm import Session
from db.models import ConsultSession, ConsultMessage
from datetime import datetime


def create_session(db: Session, department: str, user_id: int, first_msg: str) -> ConsultSession:
    session = ConsultSession(
        title=first_msg[:50],
        department=department,
        user_id=user_id,
        message_count=1,
        create_time=datetime.now(),
        update_time=datetime.now()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    # 保存第一条消息
    _add_message(db, session.id, "user", first_msg)
    return session


def _add_message(db: Session, session_id: int, role: str, content: str):
    msg = ConsultMessage(session_id=session_id, role=role, content=content, create_time=datetime.now())
    db.add(msg)
    db.commit()


def append_message(db: Session, session_id: int, role: str, content: str):
    _add_message(db, session_id, role, content)
    db.query(ConsultSession).filter(ConsultSession.id == session_id).update({
        ConsultSession.message_count: ConsultSession.message_count + 1,
        ConsultSession.update_time: datetime.now()
    })
    db.commit()


def get_user_sessions(db: Session, user_id: int, skip=0, limit=20):
    return db.query(ConsultSession).filter(
        ConsultSession.user_id == user_id
    ).order_by(ConsultSession.update_time.desc()).offset(skip).limit(limit).all()


def get_session(db: Session, session_id: int):
    """按ID取会话（调用方需自行校验归属）"""
    return db.query(ConsultSession).filter(ConsultSession.id == session_id).first()


def get_session_messages(db: Session, session_id: int):
    return db.query(ConsultMessage).filter(
        ConsultMessage.session_id == session_id
    ).order_by(ConsultMessage.id).all()


def update_session_title(db: Session, session_id: int, title: str):
    db.query(ConsultSession).filter(ConsultSession.id == session_id).update({
        ConsultSession.title: title
    })
    db.commit()


def delete_session(db: Session, session_id: int):
    db.query(ConsultMessage).filter(ConsultMessage.session_id == session_id).delete()
    db.query(ConsultSession).filter(ConsultSession.id == session_id).delete()
    db.commit()
