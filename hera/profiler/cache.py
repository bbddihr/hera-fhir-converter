"""시그니처 → 분류결과 영속 캐시 (JSON 파일).

cache hit 시 LLM 호출 없이 form_type/confidence를 즉시 반환(결정론·고속·저비용).
파일은 .gitignore 처리되어 저장소에 올라가지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path

# 모듈 레벨 — 테스트에서 monkeypatch로 임시 경로 주입 가능.
CACHE_PATH = Path(__file__).resolve().parent / ".signature_cache.json"


def _load() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def lookup(sig: str) -> dict | None:
    """시그니처에 대응하는 분류결과 {form_type, confidence} 또는 None."""
    return _load().get(sig)


def write(sig: str, result: dict) -> None:
    """분류결과를 시그니처와 함께 적재."""
    data = _load()
    data[sig] = result
    CACHE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
