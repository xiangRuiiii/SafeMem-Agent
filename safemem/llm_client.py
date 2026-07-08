from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
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
    profile: str = ""
    api_key: str = ""
    base_url: str = ""
    model: str = ""


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

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
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


def configured_model(
    value: str = "",
    *,
    profile: str = "",
    config_path: str | Path | None = None,
) -> str:
    settings = load_llm_settings(profile=profile, config_path=config_path)
    return value or _first_env("SAFEMEM_LLM_MODEL", "LLM_MODEL", "OPENAI_MODEL") or settings.model


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
        api_key=str(selected.get("api_key", "")).strip(),
        base_url=str(selected.get("base_url", "")).strip(),
        model=str(selected.get("model", "")).strip(),
    )


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "llm.local.json"


def _first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""
