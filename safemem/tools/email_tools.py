from __future__ import annotations

from typing import Any


class EmailTools:
    def __init__(self) -> None:
        self.audit_log: list[dict[str, Any]] = []

    def read_email(self, email_id: str) -> dict[str, Any]:
        return self._record("read_email", {"email_id": email_id}, executed=True)

    def search_email(self, query: str) -> dict[str, Any]:
        return self._record("search_email", {"query": query}, executed=True)

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[str] | None = None,
    ) -> dict[str, Any]:
        args = {
            "to": to,
            "subject": subject,
            "body": body,
            "attachments": attachments or [],
        }
        return self._record("send_email", args, executed=True)

    def archive_email(self, email_id: str) -> dict[str, Any]:
        return self._record("archive_email", {"email_id": email_id}, executed=True)

    def delete_email(self, email_id: str) -> dict[str, Any]:
        return self._record("delete_email", {"email_id": email_id}, executed=True)

    def _record(self, tool: str, arguments: dict[str, Any], executed: bool) -> dict[str, Any]:
        item = {"tool": tool, "arguments": arguments, "executed": executed}
        self.audit_log.append(item)
        return item
