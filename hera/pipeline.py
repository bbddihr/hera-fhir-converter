"""파이프라인 오케스트레이터: XML → 계약 객체.

흐름(목표):
    XML → [Profiler] form_type 판별 → [Router] 매핑 분기
        → [Mapper] FHIR Bundle 조립 → [Validator] R4 검증 → 계약 객체

Phase 0: 스켈레톤. Phase 1에서 lab 수직 슬라이스(form_type 고정)로 구현 시작.
"""
from __future__ import annotations


def convert(xml: str) -> dict:
    """원본 EMR XML을 FHIR 계약 객체(dict)로 변환한다.

    Args:
        xml: 병원 EMR 의무기록 원본 XML 문자열.

    Returns:
        계약 객체 — {form_type, classification, target_task, target_role,
        fhir_bundle, validation}.

    Raises:
        NotImplementedError: Phase 0 스켈레톤. Phase 1에서 구현 예정.
    """
    raise NotImplementedError("pipeline.convert()는 Phase 1에서 구현됩니다.")
