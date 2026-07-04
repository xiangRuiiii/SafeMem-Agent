from __future__ import annotations

from typing import Any


class CalendarTools:
    def __init__(self) -> None:
        self.events: dict[str, dict[str, Any]] = {}
        self.audit_log: list[dict[str, Any]] = []

    def read_calendar(self, date_range: str) -> dict[str, Any]:
        return self._record("read_calendar", {"date_range": date_range})

    def create_event(self, title: str, attendees: list[str], time: str) -> dict[str, Any]:
        event_id = f"event_{len(self.events) + 1}"
        self.events[event_id] = {"title": title, "attendees": attendees, "time": time}
        return self._record(
            "create_event",
            {"event_id": event_id, "title": title, "attendees": attendees, "time": time},
        )

    def share_calendar(self, recipient: str, date_range: str) -> dict[str, Any]:
        return self._record("share_calendar", {"recipient": recipient, "date_range": date_range})

    def update_event(self, event_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        self.events.setdefault(event_id, {}).update(changes)
        return self._record("update_event", {"event_id": event_id, "changes": changes})

    def _record(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        item = {"tool": tool, "arguments": arguments, "executed": True}
        self.audit_log.append(item)
        return item
