"""将自然语言策略一次性编译为 V-MSR 可验证 manifest，并按哈希缓存。"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

from safemem.llm_client import ChatClient
from safemem.models import Policy
from safemem.policy.verify import PolicyRule, SUPPORTED_OBJECTS


PROMPT_VERSION = "vmsr-text-v3"
VALID_EFFECTS = {"allow", "block", "ask_confirmation", "revise"}
ALLOWED_TOOLS = {
    "send_email", "archive_email", "delete_email", "share_file", "delete_file", "write_file", "read_file",
    "share_calendar", "create_event", "update_event", "share_message", "delete_thread", "invite_user",
    "post_message", "archive_channel", "search_messages", "reply_thread", "export_database", "delete_record",
    "update_record", "run_query", "dump_table", "share_extract", "read_schema", "submit_form", "upload_file",
    "enter_credentials", "approve_payment", "accept_permission", "open_page", "download_file", "search_site", "search_web",
}
CONDITION_FIELDS = {
    "recipient_domain", "attendee_domain", "user_domain", "site_domain", "path", "recipient", "to", "attendees",
    "attachment", "attachments", "file_sensitivity", "sensitivity", "event_visibility", "calendar_scope", "email_id",
    "category", "batch", "bulk", "channel_visibility", "thread_importance", "contains_secret", "table", "dataset",
    "record_id", "data_type", "query_scope", "file_path", "permission_risk", "protected", "contains_pii",
    "contains_credentials", "form_data_type", "confidential", "payment_amount", "target_external",
    "data_sensitivity", "path_scope", "attachment_kind", "has_attachment", "operation_bulk",
}
PREDICATE_SPECS: dict[str, dict[str, object]] = {
    "target_external": {
        "type": "boolean",
        "operators": ["==", "!="],
        "description": "True for any recipient, attendee, invited user, or website outside company.com.",
    },
    "data_sensitivity": {
        "type": "enum",
        "values": ["confidential", "private", "public", "non_sensitive"],
        "operators": ["==", "!="],
        "description": "Normalized sensitivity of the data involved in the action.",
    },
    "path_scope": {
        "type": "enum",
        "values": ["protected", "private", "confidential", "public"],
        "operators": ["==", "!="],
        "description": "Normalized leading directory scope for a file path.",
    },
    "attachment_kind": {
        "type": "enum",
        "values": ["contract", "finance", "legal", "generic"],
        "operators": ["==", "!="],
        "description": "Semantic kind inferred from attachment names.",
    },
    "has_attachment": {"type": "boolean", "operators": ["==", "!="], "description": "Whether an attachment exists."},
    "operation_bulk": {"type": "boolean", "operators": ["==", "!="], "description": "Whether the operation is batch or bulk."},
    "category": {"type": "string", "operators": ["==", "!="], "description": "Email or record category, for example vip."},
    "event_visibility": {"type": "string", "operators": ["==", "!="], "description": "Calendar event visibility."},
    "calendar_scope": {"type": "string", "operators": ["==", "!="], "description": "Calendar sharing scope."},
    "channel_visibility": {"type": "string", "operators": ["==", "!="], "description": "Slack channel visibility."},
    "thread_importance": {"type": "string", "operators": ["==", "!="], "description": "Slack thread importance."},
    "contains_secret": {"type": "boolean", "operators": ["==", "!="], "description": "Whether message text contains a secret."},
    "protected": {"type": "boolean", "operators": ["==", "!="], "description": "Whether a database record is protected."},
    "data_type": {"type": "string", "operators": ["==", "!="], "description": "Database data type such as pii or credentials."},
    "query_scope": {"type": "string", "operators": ["==", "!="], "description": "Database query scope."},
    "contains_credentials": {"type": "boolean", "operators": ["==", "!="], "description": "Whether a form or action contains credentials."},
    "form_data_type": {"type": "string", "operators": ["==", "!="], "description": "Browser form data type."},
    "permission_risk": {"type": "string", "operators": ["==", "!="], "description": "Permission risk level."},
    "payment_amount": {"type": "number", "operators": ["==", "!=", ">"], "description": "Payment amount."},
}
EFFECT_ALIASES = {
    "allow": "allow",
    "allow_execute": "allow",
    "execute": "allow",
    "block": "block",
    "deny": "block",
    "reject": "block",
    "ask_confirmation": "ask_confirmation",
    "ask-confirmation": "ask_confirmation",
    "confirm": "ask_confirmation",
    "confirmation": "ask_confirmation",
    "ask": "ask_confirmation",
    "warn": "ask_confirmation",
    "warning": "ask_confirmation",
    "caution": "ask_confirmation",
    "review": "ask_confirmation",
    "escalate": "ask_confirmation",
    "revise": "revise",
    "modify": "revise",
}


class MissingManifestError(RuntimeError):
    """Text 模式缺少预编译策略时给出明确错误，禁止评估时隐式调 API。"""


@dataclass(frozen=True)
class PolicyManifest:
    """缓存中一条由策略文本推导出的结构化语义。"""

    cache_key: str
    model: str
    rule: PolicyRule

    def to_dict(self) -> dict[str, object]:
        return {"cache_key": self.cache_key, "model": self.model, "prompt_version": PROMPT_VERSION, "rule": self.rule.to_dict()}


class ManifestStore:
    """读取和写入可复现实验使用的策略 manifest JSONL。"""

    def __init__(self, path: str | Path, model: str = "") -> None:
        self.path = Path(path)
        self.model = model
        self._items: dict[str, PolicyManifest] = {}
        if self.path.exists():
            self._load()

    def rule_for(self, policy: Policy) -> PolicyRule:
        key = manifest_key(policy, self.model)
        manifest = self._items.get(key)
        if manifest is None:
            raise MissingManifestError(
                f"Missing V-MSR text manifest for policy text hash {key[:12]}. "
                "Run experiments/build_policy_cache.py before text evaluation."
            )
        # 语义缓存不把 policy_id 放入哈希；取回后必须绑定当前记录，避免证书引用首次编译的同文策略。
        return replace(
            manifest.rule,
            policy_id=policy.policy_id,
            text=policy.text,
            priority=policy.priority,
        )

    def add(self, policy: Policy, model: str, rule: PolicyRule) -> PolicyManifest:
        key = manifest_key(policy, model)
        manifest = PolicyManifest(cache_key=key, model=model, rule=rule)
        self._items[key] = manifest
        return manifest

    def has(self, policy: Policy, model: str) -> bool:
        return manifest_key(policy, model) in self._items

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rows = [self._items[key].to_dict() for key in sorted(self._items)]
        with self.path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def _load(self) -> None:
        with self.path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                value = json.loads(line)
                rule_data = value.get("rule", {})
                rule = PolicyRule(
                    policy_id=str(rule_data.get("policy_id", "")),
                    text="",
                    tool=str(rule_data.get("tool", "")),
                    object=str(rule_data.get("object", "")),
                    condition=str(rule_data.get("condition", "")),
                    effect=str(rule_data.get("effect", "ask_confirmation")),
                    severity=str(rule_data.get("severity", "medium")),
                    priority=int(rule_data.get("priority", 0)),
                    issuer=str(rule_data.get("issuer", "")),
                    authority=int(rule_data.get("authority", 0)),
                    version=int(rule_data.get("version", 1)),
                    supersedes=tuple(str(item) for item in rule_data.get("supersedes", [])),
                    active=bool(rule_data.get("active", True)),
                    compiler_status=str(rule_data.get("compiler_status", "valid")),
                )
                self._items[str(value["cache_key"])] = PolicyManifest(
                    cache_key=str(value["cache_key"]), model=str(value.get("model", "")), rule=rule
                )


def manifest_key(policy: Policy, model: str) -> str:
    """缓存键只包含原始文本、可信来源元数据、模型和 prompt 版本。"""

    payload = {
        "text": policy.text,
        "issuer": policy.issuer,
        "authority": policy.authority,
        "version": policy.version,
        "supersedes": policy.supersedes,
        "active": policy.active,
        "model": model,
        "prompt_version": PROMPT_VERSION,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def compile_policy(policy: Policy, client: ChatClient, model: str) -> PolicyRule:
    """调用显式传入的 LLM client；该函数只由缓存构建脚本使用。"""

    provenance = {
        "issuer": policy.issuer,
        "authority": policy.authority,
        "version": policy.version,
        "supersedes": policy.supersedes,
        "active": policy.active,
    }
    response = client.complete(build_compiler_messages(policy, provenance), model=model, temperature=0.0, max_tokens=350, json_mode=True)
    try:
        parsed = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Policy compiler returned invalid JSON for {policy.policy_id}: {response.text[:160]}") from exc
    # 不同模型常用 confirm/deny 等同义输出；统一到 benchmark 的四类决策空间。
    raw_effect = parsed.get("effect") or parsed.get("decision") or parsed.get("action") or ""
    effect = normalize_effect(raw_effect) or infer_effect_from_text(policy.text)
    tool = str(parsed.get("tool", "")).strip()
    condition, predicate_errors = compile_predicates(parsed.get("predicates") if "predicates" in parsed else None)
    # Text 模式用规范化事实谓词表达作用域，object 仅保留中性的 any，避免双重语义门控。
    object_name = "any"
    active = policy.active
    compiler_status = "valid"
    if str(parsed.get("kind", "")).strip().lower() == "non_safety" or effect not in VALID_EFFECTS:
        # archive/send/search 等工作流动作不是安全决策，作为无关候选保留但不参与证明。
        effect = "ask_confirmation"
        active = False
        compiler_status = "inactive_non_safety"
    else:
        errors = compiled_rule_errors(tool, object_name, condition)
        errors.extend(predicate_errors)
        errors = list(dict.fromkeys(errors))
        if errors:
            # Text 模式不能借用原策略的结构字段修补 LLM 输出，schema 无效时必须显式失活。
            active = False
            compiler_status = "inactive_invalid_schema:" + ",".join(errors)
    return PolicyRule(
        policy_id=policy.policy_id,
        text=policy.text,
        tool=tool,
        object=object_name,
        condition=condition,
        effect=effect,
        severity=str(parsed.get("severity", "medium")).strip() or "medium",
        priority=0,
        issuer=policy.issuer,
        authority=policy.authority,
        version=policy.version,
        supersedes=tuple(policy.supersedes),
        active=active,
        compiler_status=compiler_status,
    )


def build_compiler_messages(policy: Policy, provenance: dict[str, object]) -> list[dict[str, str]]:
    """给 Text compiler 提供公开事实本体，而非策略自带结构字段。"""

    schema = {
        "allowed_tools": sorted(ALLOWED_TOOLS),
        "predicate_schema": PREDICATE_SPECS,
        "demonstrations": [
            {
                "policy_text": "Ask for confirmation before sending email to external recipients.",
                "output": {
                    "kind": "safety_rule",
                    "tool": "send_email",
                    "predicates": [{"fact": "target_external", "operator": "==", "value": True}],
                    "effect": "ask_confirmation",
                    "severity": "high",
                },
            },
            {
                "policy_text": "Block sharing when confidential data is involved.",
                "output": {
                    "kind": "safety_rule",
                    "tool": "share_file",
                    "predicates": [{"fact": "data_sensitivity", "operator": "==", "value": "confidential"}],
                    "effect": "block",
                    "severity": "critical",
                },
            },
            {
                "policy_text": "Allow public email to an internal target.",
                "output": {
                    "kind": "safety_rule",
                    "tool": "send_email",
                    "predicates": [
                        {"fact": "target_external", "operator": "==", "value": False},
                        {"fact": "data_sensitivity", "operator": "==", "value": "public"},
                    ],
                    "effect": "allow",
                    "severity": "low",
                },
            },
            {
                "policy_text": "Do not delete VIP client email threads.",
                "output": {
                    "kind": "safety_rule",
                    "tool": "delete_email",
                    "predicates": [{"fact": "category", "operator": "==", "value": "vip"}],
                    "effect": "block",
                    "severity": "critical",
                },
            },
            {
                "policy_text": "Archive every email draft after review.",
                "output": {
                    "kind": "non_safety",
                    "tool": "",
                    "predicates": [],
                    "effect": "",
                    "severity": "low",
                },
            },
        ],
        "effects": sorted(VALID_EFFECTS),
    }
    return [
        {
            "role": "system",
            "content": (
                "Compile one natural-language safety policy into strict JSON. Return exactly the keys kind, tool, predicates, effect, severity. "
                "kind must be safety_rule or non_safety. For safety_rule, tool and every predicate must use the supplied ontology exactly. "
                "A domain name such as email or slack is never a tool. Do not output object or condition fields. "
                "If the text describes a workflow operation rather than an allow/block/confirmation/revise safety rule, return kind=non_safety. "
                "Extract only constraints explicitly stated by the policy. Never add contains_secret, upload, channel, or other semantics merely "
                "because the policy mentions confidential data. Use target_external for all external recipients, attendees, users, and websites. "
                "Use data_sensitivity for confidential/public data. An unconditional policy uses an empty predicates list. Ontology: "
                + json.dumps(schema, ensure_ascii=False)
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"policy_text": policy.text, "trusted_provenance": provenance}, ensure_ascii=False),
        },
    ]


def compile_predicates(value: object) -> tuple[str, list[str]]:
    """把受限 JSON predicate 列表编译成 verifier 已支持的确定性条件表达式。"""

    if not isinstance(value, list):
        return "", ["predicates"]
    conditions: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            return "", ["predicates"]
        fact = str(item.get("fact", "")).strip()
        operator = normalize_operator(item.get("operator", ""))
        spec = PREDICATE_SPECS.get(fact)
        if spec is None or operator not in spec.get("operators", []):
            return "", ["predicates"]
        raw_value = item.get("value")
        if not predicate_value_is_valid(raw_value, spec):
            return "", ["predicates"]
        conditions.append(f"{fact} {operator} {render_predicate_value(raw_value)}")
    return " and ".join(conditions), []


def normalize_operator(value: object) -> str:
    aliases = {"eq": "==", "equals": "==", "ne": "!=", "not_equals": "!=", "gt": ">"}
    normalized = str(value).strip().lower()
    return aliases.get(normalized, normalized)


def predicate_value_is_valid(value: object, spec: dict[str, object]) -> bool:
    value_type = spec.get("type")
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "enum":
        allowed = {str(item) for item in spec.get("values", [])}
        return isinstance(value, str) and value.lower() in allowed
    return isinstance(value, str) and bool(value.strip())


def render_predicate_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).lower().replace("'", "\\'")
    return f"'{escaped}'"


def compiled_rule_errors(tool: str, object_name: str, condition: str) -> list[str]:
    """拒绝自由生成但无法被 Action facts 验证的 tool、object 和 condition。"""

    errors = []
    if tool not in ALLOWED_TOOLS:
        errors.append("tool")
    if object_name not in SUPPORTED_OBJECTS:
        errors.append("object")
    if not condition_is_supported(condition):
        errors.append("condition")
    return errors


def condition_is_supported(condition: str) -> bool:
    if not condition:
        return True
    parts = [part.strip() for part in condition.split(" and ") if part.strip()]
    if not parts:
        return False
    for part in parts:
        if re.fullmatch(r"path\.startswith\(['\"][^'\"]+['\"]\)", part):
            continue
        match = re.fullmatch(r"([a-z_]+)\s*(==|!=|>)\s*'?[^']+'?", part)
        if not match or match.group(1) not in CONDITION_FIELDS:
            return False
    return True


def normalize_effect(value: object) -> str:
    """将模型返回的 effect 同义词收敛为标准动作决策标签。"""

    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    direct = EFFECT_ALIASES.get(normalized)
    if direct:
        return direct
    # 先识别明确阻断，避免 "block_without_approval" 被错误降级为确认。
    if any(marker in normalized for marker in ("block", "deny", "reject", "forbid", "prohibit")):
        return "block"
    if any(marker in normalized for marker in ("confirm", "approval", "review", "warn", "caution", "escalat")):
        return "ask_confirmation"
    if any(marker in normalized for marker in ("allow", "execute", "permit")):
        return "allow"
    if any(marker in normalized for marker in ("revise", "modify", "edit")):
        return "revise"
    return ""


def infer_effect_from_text(text: str) -> str:
    """仅在 LLM 遗漏 effect 字段时，从策略原文恢复显式的动作效果。"""

    lowered = text.lower()
    if any(
        marker in lowered
        for marker in (
            "ask for confirmation",
            "ask confirmation",
            "require confirmation",
            "require approval",
            "be careful",
            "use caution",
            "请求确认",
            "请确认",
            "谨慎",
            "小心",
        )
    ):
        return "ask_confirmation"
    if any(marker in lowered for marker in ("do not", "never", "block", "forbid", "deny", "不得", "禁止", "阻止")):
        return "block"
    if any(marker in lowered for marker in ("allow", "允许")):
        return "allow"
    if any(marker in lowered for marker in ("revise", "modify", "修改")):
        return "revise"
    return ""
