"""
多轮诊断式问询 API
接收对话历史，返回 AI 医生回复 + 快捷建议
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import consult_crud
from core.security import get_current_user
from medical_business.consultation import diagnostic_interview
from utils.common import resp_success, resp_fail

router = APIRouter()


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[int] = None
    department: Optional[str] = None


@router.post("/chat", summary="多轮问诊对话")
def consultation_chat(req: ChatRequest, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    if not req.messages or len(req.messages) == 0:
        return resp_fail("请提供对话消息")

    messages_dict = [{"role": m.role, "content": m.content} for m in req.messages]
    result = diagnostic_interview(messages_dict)

    # 保存到数据库
    try:
        last_user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        if req.session_id:
            # 已有会话 → 追加消息
            consult_crud.append_message(db, req.session_id, "user", last_user_msg)
            consult_crud.append_message(db, req.session_id, "assistant", result.get("reply", ""))
            sid = req.session_id
        else:
            # 新会话 → 创建
            session = consult_crud.create_session(db, req.department or "内科", current_user.id, last_user_msg)
            consult_crud.append_message(db, session.id, "assistant", result.get("reply", ""))
            sid = session.id
        result["session_id"] = sid
    except Exception:
        result["session_id"] = None

    return resp_success(data=result, msg="success")


# ── 历史会话列表 ──
@router.get("/sessions", summary="获取历史问诊会话列表")
def list_sessions(skip: int = 0, limit: int = 20, db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    sessions = consult_crud.get_user_sessions(db, current_user.id, skip, limit)
    data = []
    for s in sessions:
        data.append({
            "id": s.id, "title": s.title, "department": s.department,
            "message_count": s.message_count,
            "update_time": str(s.update_time)[:19] if s.update_time else ""
        })
    return resp_success(data=data)


# ── 某次会话的消息 ──
@router.get("/session/{session_id}", summary="获取某次会话的全部消息")
def get_session(session_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    msgs = consult_crud.get_session_messages(db, session_id)
    data = [{"role": m.role, "content": m.content,
             "time": str(m.create_time)[:19] if m.create_time else ""} for m in msgs]
    return resp_success(data=data)


# ── 删除会话 ──
@router.delete("/session/{session_id}", summary="删除问诊会话")
def delete_session(session_id: int, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    consult_crud.delete_session(db, session_id)
    return resp_success(msg="对话已删除")
