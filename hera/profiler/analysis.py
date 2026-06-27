"""의미 분석 — Claude Sonnet 4.6로 XML 내용을 읽어 ② 분석 카드 데이터를 생성.

산출(LLM): doc_kind(내부 라우팅) · document_label(서식명) · confidence · rationale(근거 칩).
권장/대안 리소스·필드매핑은 결정론적 조립기(mapper)가 제공한다(②③의 FHIR 구조 = 조립의 진실).

키가 없거나 호출 실패 시 heuristic()으로 구조 기반 폴백.
"""
from __future__ import annotations

import anthropic

from .. import config

DOC_KINDS = ["consult", "lab", "anesthesia", "unknown"]

_LABELS = {
    "consult": "협의진료의뢰서",
    "lab": "진단검사기록",
    "anesthesia": "마취기록",
    "unknown": "미분류 서식",
}

_SYSTEM = (
    "당신은 병원 의무기록 서식 분석기다. 입력으로 EMR 원본 XML이 주어진다. "
    "태그 구조가 아니라 '안의 텍스트 내용(semantic)'을 읽고 어떤 의무기록인지 판단하라.\n"
    "- consult: 협의진료의뢰서/협진 (의뢰사유·회신내용·회신과·회신일시 등 의뢰-회신 구조)\n"
    "- lab: 진단검사기록 (검사 항목·결과값·참고치)\n"
    "- anesthesia: 마취기록 (마취 유도·술중 활력징후·투여 약물)\n"
    "- unknown: 판단 불가\n"
    "rationale에는 그렇게 판단한 근거가 된 핵심 항목명/문구를 짧게 나열하라(칩으로 노출됨). "
    "반드시 analyze_document 도구를 호출해 결과를 반환하라."
)

_TOOL = {
    "name": "analyze_document",
    "description": "의무기록 XML을 의미 기반으로 분석한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "doc_kind": {"type": "string", "enum": DOC_KINDS},
            "document_label": {"type": "string", "description": "한국어 서식명 (예: 협의진료의뢰서)"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {
                "type": "array",
                "items": {"type": "string"},
                "description": "판별 근거가 된 핵심 항목명/문구",
            },
        },
        "required": ["doc_kind", "document_label", "confidence", "rationale"],
    },
}


def analyze(xml: str) -> dict:
    """XML → {doc_kind, document_label, confidence, rationale}. (실제 Claude API 호출)

    Raises:
        RuntimeError: API 키 미설정 또는 분석 실패.
    """
    if not config.api_key_present():
        raise RuntimeError("ANTHROPIC_API_KEY 미설정 — 의미 분석을 호출할 수 없습니다.")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=config.CLASSIFIER_MODEL,
        max_tokens=600,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "analyze_document"},
        messages=[{"role": "user", "content": xml}],
    )
    for block in message.content:
        if block.type == "tool_use" and block.name == "analyze_document":
            d = block.input
            return {
                "doc_kind": str(d["doc_kind"]),
                "document_label": str(d["document_label"]),
                "confidence": float(d["confidence"]),
                "rationale": [str(x) for x in d.get("rationale", [])],
            }
    raise RuntimeError("의미 분석 실패 — 도구 호출 결과를 찾지 못했습니다.")


def heuristic(xml: str) -> dict:
    """구조 기반 폴백 (키 없음/호출 실패 시). confidence=0.0."""
    if "GeneralRecord" in xml or "의뢰사유" in xml or "회신내용" in xml:
        kind, rationale = "consult", ["GeneralRecord 구조", "의뢰/회신 항목"]
    elif "AnesthesiaRecord" in xml or "Vital" in xml:
        kind, rationale = "anesthesia", ["AnesthesiaRecord 구조"]
    elif "LabReport" in xml or "ReferenceRange" in xml:
        kind, rationale = "lab", ["LabReport 구조", "참고치 항목"]
    else:
        kind, rationale = "unknown", ["구조 기반 판단 불가"]
    return {
        "doc_kind": kind,
        "document_label": _LABELS[kind],
        "confidence": 0.0,
        "rationale": rationale,
    }
