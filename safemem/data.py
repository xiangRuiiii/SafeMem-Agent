from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from safemem.models import Episode


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_episodes(path: str | Path) -> list[Episode]:
    return [Episode.from_dict(row) for row in read_jsonl(path)]


def write_json(path: str | Path, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys())
    with target.open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(headers) + "\n")
        for row in rows:
            values = [str(row.get(header, "")).replace(",", ";") for header in headers]
            handle.write(",".join(values) + "\n")
