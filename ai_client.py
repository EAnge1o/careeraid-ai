from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import requests

# 单例模式实现
class Singleton:
    _instances = {}
    
    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__new__(cls)
        return cls._instances[cls]

# 单例模式实现
class Singleton:
    _instances = {}
    
    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__new__(cls)
        return cls._instances[cls]


@dataclass
class LLMConfig:
    provider: str = "offline"  # offline | spark | openai_compatible | volc
    spark_app_id: str = ""
    spark_api_key: str = ""
    spark_api_secret: str = ""
    spark_api_url: str = ""
    spark_model: str = ""
    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    # 火山引擎（火山方舟/豆包）大模型 API 预留
    volc_base_url: str = ""
    volc_api_key: str = ""
    volc_model: str = ""
    volc_enable_web_search: bool = False


def load_llm_config() -> LLMConfig:
    provider = (os.getenv("AI_PROVIDER") or "offline").strip().lower()
    return LLMConfig(
        provider=provider,
        spark_app_id=os.getenv("SPARK_APP_ID", ""),
        spark_api_key=os.getenv("SPARK_API_KEY", ""),
        spark_api_secret=os.getenv("SPARK_API_SECRET", ""),
        spark_api_url=os.getenv("SPARK_API_URL", ""),
        spark_model=os.getenv("SPARK_MODEL", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", ""),
        volc_base_url=os.getenv("VOLC_BASE_URL", "").rstrip("/") or os.getenv("VOLC_API_ENDPOINT", "").rstrip("/"),
        volc_api_key=os.getenv("VOLC_API_KEY", "") or os.getenv("ARK_API_KEY", ""),
        volc_model=os.getenv("VOLC_MODEL", "") or os.getenv("ARK_MODEL_ID", ""),
        volc_enable_web_search=(os.getenv("VOLC_ENABLE_WEB_SEARCH", "").strip().lower() in {"1", "true", "yes"}),
    )


class AIClient(Singleton):
    """
    说明：
    - 这里提供“可接入”星火/通用 OpenAI-兼容接口的封装入口。
    - 由于不同版本星火接口鉴权/URL/参数差异较大，本项目以“可配置 + 可替换”方式提供。
    - 未配置密钥时自动回退到 offline，由 ai_helper 走规则/相似度兜底。
    """

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        if not hasattr(self, 'config'):
            self.config = config or load_llm_config()

    def is_enabled(self) -> bool:
        if self.config.provider == "spark":
            return bool(self.config.spark_api_url and self.config.spark_api_key and self.config.spark_api_secret)
        if self.config.provider == "openai_compatible":
            return bool(self.config.openai_base_url and self.config.openai_api_key and self.config.openai_model)
        if self.config.provider == "volc":
            return bool(self.config.volc_base_url and self.config.volc_api_key and self.config.volc_model)
        return False

    def chat_json(self, system_prompt: str, user_prompt: str, schema_hint: str = "") -> dict[str, Any]:
        """
        期望返回 JSON（文本可被 json.loads 解析）。
        - schema_hint 用于提示输出字段结构（不强制）。
        """
        if not self.is_enabled():
            raise RuntimeError("LLM not configured. Please set .env, or use offline fallback.")

        if self.config.provider == "openai_compatible":
            return self._openai_compatible_chat_json(system_prompt, user_prompt, schema_hint=schema_hint)

        if self.config.provider == "volc":
            return self._volc_chat_json(system_prompt, user_prompt, schema_hint=schema_hint)

        if self.config.provider == "spark":
            raise NotImplementedError(
                "Spark provider placeholder. Please implement per your Spark API docs, or switch AI_PROVIDER=offline."
            )

        raise RuntimeError(f"Unknown provider: {self.config.provider}")

    def chat_text(self, system_prompt: str, user_prompt: str) -> str:
        """返回纯文本（用于 Agent 对话）。"""
        if not self.is_enabled():
            raise RuntimeError("LLM not configured. Please set .env, or use offline fallback.")

        if self.config.provider == "openai_compatible":
            return self._openai_compatible_chat_text(system_prompt, user_prompt)

        if self.config.provider == "volc":
            return self._volc_chat_text(system_prompt, user_prompt)

        if self.config.provider == "spark":
            raise NotImplementedError(
                "Spark provider placeholder. Please implement per your Spark API docs, or switch AI_PROVIDER=offline."
            )

        raise RuntimeError(f"Unknown provider: {self.config.provider}")

    def _openai_compatible_chat_json(
        self, system_prompt: str, user_prompt: str, schema_hint: str = ""
    ) -> dict[str, Any]:
        url = self.config.openai_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.openai_api_key}", "Content-Type": "application/json"}
        content = user_prompt if not schema_hint else f"{user_prompt}\n\n输出 JSON 结构参考：\n{schema_hint}"
        payload = {
            "model": self.config.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "temperature": 0.2,
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return json.loads(text)

    def _openai_compatible_chat_text(self, system_prompt: str, user_prompt: str) -> str:
        url = self.config.openai_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.openai_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.config.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _volc_chat_json(
        self, system_prompt: str, user_prompt: str, schema_hint: str = ""
    ) -> dict[str, Any]:
        """
        火山引擎（火山方舟/豆包）大模型 API 调用预留。
        方舟平台若提供 OpenAI 兼容端点，可直接用 AI_PROVIDER=openai_compatible + OPENAI_* 指向该端点；
        否则在此使用 VOLC_BASE_URL / VOLC_API_KEY / VOLC_MODEL 调用方舟自有接口。
        文档：https://www.volcengine.com/docs/82379/
        """
        url = self.config.volc_base_url
        # 若配置为 OpenAI 兼容的 base（如 /chat/completions 已含在 base 中），直接 POST
        if "/chat/completions" not in url and "/v1/" not in url:
            url = url.rstrip("/") + "/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.volc_api_key}",
            "Content-Type": "application/json",
        }
        content = user_prompt if not schema_hint else f"{user_prompt}\n\n输出 JSON 结构参考：\n{schema_hint}"
        payload = {
            "model": self.config.volc_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "temperature": 0.2,
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Volc API returned no choices")
        text = (choices[0].get("message") or {}).get("content") or ""
        return json.loads(text)

    def _volc_chat_text(self, system_prompt: str, user_prompt: str) -> str:
        url = self.config.volc_base_url
        if "/chat/completions" not in url and "/v1/" not in url:
            url = url.rstrip("/") + "/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.volc_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.volc_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Volc API returned no choices")
        return (choices[0].get("message") or {}).get("content") or ""

    def web_search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        """
        联网搜索（简易版）：默认使用 DuckDuckGo HTML 页面做兜底抓取，便于“市场要求/竞赛/岗位趋势”解释更严谨。
        若你后续要用火山引擎自带 Web Search 工具，可在这里替换为官方接口。
        """
        q = (query or "").strip()
        if not q:
            return []
        try:
            r = requests.get(
                "https://duckduckgo.com/html/",
                params={"q": q},
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            r.raise_for_status()
            html = r.text
            import re

            results: list[dict[str, str]] = []
            # 抓取前若干条结果标题与链接
            for m in re.finditer(r'<a rel="nofollow" class="result__a" href="([^"]+)".*?>(.*?)</a>', html, re.S):
                url = re.sub(r"&amp;", "&", m.group(1))
                title = re.sub(r"<.*?>", "", m.group(2)).strip()
                if title and url:
                    results.append({"title": title, "url": url})
                if len(results) >= limit:
                    break
            return results
        except Exception:
            return []