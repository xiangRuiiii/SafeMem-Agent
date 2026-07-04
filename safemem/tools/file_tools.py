from __future__ import annotations

from typing import Any


class FileTools:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.audit_log: list[dict[str, Any]] = []

    def read_file(self, path: str) -> dict[str, Any]:
        return self._record("read_file", {"path": path, "content": self.files.get(path, "")})

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        self.files[path] = content
        return self._record("write_file", {"path": path, "content": content})

    def delete_file(self, path: str) -> dict[str, Any]:
        self.files.pop(path, None)
        return self._record("delete_file", {"path": path})

    def share_file(self, path: str, recipient: str) -> dict[str, Any]:
        return self._record("share_file", {"path": path, "recipient": recipient})

    def _record(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        item = {"tool": tool, "arguments": arguments, "executed": True}
        self.audit_log.append(item)
        return item
