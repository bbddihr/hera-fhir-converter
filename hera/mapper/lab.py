"""검사형 매퍼 — Observation(laboratory) + DiagnosticReport 그룹화 → Bundle(collection).

결정론적 조립: LLM이 아니라 코드/룰셋으로 R4 valid Bundle을 만든다(검증 안정성).
참조는 bundle-local urn:uuid(deterministic uuid5)로 연결한다.

Phase 1: 단일 숫자 valueQuantity 중심. Phase 2에서 interpretation/UCUM 정식화.
"""
from __future__ import annotations

import uuid

from .value_parser import value_field

_NS = uuid.UUID("12345678-1234-5678-1234-567812345678")

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


def _observation(idx: int, item: dict) -> dict:
    obs = {
        "resourceType": "Observation",
        "id": f"obs-{idx}",
        "status": "final",
        "category": [OBS_CATEGORY],
        "code": {"text": item["name"]},  # MVP: local text. LOINC 매핑은 로드맵.
    }
    obs.update(value_field(item["raw_value"], item.get("unit")))
    return obs


def build_bundle(parsed: dict) -> dict:
    """파싱 결과 → collection Bundle(dict)."""
    specimen = parsed.get("specimen", "Lab Panel")
    items = parsed.get("items", [])

    observations = [_observation(i + 1, item) for i, item in enumerate(items)]
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
