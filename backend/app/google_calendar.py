from __future__ import annotations

from datetime import datetime
from typing import Any

from dateutil import parser as dtparser
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from backend.app.config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    def __init__(self) -> None:
        self._service = None

    def _build_service(self):
        if settings.google_service_account_file:
            creds = ServiceAccountCredentials.from_service_account_file(
                settings.google_service_account_file,
                scopes=SCOPES,
            )
            if settings.google_workspace_subject_email:
                creds = creds.with_subject(settings.google_workspace_subject_email)
            return build("calendar", "v3", credentials=creds, cache_discovery=False)

        creds = OAuthCredentials.from_authorized_user_file(
            settings.google_oauth_token_file, SCOPES
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(settings.google_oauth_token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    @property
    def service(self):
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def check_conflict(self, start_iso: str, end_iso: str) -> bool:
        """
        Returns True if there is a conflict (busy) in the interval.
        """
        start = dtparser.isoparse(start_iso)
        end = dtparser.isoparse(end_iso)

        body = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "items": [{"id": settings.google_calendar_id}],
        }
        fb = self.service.freebusy().query(body=body).execute()
        busy = fb.get("calendars", {}).get(settings.google_calendar_id, {}).get("busy", [])
        return len(busy) > 0

    def create_event(
        self,
        summary: str,
        description: str,
        start_iso: str,
        end_iso: str,
        timezone: str,
        priority: str,
        attendee_email: str | None = None,
        reminders: list[dict] | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_iso, "timeZone": timezone},
            "end": {"dateTime": end_iso, "timeZone": timezone},
        }
        if attendee_email:
            event["attendees"] = [{"email": attendee_email}]
        if reminders is not None:
            event["reminders"] = {"useDefault": False, "overrides": reminders}

        created = (
            self.service.events()
            .insert(
                calendarId=settings.google_calendar_id,
                body=event,
                sendUpdates="all" if attendee_email else "none",
            )
            .execute()
        )
        return created

