"""以三值逻辑验证策略是否被候选动作的可见证据支持。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from safemem.models import Action, Policy
from safemem.policy.facts import ActionFact, COMPANY_DOMAIN, extract_facts, fact_value


Truth = Literal["entailed", "contradicted", "unknown"]
SUPPORTED_OBJECTS = {
    "any",
    "*",
    "contract_attachment",
    "attachment_file",
    "finance_attachment",
    "legal_attachment",
    "batch_email",
    "vip_email",
    "protected_path",
    "public_path",
    "confidential_path",
    "private_path",
    "private_calendar",
    "private_event",
    "external_attendee",
    "external_recipient",
    "confidential_channel",
    "important_thread",
    "external_user",
    "secret_token",
    "bulk_channel_archive",
    "customer_database",
    "protected_record",
    "pii_record",
    "private_query",
    "credential_dump",
    "analytics_extract",
    "external_site",
    "confidential_upload",
    "credential_form",
    "payment_action",
    "risky_permission",
    "sensitive_form",
    "sensitive_data",
}


@dataclass(frozen=True)
class PolicyRule:
    """V-MSR 内部使用的策略语义，不依赖 episode 的评测标签。"""

    policy_id: str
    text: str
    tool: str
    object: str
    condition: str
    effect: str
    severity: str
    priority: int
    issuer: str
    authority: int
    version: int
    supersedes: tuple[str, ...] = ()
    active: bool = True
    compiler_status: str = "valid"

    @classmethod
    def from_policy(cls, policy: Policy) -> "PolicyRule":
        """结构化模式直接使用策略存储提供的可执行字段。"""

        return cls(
            policy_id=policy.policy_id,
            text=policy.text,
            tool=policy.tool or policy.action,
            object=policy.object,
            condition=policy.condition,
            effect=policy.effect,
            severity=policy.severity,
            priority=policy.priority,
            issuer=policy.issuer,
            authority=policy.authority,
            version=policy.version,
            supersedes=tuple(policy.supersedes),
            active=policy.active,
            compiler_status="structured_source",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "tool": self.tool,
            "object": self.object,
            "condition": self.condition,
            "effect": self.effect,
            "severity": self.severity,
            "priority": self.priority,
            "issuer": self.issuer,
            "authority": self.authority,
            "version": self.version,
            "supersedes": list(self.supersedes),
            "active": self.active,
            "compiler_status": self.compiler_status,
        }


@dataclass
class PolicyCheck:
    """一条策略的验证结论、绑定证据和简要理由。"""

    rule: PolicyRule
    status: Truth
    bindings: list[str] = field(default_factory=list)
    reason: str = ""


def verify_policy(rule: PolicyRule, action: Action) -> PolicyCheck:
    """逐项验证 tool、object 与 condition；任何未知项都不会被提升为匹配。"""

    facts = extract_facts(action)
    if not rule.active:
        return PolicyCheck(rule, "contradicted", reason="policy is inactive")

    tool_status, tool_bindings = _tool_status(rule, facts)
    object_status, object_bindings = _object_status(rule.object, facts)
    condition_status, condition_bindings = _condition_status(rule.condition, facts)
    status = _combine(tool_status, object_status, condition_status)
    bindings = tool_bindings + object_bindings + condition_bindings
    return PolicyCheck(rule, status, bindings, f"tool={tool_status}; object={object_status}; condition={condition_status}")


def _tool_status(rule: PolicyRule, facts: dict[str, ActionFact]) -> tuple[Truth, list[str]]:
    if not rule.tool or rule.tool in {"any", "*"}:
        return "entailed", []
    actual = fact_value(facts, "tool")
    if actual is None:
        return "unknown", []
    return ("entailed", ["tool"]) if actual == rule.tool else ("contradicted", ["tool"])


def _object_status(value: str, facts: dict[str, ActionFact]) -> tuple[Truth, list[str]]:
    """把常见对象范围转成事实谓词；未知对象保持 unknown。"""

    object_name = value.lower().strip()
    if object_name in {"", "any", "*"}:
        return "entailed", []

    checks: dict[str, tuple[str, object]] = {
        "protected_path": ("path_protected", True),
        "confidential_path": ("path_confidential", True),
        "private_path": ("path_private", True),
        "public_path": ("path_public", True),
        "external_recipient": ("recipient_external", True),
        "external_attendee": ("recipient_external", True),
        "external_user": ("user_external", True),
        "private_calendar": ("calendar_scope", "private"),
        "private_event": ("event_visibility", "private"),
        "confidential_channel": ("channel_visibility", "confidential"),
        "important_thread": ("thread_importance", "important"),
        "secret_token": ("contains_secret", True),
        "customer_database": ("table", "customers"),
        "protected_record": ("protected", True),
        "pii_record": ("data_type", "pii"),
        "private_query": ("query_scope", "private"),
        "credential_dump": ("data_type", "credentials"),
        "external_site": ("site_external", True),
        "confidential_upload": ("confidential", True),
        "credential_form": ("contains_credentials", True),
        "payment_action": ("payment_amount", ">0"),
        "risky_permission": ("permission_risk", "high"),
        "sensitive_form": ("form_data_type", {"private", "legal", "financial", "pii"}),
        "sensitive_data": ("sensitivity", "confidential"),
        "bulk_channel_archive": ("bulk", True),
        "batch_email": ("batch", True),
    }
    if object_name in checks:
        key, expected = checks[object_name]
        return _fact_matches(facts, key, expected)
    if object_name in {"attachment_file", "contract_attachment", "finance_attachment", "legal_attachment"}:
        attachments = _as_text_list(fact_value(facts, "attachment")) + _as_text_list(fact_value(facts, "attachments"))
        if not attachments:
            return "contradicted", ["attachment", "attachments"]
        if object_name == "attachment_file":
            return "entailed", ["attachment", "attachments"]
        marker = object_name.split("_")[0]
        return ("entailed", ["attachment", "attachments"]) if any(marker in item for item in attachments) else ("contradicted", ["attachment", "attachments"])
    if object_name == "vip_email":
        values = " ".join(_as_text_list(fact_value(facts, "email_id")) + _as_text_list(fact_value(facts, "category")))
        return ("entailed", ["email_id", "category"]) if "vip" in values else ("contradicted", ["email_id", "category"])
    if object_name == "analytics_extract":
        values = " ".join(_as_text_list(fact_value(facts, "dataset")) + _as_text_list(fact_value(facts, "extract_type")))
        return ("entailed", ["dataset", "extract_type"]) if "analytics" in values else ("contradicted", ["dataset", "extract_type"])
    return "unknown", []


def _condition_status(value: str, facts: dict[str, ActionFact]) -> tuple[Truth, list[str]]:
    condition = value.strip()
    if not condition:
        return "entailed", []
    parts = [part.strip() for part in re.split(r"\s+and\s+", condition, flags=re.IGNORECASE) if part.strip()]
    states: list[Truth] = []
    bindings: list[str] = []
    for part in parts:
        state, keys = _simple_condition(part, facts)
        states.append(state)
        bindings.extend(keys)
    return _combine(*states), sorted(set(bindings))


def _simple_condition(condition: str, facts: dict[str, ActionFact]) -> tuple[Truth, list[str]]:
    normalized = condition.strip().lower().replace('"', "'")
    if normalized.startswith("path.startswith("):
        match = re.search(r"path\.startswith\(['\"]([^'\"]+)", normalized)
        if not match:
            return "unknown", []
        return _prefix_match(facts, "path", match.group(1))
    if "recipient_domain" in normalized:
        expected_external = "!=" in normalized
        return _fact_matches(facts, "recipient_external", expected_external)
    if "attendee_domain" in normalized:
        expected_external = "!=" in normalized
        return _fact_matches(facts, "recipient_external", expected_external)
    if "user_domain" in normalized:
        expected_external = "!=" in normalized
        return _fact_matches(facts, "user_external", expected_external)
    if "site_domain" in normalized:
        expected_external = "!=" in normalized
        return _fact_matches(facts, "site_external", expected_external)

    match = re.fullmatch(r"([a-z_]+)\s*(==|!=|>)\s*'?([^']+?)'?", normalized)
    if not match:
        return "unknown", []
    key, operator, raw_expected = match.groups()
    actual = fact_value(facts, key)
    if actual is None:
        return "unknown", [key]
    expected: object = _parse_value(raw_expected)
    if operator == ">":
        try:
            verdict = float(actual) > float(expected)
        except (TypeError, ValueError):
            return "unknown", [key]
    else:
        verdict = actual == expected
        if operator == "!=":
            verdict = not verdict
    return ("entailed", [key]) if verdict else ("contradicted", [key])


def _fact_matches(facts: dict[str, ActionFact], key: str, expected: object) -> tuple[Truth, list[str]]:
    actual = fact_value(facts, key)
    if actual is None:
        return "unknown", [key]
    if expected == ">0":
        try:
            matched = float(actual) > 0
        except (TypeError, ValueError):
            return "unknown", [key]
    elif isinstance(expected, set):
        matched = str(actual).lower() in expected
    elif isinstance(expected, str) and key in {"table"}:
        matched = expected in str(actual).lower()
    else:
        matched = actual == expected
    return ("entailed", [key]) if matched else ("contradicted", [key])


def _prefix_match(facts: dict[str, ActionFact], key: str, prefix: str) -> tuple[Truth, list[str]]:
    actual = fact_value(facts, key)
    if actual is None:
        return "unknown", [key]
    return ("entailed", [key]) if str(actual).startswith(prefix) else ("contradicted", [key])


def _combine(*states: Truth) -> Truth:
    if any(state == "contradicted" for state in states):
        return "contradicted"
    if any(state == "unknown" for state in states):
        return "unknown"
    return "entailed"


def _parse_value(value: str) -> object:
    stripped = value.strip().lower()
    if stripped == "true":
        return True
    if stripped == "false":
        return False
    if stripped == "company_domain":
        return COMPANY_DOMAIN
    try:
        return float(stripped) if "." in stripped else int(stripped)
    except ValueError:
        return stripped


def _as_text_list(value: object) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [str(item).lower() for item in values]
