from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import UUID, uuid4

from sqlmodel import Session, select

from backend.app.models import Conversation, Message


def ensure_conversation(session: Session, conversation_id: UUID | None) -> UUID:
    if conversation_id is None:
        conv = Conversation(id=uuid4())
        session.add(conv)
        session.commit()
        return conv.id

    conv = session.get(Conversation, conversation_id)
    if conv is None:
        conv = Conversation(id=conversation_id)
        session.add(conv)
        session.commit()
    return conv.id


def add_message(session: Session, conversation_id: UUID, role: str, content: str) -> None:
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(msg)
    conv = session.get(Conversation, conversation_id)
    if conv:
        conv.updated_at = datetime.utcnow()
        session.add(conv)
    session.commit()


def get_history(session: Session, conversation_id: UUID, limit: int = 30) -> list[dict[str, str]]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    msgs: Sequence[Message] = session.exec(stmt).all()
    msgs = msgs[-limit:]
    history: list[dict[str, str]] = []
    for m in msgs:
        if m.role not in ("user", "assistant"):
            continue
        history.append({"role": m.role, "content": m.content})
    return history

