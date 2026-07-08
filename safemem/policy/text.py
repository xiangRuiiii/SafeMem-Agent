from __future__ import annotations

import re
from typing import Any

from safemem.models import Action, Policy
from safemem.policy.matcher import action_has_external_target


TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]")


def build_action_query(action: Action) -> str:
    args = action.arguments
    parts = [
        action.tool,
        args.get("path", ""),
        args.get("recipient", ""),
        args.get("to", ""),
        args.get("attachment", ""),
        args.get("attachments", ""),
        args.get("file_sensitivity", ""),
        args.get("event_visibility", ""),
        args.get("calendar_scope", ""),
        args.get("calendar_id", ""),
        args.get("email_id", ""),
        args.get("category", ""),
        args.get("batch", ""),
    ]
    parts.extend(_list_values(args.get("recipients")))
    parts.extend(_list_values(args.get("attendees")))
    parts.extend(action_hints(action))
    return " ".join(str(part) for part in flatten_values(parts) if part not in {"", None, False})


def build_policy_doc(policy: Policy) -> str:
    return " ".join(
        str(part)
        for part in [
            policy.policy_id,
            policy.scope,
            policy.tool,
            policy.action,
            policy.object,
            policy.condition,
            policy.effect,
            policy.severity,
            policy.priority,
            policy.text,
        ]
        if part not in {"", None}
    )


def build_action_embedding_text(action: Action) -> str:
    args = action.arguments
    hints = " ".join(action_hints(action))
    return (
        f"Tool: {action.tool}. "
        f"Action arguments: {args}. "
        f"Action hints: {hints}. "
        "The agent is about to execute this tool action."
    )


def build_policy_embedding_text(policy: Policy) -> str:
    return (
        f"Scope: {policy.scope}. "
        f"Tool: {policy.tool}. "
        f"Action: {policy.action}. "
        f"Object: {policy.object}. "
        f"Condition: {policy.condition}. "
        f"Effect: {policy.effect}. "
        f"Severity: {policy.severity}. "
        f"Priority: {policy.priority}. "
        f"Policy text: {policy.text}"
    )


def action_hints(action: Action) -> list[str]:
    args = action.arguments
    hints = [action.tool]
    path = str(args.get("path", "")).lower()
    if path.startswith("/private"):
        hints.extend(["private_path", "private_file"])
    if path.startswith("/confidential"):
        hints.extend(["confidential_path", "confidential_file"])
    if path.startswith("/protected"):
        hints.extend(["protected_path", "protected_file"])
    if path.startswith("/public"):
        hints.extend(["public_path", "public_file"])
    if "roadmap" in path:
        hints.append("roadmap")
    if "finance" in path:
        hints.append("finance")
    if "staff" in path:
        hints.append("staff")

    sensitivity = str(args.get("file_sensitivity", "")).lower()
    if sensitivity:
        hints.extend([sensitivity, f"{sensitivity}_file"])
    if action_has_external_target(action):
        hints.extend(["external_recipient", "external_target", "recipient_domain_not_company"])
    elif _has_any_target(args):
        hints.extend(["internal_recipient", "company_domain"])
    if args.get("attachment") or args.get("attachments"):
        hints.append("attachment_file")
    if args.get("batch"):
        hints.append("batch_email")
    visibility = str(args.get("event_visibility", "")).lower()
    if visibility:
        hints.extend([visibility, f"{visibility}_event"])
    scope = str(args.get("calendar_scope", "")).lower()
    if scope:
        hints.extend([scope, f"{scope}_calendar"])
    return hints


def tokenize(text: str) -> list[str]:
    expanded = text.replace("_", " ").replace("/", " ").replace(".", " ").replace("@", " ")
    tokens = [token.lower() for token in TOKEN_RE.findall(expanded)]
    return [token for token in tokens if token]


def _has_any_target(args: dict[str, Any]) -> bool:
    for key in ("to", "recipient", "recipients", "attendees"):
        if args.get(key):
            return True
    return False


def _list_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def flatten_values(values: list[Any]) -> list[Any]:
    flattened: list[Any] = []
    for value in values:
        if isinstance(value, list):
            flattened.extend(flatten_values(value))
        else:
            flattened.append(value)
    return flattened
