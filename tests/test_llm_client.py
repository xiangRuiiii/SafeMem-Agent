"""LLM 客户端配置与请求体回归测试。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from safemem.llm_client import GeminiClient, OpenAICompatibleClient, load_llm_settings


class _FakeResponse:
    """模拟一次成功的 OpenAI-compatible 响应，不产生真实网络请求。"""

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        return False

    def read(self) -> bytes:
        return b'{"model":"kimi-k2.6","choices":[{"message":{"content":"{}"}}],"usage":{}}'


class _FakeGeminiResponse:
    """模拟 Gemini JSON 响应，验证其 generationConfig 不会丢失扩展字段。"""

    def __enter__(self) -> "_FakeGeminiResponse":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        return False

    def read(self) -> bytes:
        return b'{"candidates":[{"content":{"parts":[{"text":"{}"}]}}],"usageMetadata":{}}'


class LlmClientTest(unittest.TestCase):
    def test_openai_compatible_forwards_profile_request_options(self) -> None:
        """Kimi profile 必须把关闭思考模式的参数写入 HTTP 请求体。"""

        config = {
            "profiles": {
                "kimi": {
                    "provider": "openai_compatible",
                    "base_url": "https://api.moonshot.cn/v1",
                    "model": "kimi-k2.6",
                    "api_key": "test-key",
                    "request_options": {"thinking": {"type": "disabled"}},
                    "omit_request_fields": ["temperature"],
                }
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "llm.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            settings = load_llm_settings(profile="kimi", config_path=config_path)
            self.assertEqual(settings.request_options, {"thinking": {"type": "disabled"}})
            self.assertEqual(settings.omit_request_fields, {"temperature"})

            client = OpenAICompatibleClient(profile="kimi", config_path=config_path)
            with patch("safemem.llm_client.urllib.request.urlopen", return_value=_FakeResponse()) as open_url:
                client.complete(
                    [{"role": "user", "content": "Return JSON."}],
                    model="kimi-k2.6",
                    temperature=0.0,
                    max_tokens=64,
                    json_mode=True,
                )

        request = open_url.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["model"], "kimi-k2.6")
        self.assertEqual(payload["max_tokens"], 64)
        self.assertNotIn("temperature", payload)
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_gemini_forwards_thinking_config(self) -> None:
        """Gemini profile 的低思考设置必须进入 generationConfig。"""

        config = {
            "profiles": {
                "gemini": {
                    "provider": "gemini",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta",
                    "model": "gemini-3.5-flash",
                    "api_key": "test-key",
                    "request_options": {"thinkingConfig": {"thinkingLevel": "low"}},
                }
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "llm.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            client = GeminiClient(profile="gemini", config_path=config_path)
            with patch("safemem.llm_client.urllib.request.urlopen", return_value=_FakeGeminiResponse()) as open_url:
                client.complete(
                    [{"role": "user", "content": "Return JSON."}],
                    model="gemini-3.5-flash",
                    temperature=0.0,
                    max_tokens=64,
                    json_mode=True,
                )

        request = open_url.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["generationConfig"]["thinkingConfig"], {"thinkingLevel": "low"})
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")


if __name__ == "__main__":
    unittest.main()
