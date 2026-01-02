from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from openai import OpenAI

from backend.app.config import settings
from backend.app.google_calendar import GoogleCalendarClient
from backend.app.reminders import reminders_for_priority
from backend.app.scheduling import (
    compute_end,
    normalize_start_iso,
    validate_within_business_hours,
)


SYSTEM_PROMPT = """Você é um agente de atendimento (PT-BR) para agendar exames de vista.

Objetivo: conduzir a conversa, coletar dados necessários e, quando estiver tudo certo, criar o agendamento no Google Agenda.

Regras:
- Seja objetivo, educado e direto.
- Antes de criar o agendamento, CONFIRME: nome completo, telefone, data e hora, timezone (assuma {tz}), e prioridade (low/medium/high; default: medium).
- Se o cliente não informar email, o agendamento ainda pode ser criado (sem convite por email).
- Duração padrão do exame: {duration} minutos.
- Horário de atendimento: {start}–{end} (horário local).
- Se houver conflito no calendário, ofereça 2 alternativas próximas.
- Quando tiver os dados mínimos, chame a ferramenta create_exam_appointment.

Campos mínimos para criar:
- patient_name
- patient_phone
- start_time_iso (ISO 8601)
- timezone
- priority

Responda sempre em PT-BR.
""".strip()


@dataclass
class AgentResult:
    reply: str
    appointment: dict[str, Any] | None = None


def _tools_schema() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "check_availability",
            "description": "Checa se há conflito de agenda em um intervalo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time_iso": {"type": "string", "description": "ISO 8601"},
                    "end_time_iso": {"type": "string", "description": "ISO 8601"},
                },
                "required": ["start_time_iso", "end_time_iso"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "create_exam_appointment",
            "description": "Cria um agendamento de exame de vista no Google Agenda e retorna a confirmação.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "patient_phone": {"type": "string"},
                    "patient_email": {"type": "string"},
                    "start_time_iso": {"type": "string", "description": "ISO 8601"},
                    "timezone": {"type": "string", "description": "Ex.: America/Recife"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "notes": {"type": "string"},
                },
                "required": ["patient_name", "patient_phone", "start_time_iso", "timezone", "priority"],
                "additionalProperties": False,
            },
        },
    ]


class SchedulingAgent:
    def __init__(
        self,
        calendar: GoogleCalendarClient,
        on_appointment_created: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY não configurada.")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._calendar = calendar
        self._on_appointment_created = on_appointment_created

    def run(self, history: list[dict[str, str]]) -> AgentResult:
        """
        history: list of {"role": "user"|"assistant", "content": "..."} including the last user message.
        """
        sys = SYSTEM_PROMPT.format(
            tz=settings.business_timezone,
            duration=settings.exam_duration_min,
            start=settings.business_hours_start,
            end=settings.business_hours_end,
        )
        input_messages = [{"role": "system", "content": sys}, *history]

        tools = _tools_schema()
        resp = self._client.responses.create(
            model=settings.openai_model,
            input=input_messages,
            tools=tools,
            tool_choice="auto",
        )

        appointment: dict[str, Any] | None = None
        max_loops = 6
        loops = 0

        while loops < max_loops:
            loops += 1
            tool_calls = [o for o in (resp.output or []) if getattr(o, "type", None) == "function_call"]
            if not tool_calls:
                break

            tool_outputs: list[dict[str, Any]] = []
            for call in tool_calls:
                name = call.name
                args = json.loads(call.arguments or "{}")

                if name == "check_availability":
                    conflict = self._calendar.check_conflict(
                        start_iso=args["start_time_iso"],
                        end_iso=args["end_time_iso"],
                    )
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": json.dumps({"conflict": conflict}),
                        }
                    )
                    continue

                if name == "create_exam_appointment":
                    tz = args["timezone"]
                    start_dt = normalize_start_iso(args["start_time_iso"], tz)
                    end_dt = compute_end(start_dt, settings.exam_duration_min)
                    validate_within_business_hours(start_dt, end_dt)

                    conflict = self._calendar.check_conflict(
                        start_iso=start_dt.isoformat(),
                        end_iso=end_dt.isoformat(),
                    )
                    if conflict:
                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": call.call_id,
                                "output": json.dumps(
                                    {
                                        "ok": False,
                                        "error": "Horário indisponível (conflito na agenda).",
                                    }
                                ),
                            }
                        )
                        continue

                    description_lines = [
                        "Agendamento de exame de vista (IA).",
                        f"Paciente: {args['patient_name']}",
                        f"Telefone: {args['patient_phone']}",
                        f"Prioridade: {args['priority']}",
                    ]
                    if args.get("patient_email"):
                        description_lines.append(f"Email: {args['patient_email']}")
                    if args.get("notes"):
                        description_lines.append("")
                        description_lines.append(f"Observações: {args['notes']}")

                    event = self._calendar.create_event(
                        summary="Exame de vista",
                        description="\n".join(description_lines),
                        start_iso=start_dt.isoformat(),
                        end_iso=end_dt.isoformat(),
                        timezone=tz,
                        priority=args["priority"],
                        attendee_email=args.get("patient_email") or None,
                        reminders=reminders_for_priority(args["priority"]),
                    )

                    appointment = {
                        "patient_name": args["patient_name"],
                        "patient_phone": args["patient_phone"],
                        "patient_email": args.get("patient_email"),
                        "start_time_iso": start_dt.isoformat(),
                        "end_time_iso": end_dt.isoformat(),
                        "timezone": tz,
                        "priority": args["priority"],
                        "google_event_id": event.get("id"),
                        "google_event_html_link": event.get("htmlLink"),
                    }
                    if self._on_appointment_created:
                        self._on_appointment_created(appointment)

                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": json.dumps({"ok": True, "appointment": appointment}),
                        }
                    )
                    continue

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps({"ok": False, "error": f"Ferramenta desconhecida: {name}"}),
                    }
                )

            resp = self._client.responses.create(
                model=settings.openai_model,
                previous_response_id=resp.id,
                input=tool_outputs,
                tools=tools,
                tool_choice="auto",
            )

        return AgentResult(reply=(resp.output_text or "").strip(), appointment=appointment)

