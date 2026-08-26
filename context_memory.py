# -*- coding: utf-8 -*-
"""
轻量级上下文记忆模块：为 Agent 提供跨轮次的上下文联系。

使用内存 dict 按 student_id 存储（生产环境可换 Redis/DB）。
替代 RAG 向量检索，满足「上下文联系」需求；若无 session 则用本模块。
"""
from __future__ import annotations

from typing import Any

# student_id -> { "profile_summary", "key_facts", "personality_diagnosis", "regret_result" }
_MEMORY: dict[int, dict[str, Any]] = dict()
_MAX_FACTS = 20


def get(student_id: int) -> dict[str, Any]:
    return _MEMORY.get(student_id, {}).copy()


def set_profile_summary(student_id: int, summary: str) -> None:
    _ensure(student_id)
    _MEMORY[student_id]["profile_summary"] = summary


def add_key_fact(student_id: int, fact: str) -> None:
    _ensure(student_id)
    facts = _MEMORY[student_id].setdefault("key_facts", [])
    facts.append(fact)
    _MEMORY[student_id]["key_facts"] = facts[-_MAX_FACTS:]


def set_personality_diagnosis(student_id: int, diagnosis: dict[str, Any]) -> None:
    _ensure(student_id)
    _MEMORY[student_id]["personality_diagnosis"] = diagnosis


def set_regret_result(student_id: int, result: Any) -> None:
    _ensure(student_id)
    _MEMORY[student_id]["regret_result"] = result


def _ensure(student_id: int) -> None:
    if student_id not in _MEMORY:
        _MEMORY[student_id] = {}


def to_context_string(student_id: int) -> str:
    """拼成可注入 LLM 上下文的字符串"""
    m = get(student_id)
    parts = []
    if m.get("profile_summary"):
        parts.append("【画像摘要】" + m["profile_summary"])
    if m.get("key_facts"):
        parts.append("【用户提及的关键信息】" + "；".join(m["key_facts"][-10:]))
    if m.get("personality_diagnosis"):
        d = m["personality_diagnosis"]
        if isinstance(d, dict):
            s = str(d.get("summary", d))
        else:
            s = str(d)
        parts.append("【性格与短板诊断】" + s)
    if m.get("regret_result"):
        r = m["regret_result"]
        if hasattr(r, "recommendation"):
            parts.append("【博弈路径建议】" + r.recommendation)
        else:
            parts.append("【博弈路径建议】" + str(r))
    if not parts:
        return ""
    return "\n".join(parts)
