"""파이프라인 오케스트레이터: XML → 계약 객체.

흐름:
    XML → [Profiler] cache → semantic → cache (form_type 판별)
        → [Router] form_type 분기 → [Mapper] FHIR Bundle 조립
        → [Validator] R4 검증 → 계약 객체

Profiler가 1차(cache | semantic | fallback), Router가 검사형(collection)/서사형(document)을 분기한다.
"""
from __future__ import annotations

from . import config, tasks
from .contract import Classification, Contract, Validation
from .mapper import router
from .profiler import cache, semantic, signature
from .validator import validate


def profile(xml: str) -> dict:
    """form_type 판별 — cache 우선, 미적중 시 semantic, 키 없으면 fallback.

    Returns:
        {"form_type": str, "confidence": float, "via": "cache|semantic|fallback"}
    """
    sig = signature.signature(xml)

    cached = cache.lookup(sig)
    if cached:
        return {**cached, "via": "cache"}

    if config.api_key_present():
        try:
            result = semantic.classify(xml)
            cache.write(sig, result)
            return {**result, "via": "semantic"}
        except Exception:  # noqa: BLE001 — 분류 실패 시 데모가 멈추지 않도록 폴백
            pass

    # 폴백: 키 없음 또는 분류 실패 → MVP 기본 도메인(lab)으로 진행.
    return {"form_type": "lab", "confidence": 0.0, "via": "fallback"}


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
    profiled = profile(xml)
    form_type = profiled["form_type"]
    target_task, target_role = tasks.task_for(form_type)

    # form_type → 매퍼 분기 (검사형: collection / 서사형: document)
    bundle = router.route(form_type, xml)
    validation = validate(bundle)

    contract = Contract(
        form_type=form_type,
        classification=Classification(
            confidence=profiled["confidence"], via=profiled["via"]
        ),
        target_task=target_task,
        target_role=target_role,
        fhir_bundle=bundle,
        validation=Validation(**validation),
    )
    return contract.model_dump()
