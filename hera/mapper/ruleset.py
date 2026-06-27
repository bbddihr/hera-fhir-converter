"""룰셋 로더 — 임상 전문가가 코드 없이 수정하는 YAML 매핑 정의.

검사형 룰셋: UCUM 단위 정규화(ucum_aliases) + 항목별 (선택)LOINC 코드.
미정의 항목은 text 코드 + 원본 단위로 폴백한다(스코프 제한).
"""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

RULESET_DIR = Path(__file__).resolve().parents[1] / "rulesets"


@functools.lru_cache(maxsize=None)
def load_lab_ruleset() -> dict:
    """rulesets/lab-observation.yaml 로드 (캐시)."""
    path = RULESET_DIR / "lab-observation.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
