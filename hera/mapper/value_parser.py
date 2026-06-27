"""결과값/참고치/단위 파싱 + value[x] 분기 (검사형의 핵심 로직).

Phase 1: 원본 XML → 검체명 + 검사 항목 리스트 파싱, 단일 숫자 → valueQuantity.
Phase 2(예정): valueRange / 정성 분기, 참고치 비교 → interpretation(H/L/N), UCUM 매핑.
"""
from __future__ import annotations

from lxml import etree

UCUM_SYSTEM = "http://unitsofmeasure.org"


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


def value_field(raw_value: str, unit: str | None) -> dict:
    """결과값 → FHIR value[x] 필드.

    Phase 1: 단일 숫자 → valueQuantity, 그 외 → valueString(폴백, Phase 2에서 정식 분기).
    """
    num = to_float(raw_value)
    if num is not None:
        quantity: dict = {"value": num}
        if unit:
            quantity.update({"unit": unit, "system": UCUM_SYSTEM, "code": unit})
        return {"valueQuantity": quantity}
    return {"valueString": raw_value}
