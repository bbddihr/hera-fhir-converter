"""협의진료의뢰서(consult) — GeneralRecord 파싱 + document Bundle + 매핑 (메인 데모)."""
from __future__ import annotations

from pathlib import Path

from hera import pipeline
from hera.mapper import consult
from hera.mapper.general_record import index, parse_general_record
from hera.validator import validate

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "consult_note.xml"


def _xml() -> str:
    return SAMPLE.read_text(encoding="utf-8")


def test_parse_general_record():
    idx = index(parse_general_record(_xml()))
    assert "의뢰사유" in idx["attrs"]
    assert idx["choices"]["응급 여부"] == "비응급"
    assert idx["choices"]["응급실 협진"] == "Yes"
    assert len(idx["diagnoses"]) == 2
    assert idx["diagnoses"][0]["code"] == "DI015840"


def test_consult_bundle_is_r4_valid():
    result = consult.assemble(_xml())
    assert validate(result["bundle"])["r4_valid"] is True


def test_consult_resource_mix():
    from collections import Counter

    bundle = consult.assemble(_xml())["bundle"]
    assert bundle["type"] == "document"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"
    counts = Counter(e["resource"]["resourceType"] for e in bundle["entry"])
    assert counts["Composition"] == 1
    assert counts["ServiceRequest"] == 1
    assert counts["Condition"] == 2
    assert counts["Encounter"] == 1


def test_consult_coverage_13_of_12():
    cov = consult.assemble(_xml())["coverage"]
    assert cov == {"total": 13, "mapped": 12}


def test_consult_has_inferred_row():
    mapping = consult.assemble(_xml())["mapping"]
    inferred = [r for r in mapping if r["status"] == "inferred"]
    assert len(inferred) == 1
    assert inferred[0]["xml_item"] == "전문의 환자면담"


def test_pipeline_consult_end_to_end():
    # conftest: api_key 차단 → heuristic 폴백으로 consult 판별
    result = pipeline.convert(_xml())
    assert result["analysis"]["doc_kind"] == "consult"
    assert result["analysis"]["primary_resource"] == "Composition"
    assert result["analysis"]["bundle_type"] == "document"
    assert result["validation"]["r4_valid"] is True
    assert result["coverage"]["mapped"] == 12
