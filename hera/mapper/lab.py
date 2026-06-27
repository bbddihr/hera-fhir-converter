"""검사형 매퍼 — Observation(laboratory) + DiagnosticReport 그룹화 → Bundle(collection).

결정론적 조립: LLM이 아니라 코드/룰셋으로 R4 valid Bundle을 만든다(검증 안정성).
참조는 bundle-local urn:uuid(deterministic uuid5)로 연결한다.

Phase 2: 룰셋(LOINC/UCUM) + 참고치 비교 → interpretation(H/L/N) + referenceRange.
"""
from __future__ import annotations

import uuid

from . import ruleset as _ruleset
from .value_parser import (
    interpret,
    interpretation_cc,
    parse_reference_range,
    simple_quantity,
    value_field,
)

_NS = uuid.UUID("12345678-1234-5678-1234-567812345678")
LOINC_SYSTEM = "http://loinc.org"

# 분석 카드(②)용 메타
PRIMARY_RESOURCE = "DiagnosticReport"
PRIMARY_NOTE = "검사 결과를 Observation으로, DiagnosticReport로 그룹화 (collection)"
BUNDLE_TYPE = "collection"
COMPANION_RESOURCES = [{"resource": "Observation", "role": "검사 항목"}]
ALTERNATIVE_RESOURCES: list[dict] = []

OBS_CATEGORY = {
    "coding": [
        {
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "laboratory",
            "display": "Laboratory",
        }
    ]
}
DR_CATEGORY = {
    "coding": [
        {
            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            "code": "LAB",
            "display": "Laboratory",
        }
    ]
}


def _urn(local_id: str) -> str:
    """bundle-local 참조용 deterministic urn:uuid."""
    return "urn:uuid:" + str(uuid.uuid5(_NS, local_id))


def _code(name: str, item_rules: dict) -> dict:
    """검사명 → CodeableConcept. 룰셋에 LOINC가 있으면 coding 추가(선택적 활성화)."""
    loinc = item_rules.get("loinc")
    if loinc:
        return {"coding": [{"system": LOINC_SYSTEM, "code": loinc}], "text": name}
    return {"text": name}


def _reference_range(parsed_ref: dict | None, raw_ref: str | None,
                     unit: str | None, ucum_aliases: dict) -> list | None:
    """참고치 → Observation.referenceRange (범위는 low/high, 그 외는 text)."""
    if parsed_ref and parsed_ref["kind"] == "range":
        return [
            {
                "low": simple_quantity(parsed_ref["low"], unit, ucum_aliases),
                "high": simple_quantity(parsed_ref["high"], unit, ucum_aliases),
            }
        ]
    if raw_ref:
        return [{"text": raw_ref}]
    return None


def _observation(idx: int, item: dict, rs: dict) -> dict:
    name = item["name"]
    unit = item.get("unit")
    ucum_aliases = rs.get("ucum_aliases") or {}
    item_rules = (rs.get("items") or {}).get(name, {}) or {}

    obs = {
        "resourceType": "Observation",
        "id": f"obs-{idx}",
        "status": "final",
        "category": [OBS_CATEGORY],
        "code": _code(name, item_rules),
    }
    obs.update(value_field(item["raw_value"], unit, ucum_aliases))

    parsed_ref = parse_reference_range(item.get("reference_range"))
    cc = interpretation_cc(interpret(item["raw_value"], parsed_ref))
    if cc:
        obs["interpretation"] = [cc]

    ref_range = _reference_range(parsed_ref, item.get("reference_range"), unit, ucum_aliases)
    if ref_range:
        obs["referenceRange"] = ref_range
    return obs


def build_bundle(parsed: dict) -> dict:
    """파싱 결과 → collection Bundle(dict)."""
    rs = _ruleset.load_lab_ruleset()
    specimen = parsed.get("specimen", "Lab Panel")
    items = parsed.get("items", [])

    observations = [_observation(i + 1, item, rs) for i, item in enumerate(items)]
    obs_urns = [_urn(o["id"]) for o in observations]

    report = {
        "resourceType": "DiagnosticReport",
        "id": "report-1",
        "status": "final",
        "category": [DR_CATEGORY],
        "code": {"text": f"{specimen} Panel"},
        "result": [{"reference": urn} for urn in obs_urns],
    }

    entries = [{"fullUrl": _urn("report-1"), "resource": report}]
    entries += [
        {"fullUrl": urn, "resource": obs} for urn, obs in zip(obs_urns, observations)
    ]

    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def assemble(xml: str) -> dict:
    """검사형 XML → {bundle, mapping, coverage}."""
    from .value_parser import parse_lab_xml

    parsed = parse_lab_xml(xml)
    bundle = build_bundle(parsed)

    rows = []
    for item in parsed.get("items", []):
        rows.append(
            {
                "xml_item": item["name"],
                "raw_value": item.get("raw_value", ""),
                "fhir_target": "Observation.value[x] (+ interpretation)",
                "resource_group": "Observation",
                "status": "mapped",
            }
        )
    rows.append(
        {
            "xml_item": parsed.get("specimen", "Panel"),
            "raw_value": f'{len(parsed.get("items", []))} 항목',
            "fhir_target": "DiagnosticReport (그룹화)",
            "resource_group": "DiagnosticReport",
            "status": "mapped",
        }
    )
    return {"bundle": bundle, "mapping": rows, "coverage": {"total": len(rows), "mapped": len(rows)}}


def interpretation_summary(bundle: dict) -> tuple[int, int]:
    """Bundle 내 Observation의 정상/비정상 건수 (N vs H/L/A)."""
    normal = abnormal = 0
    for entry in bundle.get("entry", []):
        res = entry["resource"]
        if res.get("resourceType") != "Observation":
            continue
        interp = res.get("interpretation")
        if not interp:
            continue
        code = interp[0]["coding"][0]["code"]
        if code == "N":
            normal += 1
        else:
            abnormal += 1
    return normal, abnormal
