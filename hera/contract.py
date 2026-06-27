"""출력 계약 모델 — 2단 생성 플랫폼이 곧바로 소비하는 객체.

스키마:
    {
      "form_type": "lab",
      "classification": { "confidence": 0.97, "via": "semantic | cache | hardcoded" },
      "target_task": "검사결과 판독/요약",
      "target_role": "검사 의뢰의",
      "fhir_bundle": { "resourceType": "Bundle", "type": "collection | document", ... },
      "validation": { "r4_valid": true, "invariants": "5/5 ...", "errors": [] }
    }

Phase 1: 스파인 확정. via="hardcoded"는 Phase 3에서 Profiler 연결 시 semantic/cache로 대체.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Classification(BaseModel):
    confidence: float
    via: str  # "semantic" | "cache" | "hardcoded"


class Validation(BaseModel):
    r4_valid: bool
    invariants: str
    errors: list[str] = Field(default_factory=list)


class Contract(BaseModel):
    form_type: str
    classification: Classification
    target_task: str
    target_role: str
    fhir_bundle: dict
    validation: Validation
