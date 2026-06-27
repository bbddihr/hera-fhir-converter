"""협의진료의뢰서(consult note) 조립기 — GeneralRecord → FHIR R4 document Bundle.

결정론적 조립: 파싱된 XML 항목을 FHIR 리소스로 매핑해 valid document Bundle을 만들고,
동시에 ③ 프로파일링 매핑 리포트(항목→FHIR요소, 커버리지)를 산출한다.

주 리소스: Composition(LOINC 11488-4 consult note)
동반: ServiceRequest(의뢰) · Condition×N(진단) · Encounter(내원) · Practitioner · PractitionerRole · Patient
"""
from __future__ import annotations

import re
import uuid

from .general_record import index, parse_general_record

_NS = uuid.UUID("12345678-1234-5678-1234-567812345678")
LOINC = "http://loinc.org"
ACTCODE = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
LOCAL_DX = "urn:yuhs:dx"  # 원내 진단코드 체계(데모용 로컬 system)

PRIMARY_RESOURCE = "Composition"
PRIMARY_NOTE = "회신서를 섹션 구조의 임상 문서로 표현 (type: LOINC 11488-4 consult note)"
BUNDLE_TYPE = "document"
COMPANION_RESOURCES = [
    {"resource": "ServiceRequest", "role": "의뢰"},
    {"resource": "Condition", "role": "진단"},
    {"resource": "Encounter", "role": "내원"},
    {"resource": "Practitioner", "role": "기록자/회신과"},
]
ALTERNATIVE_RESOURCES = [
    {
        "resource": "CommunicationRequest + Communication",
        "note": "의뢰-회신을 메시지 교환으로 볼 경우 (inResponseTo가 회신에 적합)",
    }
]


def _urn(local_id: str) -> str:
    return "urn:uuid:" + str(uuid.uuid5(_NS, local_id))


def _iso(dt: str | None) -> str | None:
    m = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})", dt or "")
    return f"{m.group(1)}T{m.group(2)}:{m.group(3)}:00+09:00" if m else None


def _xhtml(text: str) -> dict:
    safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return {
        "status": "generated",
        "div": f'<div xmlns="http://www.w3.org/1999/xhtml">{safe}</div>',
    }


def assemble(xml: str) -> dict:
    """협의진료의뢰서 XML → {bundle, mapping, coverage}."""
    parsed = parse_general_record(xml)
    idx = index(parsed)
    attrs, choices, diagnoses = idx["attrs"], idx["choices"], idx["diagnoses"]

    def aval(name: str) -> str:
        a = attrs.get(name)
        return a["value"] if a else ""

    patient_urn = _urn("patient-1")
    pract_urn = _urn("practitioner-1")
    role_urn = _urn("practrole-1")
    sr_urn = _urn("servicerequest-1")
    enc_urn = _urn("encounter-1")

    reply_dt = _iso(aval("회신일시")) or "2025-01-01T00:00:00+09:00"

    # --- 리소스 조립 ---
    patient = {"resourceType": "Patient", "id": "patient-1"}

    practitioner = {"resourceType": "Practitioner", "id": "practitioner-1"}
    if aval("기록자명") or aval("전문의"):
        practitioner["name"] = [{"text": aval("기록자명") or aval("전문의")}]
    pid = (attrs.get("기록자명") or {}).get("datacode")
    if pid:
        practitioner["identifier"] = [{"value": pid}]

    practrole = {
        "resourceType": "PractitionerRole",
        "id": "practrole-1",
        "practitioner": {"reference": pract_urn},
    }
    if aval("회신과"):
        practrole["specialty"] = [{"text": aval("회신과")}]

    service_request = {
        "resourceType": "ServiceRequest",
        "id": "servicerequest-1",
        "status": "completed",
        "intent": "order",
        "subject": {"reference": patient_urn},
        "priority": "routine" if choices.get("응급 여부") == "비응급" else "urgent",
    }
    if aval("의뢰사유"):
        service_request["reasonCode"] = [{"text": aval("의뢰사유")}]
    service_request["performer"] = [{"reference": role_urn}]

    conditions = []
    for i, dx in enumerate(diagnoses, start=1):
        conditions.append(
            {
                "resourceType": "Condition",
                "id": f"condition-{i}",
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ]
                },
                "code": {
                    "coding": [{"system": LOCAL_DX, "code": dx["code"]}] if dx.get("code") else [],
                    "text": dx["text"],
                },
                "subject": {"reference": patient_urn},
            }
        )

    encounter = {
        "resourceType": "Encounter",
        "id": "encounter-1",
        "status": "finished",
        "class": {"system": ACTCODE, "code": "EMER", "display": "emergency"}
        if choices.get("응급실 협진") == "Yes"
        else {"system": ACTCODE, "code": "AMB", "display": "ambulatory"},
        "subject": {"reference": patient_urn},
    }
    if _iso(aval("진료시간")):
        encounter["period"] = {"start": _iso(aval("진료시간"))}

    sections = [
        {
            "title": "의뢰",
            "text": _xhtml(aval("의뢰사유")),
            "entry": [{"reference": sr_urn}],
        },
        {"title": "회신", "text": _xhtml(aval("회신내용"))},
    ]
    if conditions:
        sections.append(
            {
                "title": "진단",
                "entry": [{"reference": _urn(c["id"])} for c in conditions],
            }
        )

    composition = {
        "resourceType": "Composition",
        "id": "composition-1",
        "status": "final",
        "type": {
            "coding": [{"system": LOINC, "code": "11488-4", "display": "Consult note"}],
            "text": "협의진료의뢰서",
        },
        "subject": {"reference": patient_urn},
        "date": reply_dt,
        "author": [{"reference": pract_urn}],
        "title": "협의진료의뢰서",
        "section": sections,
    }

    resources = [
        composition,
        patient,
        service_request,
        *conditions,
        encounter,
        practitioner,
        practrole,
    ]
    entries = [{"fullUrl": _urn(r["id"]), "resource": r} for r in resources]

    bundle = {
        "resourceType": "Bundle",
        "type": BUNDLE_TYPE,
        "identifier": {"system": "urn:hera:bundle", "value": _urn("composition-1")},
        "timestamp": reply_dt,
        "entry": entries,
    }

    mapping, coverage = _mapping_report(attrs, choices, diagnoses)
    return {"bundle": bundle, "mapping": mapping, "coverage": coverage}


def _row(xml_item, raw_value, fhir_target, group, status="mapped") -> dict:
    return {
        "xml_item": xml_item,
        "raw_value": raw_value,
        "fhir_target": fhir_target,
        "resource_group": group,
        "status": status,
    }


def _mapping_report(attrs: dict, choices: dict, diagnoses: list) -> tuple[list, dict]:
    """③ 프로파일링 매핑 리포트 — 실제 조립한 매핑을 정직하게 기록."""

    def aval(name):
        a = attrs.get(name)
        return a["value"] if a else ""

    rows = [
        _row("의뢰사유", aval("의뢰사유"), "Composition.section[의뢰].text + ServiceRequest.reasonCode", "Composition"),
        _row("회신내용", aval("회신내용"), "Composition.section[회신].text", "Composition"),
        _row("회신일시", aval("회신일시"), "Composition.date", "Composition"),
        _row("기록자명", aval("기록자명"), "Composition.author → Practitioner", "Composition"),
        _row("응급 여부", choices.get("응급 여부", ""), "ServiceRequest.priority = routine", "ServiceRequest"),
        _row("회신과", aval("회신과"), "ServiceRequest.performer → PractitionerRole.specialty", "ServiceRequest"),
        _row("진료시간", aval("진료시간"), "Encounter.period.start", "Encounter"),
        _row("응급실 협진", choices.get("응급실 협진", ""), "Encounter.class = EMER", "Encounter"),
        _row("전문의", aval("전문의"), "Practitioner", "Practitioner"),
        _row("협진주치의", aval("협진주치의"), "PractitionerRole", "Practitioner"),
    ]
    for dx in diagnoses:
        rows.append(
            _row("진단: " + dx["text"], dx.get("code", ""), "Condition.code", "Condition")
        )
    # 매핑 불확실 — 정직하게 '추론 필요'로 표시
    rows.append(
        _row("전문의 환자면담", choices.get("전문의 환자면담", ""), "Encounter.participant", "Encounter", status="inferred")
    )

    total = len(rows)
    mapped = sum(1 for r in rows if r["status"] == "mapped")
    return rows, {"total": total, "mapped": mapped}
