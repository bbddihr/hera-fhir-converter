"""테스트 격리 — 실제 API 호출·실제 캐시 파일을 건드리지 않도록 기본 차단.

- cache.CACHE_PATH를 임시 파일로 우회
- api_key_present를 기본 False로 (semantic 경로를 테스트하는 케이스는 개별적으로 True 설정)
"""
from __future__ import annotations

import pytest

from hera import config
from hera.profiler import cache


@pytest.fixture(autouse=True)
def _isolate_external(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "test_cache.json")
    monkeypatch.setattr(config, "api_key_present", lambda: False)
    yield
