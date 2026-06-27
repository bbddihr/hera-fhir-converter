"""결과값/참고치/단위 파싱 + value[x] 분기 + interpretation (검사형 핵심 로직).

- 결과값 형태 분기: 단일 숫자 → valueQuantity / 범위(a~b) → valueRange / 정성 → valueCodeableConcept
- 참고치 파싱: 양방향(a-b)·단방향(>,<,≥,≤)·정성·결측
- 결과값↔참고치 비교 → interpretation H/L/N/A (HL7 v3 ObservationInterpretation)
- UCUM 단위 정규화(ucum_aliases)
"""
from __future__ import annotations

import re

from lxml import etree

UCUM_SYSTEM = "http://unitsofmeasure.org"
INTERP_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"
_INTERP_DISPLAY = {"H": "High", "L": "Low", "N": "Normal", "A": "Abnormal"}

_RANGE_RE = re.compile(r"^\s*([\d.]+)\s*[-~]\s*([\d.]+)\s*$")
_BOUND_RE = re.compile(r"^\s*(<=|>=|<|>|≤|≥)\s*([\d.]+)\s*$")

# 정성 결과 동의어 정규화
_QUAL_SYNONYMS = {
    "음성": "negative", "negative": "negative", "neg": "negative",
    "non-reactive": "negative", "nonreactive": "negative",
    "양성": "positive", "positive": "positive", "pos": "positive",
    "reactive": "positive",
}


def parse_lab_xml(xml: str) -> dict:
    """검사형 EMR XML을 파싱한다.

    Returns:
        {"specimen": str, "items": [{"name", "raw_value", "unit", "reference_range"}, ...]}

    Raises:
        ValueError: well-formed XML이 아닐 때.
    """
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(data)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"well-formed XML이 아닙니다: {exc}") from exc

    specimen = (root.findtext("Specimen") or "Lab Panel").strip()

    items: list[dict] = []
    for test in root.iter("Test"):
        name = (test.findtext("Name") or "").strip()
        if not name:
            continue
        raw_value = (test.findtext("Value") or "").strip()
        unit = (test.findtext("Unit") or "").strip() or None
        ref = (test.findtext("ReferenceRange") or "").strip() or None
        items.append(
            {"name": name, "raw_value": raw_value, "unit": unit, "reference_range": ref}
        )
    return {"specimen": specimen, "items": items}


def to_float(s: str | None) -> float | None:
    """문자열을 float으로, 실패 시 None."""
    try:
        return float(s)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def simple_quantity(value: float, unit: str | None, ucum_aliases: dict | None = None) -> dict:
    """FHIR SimpleQuantity dict — UCUM code는 ucum_aliases로 정규화."""
    q: dict = {"value": value}
    if unit:
        code = (ucum_aliases or {}).get(unit, unit)
        q.update({"unit": unit, "system": UCUM_SYSTEM, "code": code})
    return q


def value_field(raw_value: str, unit: str | None, ucum_aliases: dict | None = None) -> dict:
    """결과값 → FHIR value[x] 필드 (자동 분기)."""
    num = to_float(raw_value)
    if num is not None:
        return {"valueQuantity": simple_quantity(num, unit, ucum_aliases)}

    m = _RANGE_RE.match(raw_value or "")
    if m:
        low = simple_quantity(float(m.group(1)), unit, ucum_aliases)
        high = simple_quantity(float(m.group(2)), unit, ucum_aliases)
        return {"valueRange": {"low": low, "high": high}}

    if raw_value:
        return {"valueCodeableConcept": {"text": raw_value}}
    return {"valueString": ""}


def parse_reference_range(ref: str | None) -> dict | None:
    """참고치 문자열 → 구조화. 결측/해석불가 시 None."""
    if not ref:
        return None
    m = _RANGE_RE.match(ref)
    if m:
        return {"kind": "range", "low": float(m.group(1)), "high": float(m.group(2))}
    m = _BOUND_RE.match(ref)
    if m:
        op = m.group(1).replace("≤", "<=").replace("≥", ">=")
        val = float(m.group(2))
        if op in (">", ">="):  # 정상 범위가 경계 위
            return {"kind": "low_bound", "op": op, "value": val}
        return {"kind": "high_bound", "op": op, "value": val}  # 정상 범위가 경계 아래
    return {"kind": "qualitative", "expected": ref.strip()}


def _norm_qual(s: str) -> str:
    key = s.strip().lower()
    return _QUAL_SYNONYMS.get(key, key)


def interpret(raw_value: str, parsed_ref: dict | None) -> str | None:
    """결과값↔참고치 비교 → interpretation 코드(H/L/N/A) 또는 None."""
    if not parsed_ref:
        return None
    kind = parsed_ref["kind"]

    if kind == "qualitative":
        if not raw_value:
            return None
        return "N" if _norm_qual(raw_value) == _norm_qual(parsed_ref["expected"]) else "A"

    num = to_float(raw_value)
    if num is None:
        return None

    if kind == "range":
        if num < parsed_ref["low"]:
            return "L"
        if num > parsed_ref["high"]:
            return "H"
        return "N"
    if kind == "low_bound":  # 정상 = 경계 초과(이상)
        ok = num >= parsed_ref["value"] if parsed_ref["op"] == ">=" else num > parsed_ref["value"]
        return "N" if ok else "L"
    if kind == "high_bound":  # 정상 = 경계 미만(이하)
        ok = num <= parsed_ref["value"] if parsed_ref["op"] == "<=" else num < parsed_ref["value"]
        return "N" if ok else "H"
    return None


def interpretation_cc(code: str | None) -> dict | None:
    """interpretation 코드 → FHIR CodeableConcept(HL7 v3)."""
    if not code:
        return None
    return {
        "coding": [
            {"system": INTERP_SYSTEM, "code": code, "display": _INTERP_DISPLAY[code]}
        ]
    }
