"""SafeMem 回归测试模块。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class LlmResponse:
    text: str
    raw: dict[str, Any]
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LlmSettings:
    """单个 LLM profile 的连接与供应商扩展配置。"""

    profile: str = ""
    provider: str = "openai_compatible"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = ""
    request_options: dict[str, Any] = field(default_factory=dict)
    omit_request_fields: set[str] = field(default_factory=set)


class ChatClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LlmResponse:
        raise NotImplementedError


class EmbeddingClient(Protocol):
    """真实 Dense Embedding 的最小接口，便于接入 OpenAI-compatible 服务。"""

    def embed(self, texts: list[str], *, model: str) -> list[list[float]]:
        raise NotImplementedError


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        profile: str = "",
        config_path: str | Path | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = load_llm_settings(profile=profile, config_path=config_path)
        self.api_key = api_key or _first_env("SAFEMEM_LLM_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY") or settings.api_key
        self.base_url = (
            base_url
            or _first_env("SAFEMEM_LLM_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL")
            or settings.base_url
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.timeout = timeout
        self.request_options = dict(settings.request_options)
        self.omit_request_fields = set(settings.omit_request_fields)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LlmResponse:
        if not self.api_key:
            raise RuntimeError("Missing API key. Set SAFEMEM_LLM_API_KEY, LLM_API_KEY, or OPENAI_API_KEY.")
        if not model:
            raise RuntimeError("Missing model. Pass --model or set SAFEMEM_LLM_MODEL / LLM_MODEL.")

        # 供应商扩展参数（例如 Kimi 的 thinking 开关）只补充请求体，
        # 不允许覆盖基准评测固定的模型、消息和生成参数。
        payload: dict[str, Any] = dict(self.request_options)
        payload.update({
            "model": model,
            "messages": messages,
        })
        if "temperature" not in self.omit_request_fields:
            payload["temperature"] = temperature
        if "max_tokens" not in self.omit_request_fields:
            payload["max_tokens"] = max_tokens
        if json_mode and "response_format" not in self.omit_request_fields:
            payload["response_format"] = {"type": "json_object"}

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM API request failed: {exc}") from exc

        choice = raw.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = raw.get("usage", {})
        return LlmResponse(
            text=message.get("content", ""),
            raw=raw,
            model=raw.get("model", model),
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
            total_tokens=int(usage.get("total_tokens", 0) or 0),
        )


class OpenAICompatibleEmbeddingClient:
    """调用 OpenAI-compatible `/embeddings` 端点，不复用哈希词袋伪向量。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        profile: str = "",
        config_path: str | Path | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = load_llm_settings(profile=profile, config_path=config_path)
        self.api_key = api_key or settings.embedding_api_key or settings.api_key
        self.base_url = (base_url or settings.embedding_base_url or settings.base_url).rstrip("/")
        self.timeout = timeout

    def embed(self, texts: list[str], *, model: str) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("Missing embedding API key in the selected profile.")
        if not self.base_url or not model:
            raise RuntimeError("Missing embedding base URL or model in the selected profile.")
        payload = {"model": model, "input": texts}
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        raw = _read_json(request, self.timeout, "Embedding API")
        return [list(item.get("embedding", [])) for item in raw.get("data", [])]


class AnthropicClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        profile: str = "",
        config_path: str | Path | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = load_llm_settings(profile=profile, config_path=config_path)
        self.api_key = api_key or _first_env("SAFEMEM_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY") or settings.api_key
        self.base_url = (base_url or settings.base_url or "https://api.anthropic.com/v1").rstrip("/")
        self.timeout = timeout

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LlmResponse:
        if not self.api_key:
            raise RuntimeError("Missing Anthropic API key. Set SAFEMEM_ANTHROPIC_API_KEY or configure the profile.")
        if not model:
            raise RuntimeError("Missing Anthropic model. Pass --model or configure the profile.")

        system, anthropic_messages = _split_system_message(messages)
        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            payload["system"] = system

        request = urllib.request.Request(
            f"{self.base_url}/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        raw = _read_json(request, self.timeout, "LLM API")
        text = "".join(part.get("text", "") for part in raw.get("content", []) if part.get("type") == "text")
        usage = raw.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0) or 0)
        completion_tokens = int(usage.get("output_tokens", 0) or 0)
        return LlmResponse(
            text=text,
            raw=raw,
            model=raw.get("model", model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        profile: str = "",
        config_path: str | Path | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = load_llm_settings(profile=profile, config_path=config_path)
        self.api_key = api_key or _first_env("SAFEMEM_GEMINI_API_KEY", "GEMINI_API_KEY") or settings.api_key
        self.base_url = (
            base_url
            or settings.base_url
            or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        self.timeout = timeout
        self.request_options = dict(settings.request_options)
        self.omit_request_fields = set(settings.omit_request_fields)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LlmResponse:
        if not self.api_key:
            raise RuntimeError("Missing Gemini API key. Set SAFEMEM_GEMINI_API_KEY or configure the profile.")
        if not model:
            raise RuntimeError("Missing Gemini model. Pass --model or configure the profile.")

        system, user_messages = _split_system_message(messages)
        # Gemini 的供应商扩展项位于 generationConfig，例如 thinkingConfig。
        generation_config: dict[str, Any] = dict(self.request_options)
        if "temperature" not in self.omit_request_fields:
            generation_config["temperature"] = temperature
        if "maxOutputTokens" not in self.omit_request_fields:
            generation_config["maxOutputTokens"] = max_tokens
        payload: dict[str, Any] = {
            "contents": [
                {"role": _gemini_role(item["role"]), "parts": [{"text": item["content"]}]}
                for item in user_messages
            ],
            "generationConfig": generation_config,
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode and "responseMimeType" not in self.omit_request_fields:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        request = urllib.request.Request(
            f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        raw = _read_json(request, self.timeout, "LLM API")
        candidates = raw.get("candidates", [])
        content = candidates[0].get("content", {}) if candidates else {}
        text = "".join(part.get("text", "") for part in content.get("parts", []))
        usage = raw.get("usageMetadata", {})
        prompt_tokens = int(usage.get("promptTokenCount", 0) or 0)
        completion_tokens = int(usage.get("candidatesTokenCount", 0) or 0)
        total_tokens = int(usage.get("totalTokenCount", prompt_tokens + completion_tokens) or 0)
        return LlmResponse(
            text=text,
            raw=raw,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )


def make_chat_client(
    *,
    api_key: str = "",
    base_url: str = "",
    profile: str = "",
    config_path: str | Path | None = None,
    timeout: float = 60.0,
) -> ChatClient:
    settings = load_llm_settings(profile=profile, config_path=config_path)
    provider = settings.provider.lower().replace("-", "_")
    if provider in {"", "openai", "openai_compatible", "compatible"}:
        return OpenAICompatibleClient(api_key, base_url, profile, config_path, timeout)
    if provider in {"anthropic", "claude"}:
        return AnthropicClient(api_key, base_url, profile, config_path, timeout)
    if provider in {"gemini", "google"}:
        return GeminiClient(api_key, base_url, profile, config_path, timeout)
    raise RuntimeError(f"Unsupported LLM provider for profile '{settings.profile}': {settings.provider}")


def make_embedding_client(
    *,
    api_key: str = "",
    base_url: str = "",
    profile: str = "",
    config_path: str | Path | None = None,
    timeout: float = 60.0,
) -> EmbeddingClient:
    """当前 dense adapter 使用 OpenAI-compatible 协议，供应商由 profile 提供。"""

    return OpenAICompatibleEmbeddingClient(api_key, base_url, profile, config_path, timeout)


def configured_model(
    value: str = "",
    *,
    profile: str = "",
    config_path: str | Path | None = None,
) -> str:
    settings = load_llm_settings(profile=profile, config_path=config_path)
    return value or _first_env("SAFEMEM_LLM_MODEL", "LLM_MODEL", "OPENAI_MODEL") or settings.model


def configured_embedding_model(
    value: str = "",
    *,
    profile: str = "",
    config_path: str | Path | None = None,
) -> str:
    """读取 profile 中的真实 embedding 模型；未配置时让调用方显式报错。"""

    settings = load_llm_settings(profile=profile, config_path=config_path)
    return value or settings.embedding_model


def load_llm_settings(
    *,
    profile: str = "",
    config_path: str | Path | None = None,
) -> LlmSettings:
    path = Path(config_path) if config_path else _default_config_path()
    if not path.exists():
        return LlmSettings(profile=profile)

    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    profiles = data.get("profiles", {})
    profile_name = profile or data.get("default_profile", "")
    if not profile_name:
        return LlmSettings()
    selected = profiles.get(profile_name, {})
    if not isinstance(selected, dict):
        return LlmSettings(profile=profile_name)
    return LlmSettings(
        profile=profile_name,
        provider=str(selected.get("provider", "openai_compatible")).strip() or "openai_compatible",
        api_key=str(selected.get("api_key", "")).strip(),
        base_url=str(selected.get("base_url", "")).strip(),
        model=str(selected.get("model", "")).strip(),
        embedding_api_key=str(selected.get("embedding_api_key", "")).strip(),
        embedding_base_url=str(selected.get("embedding_base_url", "")).strip(),
        embedding_model=str(selected.get("embedding_model", "")).strip(),
        request_options=_request_options(selected.get("request_options", {})),
        omit_request_fields=_omit_request_fields(selected.get("omit_request_fields", [])),
    )


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "llm.local.json"


def _first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _request_options(value: Any) -> dict[str, Any]:
    """只接受 JSON 对象形式的供应商扩展参数，避免错误配置进入请求体。"""

    if not isinstance(value, dict):
        return {}
    return dict(value)


def _omit_request_fields(value: Any) -> set[str]:
    """允许 profile 省略少数不被某些兼容端点接受的标准字段。"""

    allowed = {"temperature", "max_tokens", "response_format", "maxOutputTokens", "responseMimeType"}
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip() in allowed}


def _read_json(request: urllib.request.Request, timeout: float, label: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{label} HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{label} request failed: {exc}") from exc


def _split_system_message(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts = [item["content"] for item in messages if item.get("role") == "system"]
    non_system = [
        {"role": item.get("role", "user"), "content": item.get("content", "")}
        for item in messages
        if item.get("role") != "system"
    ]
    return "\n\n".join(system_parts), non_system


def _gemini_role(role: str) -> str:
    if role == "assistant":
        return "model"
    return "user"
