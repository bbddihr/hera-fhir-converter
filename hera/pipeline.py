"""파이프라인 오케스트레이터: XML → 변환 결과.

흐름:
    XML → [Profiler] 의미 분석 (cache → LLM → fallback)
        → [Router] doc_kind 분기 → [Assembler] FHIR Bundle + 매핑 리포트
        → [Validator] R4 검증 → 변환 결과(analysis + mapping + bundle + validation)

LLM은 ② 의미 분석(판별·근거)만, ③④ FHIR 조립·검증은 결정론적 코드가 담당한다.
"""
from __future__ import annotations

from . import config
from .contract import Analysis, ConversionResult, MappingRow, Validation
from .mapper import router
from .profiler import analysis as analysis_mod
from .profiler import cache, signature
from .validator import validate


def analyze(xml: str) -> dict:
    """의미 분석 — cache 우선, 미적중 시 LLM, 키 없음/실패 시 구조 기반 폴백.

    Returns:
        {"doc_kind", "document_label", "confidence", "rationale", "via"}
    """
    sig = signature.signature(xml)

    cached = cache.lookup(sig)
    if cached:
        return {**cached, "via": "cache"}

    if config.api_key_present():
        try:
            result = analysis_mod.analyze(xml)
            cache.write(sig, result)
            return {**result, "via": "semantic"}
        except Exception:  # noqa: BLE001 — 분석 실패 시 데모가 멈추지 않도록 폴백
            pass

    return {**analysis_mod.heuristic(xml), "via": "fallback"}


def convert(xml: str) -> dict:
    """원본 EMR XML을 변환 결과(dict)로 변환한다.

    Returns:
        {analysis, mapping, coverage, fhir_bundle, validation}

    Raises:
        ValueError: well-formed XML이 아닐 때.
    """
    analyzed = analyze(xml)
    doc_kind = analyzed["doc_kind"]

    module = router.get_assembler(doc_kind)
    built = module.assemble(xml)
    validation = validate(built["bundle"])

    analysis = Analysis(
        doc_kind=doc_kind,
        document_label=analyzed["document_label"],
        confidence=analyzed["confidence"],
        via=analyzed["via"],
        rationale=analyzed.get("rationale", []),
        primary_resource=module.PRIMARY_RESOURCE,
        primary_note=getattr(module, "PRIMARY_NOTE", None),
        companion_resources=module.COMPANION_RESOURCES,
        alternative_resources=module.ALTERNATIVE_RESOURCES,
        bundle_type=module.BUNDLE_TYPE,
    )
    result = ConversionResult(
        analysis=analysis,
        mapping=[MappingRow(**row) for row in built["mapping"]],
        coverage=built["coverage"],
        fhir_bundle=built["bundle"],
        validation=Validation(**validation),
    )
    return result.model_dump()
