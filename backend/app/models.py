from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    conversation_id: UUID = Field(index=True)
    role: str = Field(index=True)  # user | assistant | tool
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Appointment(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    conversation_id: UUID = Field(index=True)

    patient_name: str
    patient_phone: str
    patient_email: Optional[str] = None

    start_time_iso: str
    end_time_iso: str
    timezone: str

    priority: str = Field(default="medium", index=True)  # low | medium | high
    status: str = Field(default="scheduled", index=True)  # scheduled | cancelled

    google_event_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

