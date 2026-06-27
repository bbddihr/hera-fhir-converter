"""lab 매퍼 + validator + 파이프라인 end-to-end 테스트 (데모 시나리오 1)."""
from __future__ import annotations

from pathlib import Path

from hera import pipeline
from hera.mapper import lab
from hera.mapper.value_parser import parse_lab_xml
from hera.validator import validate

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "random_urine.xml"


def _bundle():
    return lab.build_bundle(parse_lab_xml(SAMPLE.read_text(encoding="utf-8")))


def test_bundle_shape():
    bundle = _bundle()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    # DiagnosticReport(1) + Observation(5)
    assert len(bundle["entry"]) == 6
    assert bundle["entry"][0]["resource"]["resourceType"] == "DiagnosticReport"
    obs = [e["resource"] for e in bundle["entry"][1:]]
    assert all(o["resourceType"] == "Observation" for o in obs)
    assert all(o["category"][0]["coding"][0]["code"] == "laboratory" for o in obs)


def test_report_references_all_observations():
    bundle = _bundle()
    report = bundle["entry"][0]["resource"]
    obs_urns = {e["fullUrl"] for e in bundle["entry"][1:]}
    ref_urns = {r["reference"] for r in report["result"]}
    assert ref_urns == obs_urns


def test_bundle_is_r4_valid():
    result = validate(_bundle())
    assert result["r4_valid"] is True
    assert result["errors"] == []


def test_pipeline_end_to_end():
    result = pipeline.convert(SAMPLE.read_text(encoding="utf-8"))
    assert result["analysis"]["doc_kind"] == "lab"
    assert result["validation"]["r4_valid"] is True
    assert result["fhir_bundle"]["type"] == "collection"
    assert "target_role" not in result  # TASK 계약 제거 확인
