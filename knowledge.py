from __future__ import annotations

from pathlib import Path
from typing import List, Dict


_CACHE_TEXT: str | None = None


def _load_text() -> str:
    global _CACHE_TEXT
    if _CACHE_TEXT is not None:
        return _CACHE_TEXT
    base = Path(__file__).resolve().parent
    path = base / "data" / "knowledge_career.md"
    try:
        _CACHE_TEXT = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _CACHE_TEXT = ""
    return _CACHE_TEXT


def search_knowledge(query: str, max_chunks: int = 3) -> List[Dict[str, str]]:
    """从本地知识库中按关键字返回若干段落，作为轻量 RAG。"""
    text = _load_text()
    if not text or not query:
        return []
    q = query.lower()
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    results: List[Dict[str, str]] = []
    for p in parts:
        if any(k in p for k in ["Java", "前端", "AI", "算法", "大数据", "竞赛", "证书", "路径", "大厂", "国企"]):
            if any(w in p.lower() for w in q.split()):
                results.append({"snippet": p[:400]})
        if len(results) >= max_chunks:
            break
    return results

