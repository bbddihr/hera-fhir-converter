"""파이프라인 오케스트레이터: XML → 계약 객체.

흐름:
    XML → [Profiler] form_type 판별 → [Router] 매핑 분기
        → [Mapper] FHIR Bundle 조립 → [Validator] R4 검증 → 계약 객체

Phase 1: form_type을 'lab'으로 고정(분류기 없이 매핑·검증·출력을 먼저 검증).
Phase 3에서 Profiler를 1차로 삽입하고 via='hardcoded'를 semantic/cache로 대체한다.
"""
from __future__ import annotations

from .contract import Classification, Contract, Validation
from .mapper import lab
from .mapper.value_parser import parse_lab_xml
from .validator import validate

# Phase 3에서 hera.tasks로 이관 예정.
_LAB_TASK = ("검사결과 판독/요약", "검사 의뢰의")


def convert(xml: str) -> dict:
    """원본 EMR XML을 FHIR 계약 객체(dict)로 변환한다.

    Args:
        xml: 병원 EMR 의무기록 원본 XML 문자열.

    Returns:
        계약 객체 dict — {form_type, classification, target_task, target_role,
        fhir_bundle, validation}.

    Raises:
        ValueError: well-formed XML이 아닐 때.
    """
    # Phase 1: 분류 고정.
    form_type = "lab"
    target_task, target_role = _LAB_TASK

    parsed = parse_lab_xml(xml)
    bundle = lab.build_bundle(parsed)
    validation = validate(bundle)

    contract = Contract(
        form_type=form_type,
        classification=Classification(confidence=1.0, via="hardcoded"),
        target_task=target_task,
        target_role=target_role,
        fhir_bundle=bundle,
        validation=Validation(**validation),
    )
    return contract.model_dump()
