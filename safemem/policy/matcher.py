from __future__ import annotations

from typing import Any

from safemem.models import Action, Policy

COMPANY_DOMAIN = "company.com"

SEVERITY_SCORE = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def tool_matches(policy: Policy, action: Action) -> bool:
    policy_tool = policy.tool or policy.action
    return not policy_tool or policy_tool == action.tool


def object_matches(policy: Policy, action: Action) -> bool:
    target = policy.object.lower()
    args = action.arguments
    if target in {"", "any", "*"}:
        return True
    if target == "contract_attachment":
        return _contains(args.get("attachment"), "contract") or _contains(args.get("attachments"), "contract")
    if target == "attachment_file":
        return bool(args.get("attachment") or args.get("attachments"))
    if target == "finance_attachment":
        return _contains(args.get("attachment"), "finance") or _contains(args.get("attachments"), "finance")
    if target == "legal_attachment":
        return _contains(args.get("attachment"), "legal") or _contains(args.get("attachments"), "legal")
    if target == "batch_email":
        return bool(args.get("batch")) or len(_as_list(args.get("email_ids"))) > 1
    if target == "vip_email":
        return _contains(args.get("email_id"), "vip") or _contains(args.get("category"), "vip")
    if target == "protected_path":
        return str(args.get("path", "")).startswith("/protected")
    if target == "public_path":
        return str(args.get("path", "")).startswith("/public")
    if target == "confidential_path":
        path = str(args.get("path", "")).lower()
        return path.startswith("/confidential") or "finance" in path or "roadmap" in path or "staff" in path
    if target == "private_path":
        return str(args.get("path", "")).startswith("/private")
    if target == "private_calendar":
        return str(args.get("calendar_scope", "")).lower() == "private"
    if target == "private_event":
        return str(args.get("event_visibility", "")).lower() == "private"
    if target == "external_attendee":
        return any(_is_external(value) for value in _as_list(args.get("attendees")))
    if target == "external_recipient":
        return action_has_external_target(action)
    return target in " ".join(str(value).lower() for value in args.values())


def condition_matches(policy: Policy, action: Action) -> bool:
    condition = policy.condition.lower().strip()
    if not condition:
        return True
    if "recipient_domain == company_domain" in condition:
        return not action_has_external_target(action)
    if "recipient_domain != company_domain" in condition:
        return action_has_external_target(action)
    if "attendee_domain == company_domain" in condition:
        return not any(_is_external(value) for value in _as_list(action.arguments.get("attendees")))
    if "attendee_domain != company_domain" in condition:
        return any(_is_external(value) for value in _as_list(action.arguments.get("attendees")))
    if "path.startswith('/protected')" in condition:
        return str(action.arguments.get("path", "")).startswith("/protected")
    if "path.startswith('/confidential')" in condition:
        return str(action.arguments.get("path", "")).startswith("/confidential")
    if "path.startswith('/private')" in condition:
        return str(action.arguments.get("path", "")).startswith("/private")
    if "path.startswith('/public')" in condition:
        return str(action.arguments.get("path", "")).startswith("/public")
    if "email_category" in condition and "vip" in condition:
        return object_matches(Policy(policy_id="_", text="", object="vip_email"), action)
    if "batch" in condition:
        return object_matches(Policy(policy_id="_", text="", object="batch_email"), action)
    if "attachment" in condition and "finance" in condition:
        return object_matches(Policy(policy_id="_", text="", object="finance_attachment"), action)
    if "calendar_scope" in condition and "private" in condition:
        return str(action.arguments.get("calendar_scope", "")).lower() == "private"
    if "event_visibility" in condition and "private" in condition:
        return str(action.arguments.get("event_visibility", "")).lower() == "private"
    return True


def policy_applies(policy: Policy, action: Action) -> bool:
    return tool_matches(policy, action) and object_matches(policy, action) and condition_matches(policy, action)


def action_has_external_target(action: Action) -> bool:
    args = action.arguments
    targets: list[Any] = []
    for key in ("to", "recipient", "recipients"):
        targets.extend(_as_list(args.get(key)))
    targets.extend(_as_list(args.get("attendees")))
    return any(_is_external(value) for value in targets)


def severity_value(policy: Policy) -> int:
    return SEVERITY_SCORE.get(policy.severity.lower(), 1)


def _is_external(value: Any) -> bool:
    text = str(value).lower()
    return "@" in text and not text.endswith("@" + COMPANY_DOMAIN)


def _contains(value: Any, needle: str) -> bool:
    needle = needle.lower()
    return any(needle in str(item).lower() for item in _as_list(value))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
