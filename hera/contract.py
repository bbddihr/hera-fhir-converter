"""출력 계약 모델 — 2단 생성 플랫폼이 곧바로 소비하는 객체.

목표 스키마:
    {
      "form_type": "anesthesia_record",
      "classification": { "confidence": 0.97, "via": "semantic | cache" },
      "target_task": "마취통증의학과 협의진료 회신서",
      "target_role": "마취과 전문의",
      "fhir_bundle": { "resourceType": "Bundle", "type": "document | collection", ... },
      "validation": { "r4_valid": true, "invariants": "12/12", "errors": [] }
    }

Phase 0: 스텁. Phase 1에서 Pydantic 모델로 스파인 확정.
"""
from __future__ import annotations

# TODO(Phase 1): Pydantic 모델 정의 (Classification, Validation, Contract).
