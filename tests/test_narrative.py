"""Phase 4 — 서사형 라우팅(마취 → Composition document) + R4 검증 (시나리오 4)."""
from __future__ import annotations

from pathlib import Path

from hera.mapper import narrative, router
from hera.validator import validate

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "anesthesia_record.xml"


def _xml() -> str:
    return SAMPLE.read_text(encoding="utf-8")


def _bundle() -> dict:
    return narrative.build_bundle(_xml())


def test_parse_anesthesia():
    parsed = narrative.parse_anesthesia_xml(_xml())
    assert parsed["operation"]["anesthesia_type"] == "전신마취"
    assert len(parsed["vitals"]) == 3
    assert len(parsed["medications"]) == 2


def test_document_bundle_shape():
    bundle = _bundle()
    assert bundle["type"] == "document"
    # 문서 Bundle 필수: identifier + timestamp + 첫 리소스 = Composition
    assert "identifier" in bundle and bundle["identifier"]["value"]
    assert "timestamp" in bundle
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"


def test_resource_mix():
    types = [e["resource"]["resourceType"] for e in _bundle()["entry"]]
    assert types.count("Composition") == 1
    assert types.count("Patient") == 1
    assert types.count("Procedure") == 1
    assert types.count("Observation") == 6  # 3 timepoints × 2 vitals
    assert types.count("MedicationAdministration") == 2


def test_composition_sections_reference_resources():
    comp = _bundle()["entry"][0]["resource"]
    titles = [s["title"] for s in comp["section"]]
    assert titles == ["마취 정보", "술중 활력징후", "투여 약물"]
    # 활력징후 섹션은 6개 Observation을 참조
    vitals_section = comp["section"][1]
    assert len(vitals_section["entry"]) == 6


def test_document_bundle_is_r4_valid():
    result = validate(_bundle())
    assert result["r4_valid"] is True, result["errors"]


def test_router_dispatches_by_form_type():
    # 서사형 → document, 검사형 → collection
    assert router.route("anesthesia_record", _xml())["type"] == "document"

    lab_xml = (
        SAMPLE.parent / "random_urine.xml"
    ).read_text(encoding="utf-8")
    assert router.route("lab", lab_xml)["type"] == "collection"
