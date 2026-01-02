from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateutil import parser as dtparser

from backend.app.config import settings


@dataclass(frozen=True)
class BusinessHours:
    start: time
    end: time


def _parse_hhmm(value: str) -> time:
    hh, mm = value.strip().split(":")
    return time(hour=int(hh), minute=int(mm))


def business_hours() -> BusinessHours:
    return BusinessHours(
        start=_parse_hhmm(settings.business_hours_start),
        end=_parse_hhmm(settings.business_hours_end),
    )


def normalize_start_iso(start_time_iso: str, timezone: str) -> datetime:
    """
    Parses ISO datetime and ensures it's timezone-aware in provided timezone.
    """
    tz = ZoneInfo(timezone)
    dt = dtparser.isoparse(start_time_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def compute_end(start: datetime, duration_min: int) -> datetime:
    return start + timedelta(minutes=duration_min)


def validate_within_business_hours(start: datetime, end: datetime) -> None:
    bh = business_hours()
    if start.date() != end.date():
        raise ValueError("Agendamento deve começar e terminar no mesmo dia.")
    start_t = start.time().replace(tzinfo=None)
    end_t = end.time().replace(tzinfo=None)
    if not (bh.start <= start_t and end_t <= bh.end):
        raise ValueError(
            f"Horário fora do atendimento ({settings.business_hours_start}–{settings.business_hours_end})."
        )

