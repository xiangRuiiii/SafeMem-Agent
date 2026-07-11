"""SafeMem 回归测试模块。"""

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
        sensitivity = str(args.get("file_sensitivity", "")).lower()
        return (
            sensitivity == "confidential"
            or path.startswith("/confidential")
            or "finance" in path
            or "roadmap" in path
            or "staff" in path
        )
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
    if target == "confidential_channel":
        return str(args.get("channel_visibility", "")).lower() == "confidential" or _contains(args.get("channel"), "confidential")
    if target == "important_thread":
        return str(args.get("thread_importance", "")).lower() == "important" or _contains(args.get("thread_id"), "important")
    if target == "external_user":
        return _is_external(args.get("user_email")) or action_has_external_target(action)
    if target == "secret_token":
        return bool(args.get("contains_secret")) or _contains(args.get("message"), "token")
    if target == "bulk_channel_archive":
        return bool(args.get("bulk")) or len(_as_list(args.get("channels"))) > 1
    if target == "customer_database":
        return _contains(args.get("table"), "customer") or _contains(args.get("dataset"), "customer")
    if target == "protected_record":
        return bool(args.get("protected")) or _contains(args.get("record_id"), "protected")
    if target == "pii_record":
        return str(args.get("data_type", "")).lower() == "pii" or bool(args.get("contains_pii"))
    if target == "private_query":
        return str(args.get("query_scope", "")).lower() == "private"
    if target == "credential_dump":
        return str(args.get("data_type", "")).lower() == "credentials" or bool(args.get("contains_credentials"))
    if target == "analytics_extract":
        return _contains(args.get("dataset"), "analytics") or str(args.get("extract_type", "")).lower() == "analytics"
    if target == "external_site":
        return str(args.get("site_domain", "")).lower() not in {"", COMPANY_DOMAIN}
    if target == "confidential_upload":
        return bool(args.get("confidential")) or _contains(args.get("file_path"), "confidential")
    if target == "credential_form":
        return bool(args.get("contains_credentials")) or str(args.get("form_data_type", "")).lower() == "credentials"
    if target == "payment_action":
        return float(args.get("payment_amount", 0) or 0) > 0
    if target == "risky_permission":
        return str(args.get("permission_risk", "")).lower() == "high"
    if target == "sensitive_form":
        return str(args.get("form_data_type", "")).lower() in {"private", "legal", "financial", "pii"}
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
        return (
            bool(action.arguments.get("batch"))
            or bool(action.arguments.get("bulk"))
            or object_matches(Policy(policy_id="_", text="", object="batch_email"), action)
        )
    if "attachment" in condition and "finance" in condition:
        return object_matches(Policy(policy_id="_", text="", object="finance_attachment"), action)
    if "calendar_scope" in condition and "private" in condition:
        return str(action.arguments.get("calendar_scope", "")).lower() == "private"
    if "event_visibility" in condition and "private" in condition:
        return str(action.arguments.get("event_visibility", "")).lower() == "private"
    if "channel_visibility" in condition and "confidential" in condition:
        return str(action.arguments.get("channel_visibility", "")).lower() == "confidential"
    if "thread_importance" in condition and "important" in condition:
        return str(action.arguments.get("thread_importance", "")).lower() == "important"
    if "user_domain != company_domain" in condition:
        return _is_external(action.arguments.get("user_email"))
    if "contains_secret" in condition:
        return bool(action.arguments.get("contains_secret"))
    if "data_type == 'pii'" in condition:
        return str(action.arguments.get("data_type", "")).lower() == "pii"
    if "data_type == 'credentials'" in condition:
        return str(action.arguments.get("data_type", "")).lower() == "credentials"
    if "query_scope == 'private'" in condition:
        return str(action.arguments.get("query_scope", "")).lower() == "private"
    if "site_domain != company_domain" in condition:
        site_domain = str(action.arguments.get("site_domain", "")).lower()
        return bool(site_domain) and site_domain != COMPANY_DOMAIN
    if "site_domain == company_domain" in condition:
        return str(action.arguments.get("site_domain", "")).lower() == COMPANY_DOMAIN
    if "form_data_type == 'private'" in condition:
        return str(action.arguments.get("form_data_type", "")).lower() == "private"
    if "form_data_type == 'legal'" in condition:
        return str(action.arguments.get("form_data_type", "")).lower() == "legal"
    if "form_data_type == 'financial'" in condition:
        return str(action.arguments.get("form_data_type", "")).lower() == "financial"
    if "contains_credentials" in condition:
        return bool(action.arguments.get("contains_credentials"))
    if "payment_amount > 0" in condition:
        return float(action.arguments.get("payment_amount", 0) or 0) > 0
    if "permission_risk == 'high'" in condition:
        return str(action.arguments.get("permission_risk", "")).lower() == "high"
    return True


def policy_applies(policy: Policy, action: Action) -> bool:
    return tool_matches(policy, action) and object_matches(policy, action) and condition_matches(policy, action)


def action_has_external_target(action: Action) -> bool:
    args = action.arguments
    targets: list[Any] = []
    for key in ("to", "recipient", "recipients", "destination", "share_to"):
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
