"""从候选工具动作提取可核验事实，供 V-MSR 绑定策略条件。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from safemem.models import Action


COMPANY_DOMAIN = "company.com"


@dataclass(frozen=True)
class ActionFact:
    """动作中一个可追溯的原子事实。"""

    name: str
    value: Any
    evidence: str


def extract_facts(action: Action) -> dict[str, ActionFact]:
    """保留原始参数，并补充外部目标、路径和敏感属性等派生事实。"""

    facts = {"tool": ActionFact("tool", action.tool, "tool")}
    for key, value in action.arguments.items():
        facts[key] = ActionFact(key, value, f"arguments.{key}")

    target_external_values: list[bool] = []
    recipients = _targets(action.arguments)
    if recipients:
        external = any(_is_external(item) for item in recipients)
        target_external_values.append(external)
        facts["recipient_external"] = ActionFact("recipient_external", external, "arguments.recipient/to/attendees")
        facts["recipient_domain"] = ActionFact(
            "recipient_domain",
            "external" if external else COMPANY_DOMAIN,
            "arguments.recipient/to/attendees",
        )

    user_email = action.arguments.get("user_email")
    if user_email:
        external = _is_external(user_email)
        target_external_values.append(external)
        facts["user_external"] = ActionFact("user_external", external, "arguments.user_email")
        facts["user_domain"] = ActionFact(
            "user_domain", "external" if external else COMPANY_DOMAIN, "arguments.user_email"
        )

    site = str(action.arguments.get("site_domain", "")).lower()
    if site:
        external = site != COMPANY_DOMAIN
        target_external_values.append(external)
        facts["site_external"] = ActionFact("site_external", external, "arguments.site_domain")

    if target_external_values:
        # Text 模式统一使用该事实，不再区分 recipient/user/site 等易混淆对象标签。
        facts["target_external"] = ActionFact(
            "target_external",
            any(target_external_values),
            "arguments.recipient/to/attendees/user_email/site_domain",
        )

    path = str(action.arguments.get("path", action.arguments.get("file_path", ""))).lower()
    if path:
        facts["path"] = ActionFact("path", path, "arguments.path/file_path")
        facts["path_private"] = ActionFact("path_private", path.startswith("/private"), "arguments.path/file_path")
        facts["path_confidential"] = ActionFact(
            "path_confidential",
            path.startswith("/confidential") or any(word in path for word in ("finance", "roadmap", "staff")),
            "arguments.path/file_path",
        )
        facts["path_protected"] = ActionFact("path_protected", path.startswith("/protected"), "arguments.path/file_path")
        facts["path_public"] = ActionFact("path_public", path.startswith("/public"), "arguments.path/file_path")
        scope = _path_scope(path)
        if scope:
            facts["path_scope"] = ActionFact("path_scope", scope, "arguments.path/file_path")

    sensitivity = _data_sensitivity(action.arguments, facts)
    if sensitivity:
        facts["data_sensitivity"] = ActionFact(
            "data_sensitivity",
            sensitivity,
            "arguments.sensitivity/file_sensitivity/confidential/path",
        )

    attachments = _attachment_values(action.arguments)
    if "attachment" in action.arguments or "attachments" in action.arguments:
        facts["has_attachment"] = ActionFact(
            "has_attachment", bool(attachments), "arguments.attachment/attachments"
        )
    attachment_kind = _attachment_kind(attachments)
    if attachment_kind:
        facts["attachment_kind"] = ActionFact(
            "attachment_kind", attachment_kind, "arguments.attachment/attachments"
        )

    if "batch" in action.arguments or "bulk" in action.arguments:
        facts["operation_bulk"] = ActionFact(
            "operation_bulk",
            bool(action.arguments.get("batch") or action.arguments.get("bulk")),
            "arguments.batch/bulk",
        )
    return facts


def fact_value(facts: dict[str, ActionFact], name: str) -> Any | None:
    """返回事实值；没有证据时保持 None，而不是猜测为真。"""

    item = facts.get(name)
    return item.value if item else None


def _targets(arguments: dict[str, Any]) -> list[Any]:
    values: list[Any] = []
    for key in ("to", "recipient", "recipients", "destination", "share_to", "attendees"):
        value = arguments.get(key)
        if value is None:
            continue
        values.extend(value if isinstance(value, list) else [value])
    return values


def _is_external(value: Any) -> bool:
    text = str(value).lower()
    return "@" in text and not text.endswith("@" + COMPANY_DOMAIN)


def _path_scope(path: str) -> str:
    for scope in ("protected", "private", "confidential", "public"):
        if path.startswith(f"/{scope}"):
            return scope
    return ""


def _data_sensitivity(arguments: dict[str, Any], facts: dict[str, ActionFact]) -> str:
    value = arguments.get("sensitivity", arguments.get("file_sensitivity", ""))
    if value:
        return str(value).lower()
    if arguments.get("confidential") is True:
        return "confidential"
    if fact_value(facts, "path_confidential") is True:
        return "confidential"
    return ""


def _attachment_values(arguments: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    for key in ("attachment", "attachments"):
        value = arguments.get(key)
        if value is None:
            continue
        values.extend(value if isinstance(value, list) else [value])
    return [str(item).lower() for item in values]


def _attachment_kind(attachments: list[str]) -> str:
    for kind in ("contract", "finance", "legal"):
        if any(kind in item for item in attachments):
            return kind
    return "generic" if attachments else ""
