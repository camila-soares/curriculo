from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.app.agent import SchedulingAgent
from backend.app.chat_store import add_message, ensure_conversation, get_history
from backend.app.config import settings
from backend.app.db import get_session, init_db
from backend.app.google_calendar import GoogleCalendarClient
from backend.app.models import Appointment


app = FastAPI(title="Agente IA - Agendamento de Exames de Vista", version="0.1.0")
WEB_ROOT = Path(__file__).resolve().parents[2]


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/")
def home():
    return FileResponse(str(WEB_ROOT / "index.html"))


@app.get("/resume.html")
def resume():
    return FileResponse(str(WEB_ROOT / "resume.html"))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="UUID")
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    appointment: dict[str, Any] | None = None


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"session_id inválido: {e}") from e


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, session: Session = Depends(get_session)) -> ChatResponse:
    conversation_id = ensure_conversation(session, _parse_uuid(req.session_id))

    add_message(session, conversation_id, "user", req.message)
    history = get_history(session, conversation_id, limit=30)

    calendar = GoogleCalendarClient()

    def on_created(appt: dict[str, Any]) -> None:
        session.add(
            Appointment(
                conversation_id=conversation_id,
                patient_name=appt["patient_name"],
                patient_phone=appt["patient_phone"],
                patient_email=appt.get("patient_email"),
                start_time_iso=appt["start_time_iso"],
                end_time_iso=appt["end_time_iso"],
                timezone=appt["timezone"],
                priority=appt["priority"],
                google_event_id=appt.get("google_event_id"),
            )
        )
        session.commit()

    agent = SchedulingAgent(calendar=calendar, on_appointment_created=on_created)

    try:
        result = agent.run(history=history)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Configuração do Google Calendar não encontrada. "
                "Verifique GOOGLE_SERVICE_ACCOUNT_FILE ou GOOGLE_OAUTH_TOKEN_FILE."
            ),
        ) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e

    add_message(session, conversation_id, "assistant", result.reply)
    return ChatResponse(
        session_id=str(conversation_id),
        reply=result.reply,
        appointment=result.appointment,
    )

