from __future__ import annotations


def reminders_for_priority(priority: str) -> list[dict]:
    """
    Returns Google Calendar reminder overrides (minutes before).
    https://developers.google.com/calendar/api/v3/reference/events
    """
    p = (priority or "medium").lower().strip()

    if p == "high":
        return [
            {"method": "email", "minutes": 24 * 60},
            {"method": "popup", "minutes": 24 * 60},
            {"method": "popup", "minutes": 2 * 60},
        ]
    if p == "low":
        return [{"method": "popup", "minutes": 2 * 60}]

    # medium (default)
    return [
        {"method": "email", "minutes": 24 * 60},
        {"method": "popup", "minutes": 24 * 60},
    ]

