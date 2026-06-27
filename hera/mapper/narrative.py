"""서사형 매퍼 — Composition(문서 골격) 중심 → Bundle(document).

마취: Composition + Patient + Procedure + Observation(術中 vitals) + MedicationAdministration.
본문을 의미 단위 섹션으로 분할해 Composition.section.entry로 연결한다.

결정론적 조립(LLM 아님). bundle-local urn:uuid(deterministic uuid5)로 참조 연결.
"""
from __future__ import annotations

import uuid

from lxml import etree

from . import ruleset as _ruleset
from .value_parser import UCUM_SYSTEM, simple_quantity

_NS = uuid.UUID("12345678-1234-5678-1234-567812345678")
LOINC_SYSTEM = "http://loinc.org"

# 활력징후 → (LOINC, UCUM 단위)
_VITALS = {
    "HeartRate": {"display": "Heart rate", "loinc": "8867-4", "unit": "/min"},
    "SpO2": {"display": "Oxygen saturation", "loinc": "59408-5", "unit": "%"},
}


def _urn(local_id: str) -> str:
    return "urn:uuid:" + str(uuid.uuid5(_NS, local_id))


def _text(node, tag: str) -> str | None:
    val = node.findtext(tag)
    return val.strip() if val and val.strip() else None


def parse_anesthesia_xml(xml: str) -> dict:
    """마취기록 XML 파싱.

    Raises:
        ValueError: well-formed XML이 아닐 때.
    """
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(data)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"well-formed XML이 아닙니다: {exc}") from exc

    patient_el = root.find("Patient")
    patient = {
        "name": _text(patient_el, "Name") if patient_el is not None else None,
        "id": _text(patient_el, "ID") if patient_el is not None else None,
    }

    op_el = root.find("Operation")
    operation = {
        "procedure_name": _text(op_el, "ProcedureName") if op_el is not None else None,
        "anesthesia_type": _text(op_el, "AnesthesiaType") if op_el is not None else None,
        "start": _text(op_el, "StartTime") if op_el is not None else None,
        "end": _text(op_el, "EndTime") if op_el is not None else None,
    }

    vitals = []
    for v in root.iter("Vital"):
        vitals.append(
            {
                "time": _text(v, "Time"),
                "HeartRate": _text(v, "HeartRate"),
                "SpO2": _text(v, "SpO2"),
            }
        )

    meds = []
    for m in root.iter("Medication"):
        meds.append(
            {
                "name": _text(m, "Name"),
                "dose": _text(m, "Dose"),
                "unit": _text(m, "Unit"),
                "route": _text(m, "Route"),
                "time": _text(m, "Time"),
            }
        )

    return {"patient": patient, "operation": operation, "vitals": vitals, "medications": meds}


def _patient(parsed: dict) -> dict:
    p = parsed["patient"]
    res = {"resourceType": "Patient", "id": "patient-1"}
    if p.get("name"):
        res["name"] = [{"text": p["name"]}]
    if p.get("id"):
        res["identifier"] = [{"value": p["id"]}]
    return res


def _procedure(parsed: dict, subject_urn: str) -> dict:
    op = parsed["operation"]
    res = {
        "resourceType": "Procedure",
        "id": "procedure-1",
        "status": "completed",
        "code": {"text": op.get("anesthesia_type") or "마취"},
        "subject": {"reference": subject_urn},
    }
    if op.get("start") or op.get("end"):
        period = {}
        if op.get("start"):
            period["start"] = op["start"]
        if op.get("end"):
            period["end"] = op["end"]
        res["performedPeriod"] = period
    return res


def _vital_observations(parsed: dict, subject_urn: str) -> list[dict]:
    obs = []
    idx = 0
    for v in parsed["vitals"]:
        for key, meta in _VITALS.items():
            raw = v.get(key)
            if raw is None:
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            idx += 1
            o = {
                "resourceType": "Observation",
                "id": f"vital-{idx}",
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "vital-signs",
                                "display": "Vital Signs",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [{"system": LOINC_SYSTEM, "code": meta["loinc"]}],
                    "text": meta["display"],
                },
                "subject": {"reference": subject_urn},
                "valueQuantity": simple_quantity(value, meta["unit"]),
            }
            if v.get("time"):
                o["effectiveDateTime"] = v["time"]
            obs.append(o)
    return obs


def _medications(parsed: dict, subject_urn: str) -> list[dict]:
    meds = []
    for i, m in enumerate(parsed["medications"], start=1):
        res = {
            "resourceType": "MedicationAdministration",
            "id": f"med-{i}",
            "status": "completed",
            "medicationCodeableConcept": {"text": m.get("name") or "약물"},
            "subject": {"reference": subject_urn},
            "effectiveDateTime": m.get("time") or parsed["operation"].get("start"),
        }
        dose_val = m.get("dose")
        if dose_val:
            try:
                res["dosage"] = {
                    "dose": simple_quantity(float(dose_val), m.get("unit")),
                }
                if m.get("route"):
                    res["dosage"]["route"] = {"text": m["route"]}
            except ValueError:
                pass
        meds.append(res)
    return meds


def build_bundle(xml: str, form_type: str = "anesthesia_record") -> dict:
    """마취기록 XML → document Bundle(dict)."""
    rs = _ruleset.load_anesthesia_ruleset()
    comp_rules = rs.get("composition", {})
    parsed = parse_anesthesia_xml(xml)

    patient = _patient(parsed)
    patient_urn = _urn(patient["id"])

    procedure = _procedure(parsed, patient_urn)
    vitals = _vital_observations(parsed, patient_urn)
    meds = _medications(parsed, patient_urn)

    # 섹션별 entry 참조
    section_entries = {
        "procedure": [_urn(procedure["id"])],
        "vitals": [_urn(o["id"]) for o in vitals],
        "medications": [_urn(m["id"]) for m in meds],
    }
    sections = []
    for s in comp_rules.get("sections", []):
        refs = section_entries.get(s["key"], [])
        if not refs:
            continue
        sections.append(
            {"title": s["title"], "entry": [{"reference": r} for r in refs]}
        )

    composition = {
        "resourceType": "Composition",
        "id": "composition-1",
        "status": "final",
        "type": _composition_type(comp_rules),
        "date": parsed["operation"].get("start") or "2026-01-01T00:00:00+09:00",
        "author": [{"display": "마취과 전문의"}],
        "title": comp_rules.get("title", "마취기록"),
        "subject": {"reference": patient_urn},
        "section": sections,
    }

    # entry 순서: Composition(첫 번째 필수) → 나머지
    resources = [composition, patient, procedure, *vitals, *meds]
    entries = [{"fullUrl": _urn(r["id"]), "resource": r} for r in resources]

    return {
        "resourceType": "Bundle",
        "type": "document",
        "identifier": {"system": "urn:hera:bundle", "value": _urn("composition-1")},
        "timestamp": composition["date"],
        "entry": entries,
    }


def _composition_type(comp_rules: dict) -> dict:
    t = comp_rules.get("type")
    if t:
        return {
            "coding": [
                {"system": t["system"], "code": t["code"], "display": t.get("display")}
            ],
            "text": t.get("display"),
        }
    return {"text": "임상 문서"}
