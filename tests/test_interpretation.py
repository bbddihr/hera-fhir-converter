"""Phase 2 — 참고치 파싱·interpretation·정성/범위 분기 + CBC end-to-end (시나리오 2·3)."""
from __future__ import annotations

from pathlib import Path

from hera import pipeline
from hera.mapper import lab
from hera.mapper.value_parser import (
    interpret,
    parse_reference_range,
    value_field,
)

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "cbc_chemistry.xml"


# --- 참고치 파싱 ---
def test_parse_range():
    assert parse_reference_range("4.0-10.0") == {"kind": "range", "low": 4.0, "high": 10.0}


def test_parse_bounds():
    assert parse_reference_range("<40") == {"kind": "high_bound", "op": "<", "value": 40.0}
    assert parse_reference_range(">=60") == {"kind": "low_bound", "op": ">=", "value": 60.0}


def test_parse_qualitative_and_missing():
    assert parse_reference_range("Negative") == {"kind": "qualitative", "expected": "Negative"}
    assert parse_reference_range(None) is None


# --- interpretation ---
def test_interpret_high_low_normal():
    rng = {"kind": "range", "low": 4.0, "high": 10.0}
    assert interpret("12.5", rng) == "H"
    assert interpret("3.0", rng) == "L"
    assert interpret("7.0", rng) == "N"


def test_interpret_bounds():
    assert interpret("28", {"kind": "high_bound", "op": "<", "value": 40.0}) == "N"
    assert interpret("55", {"kind": "high_bound", "op": "<", "value": 40.0}) == "H"
    assert interpret("70", {"kind": "low_bound", "op": ">=", "value": 60.0}) == "N"
    assert interpret("50", {"kind": "low_bound", "op": ">=", "value": 60.0}) == "L"


def test_interpret_qualitative():
    qref = {"kind": "qualitative", "expected": "Negative"}
    assert interpret("Negative", qref) == "N"
    assert interpret("음성", qref) == "N"  # 동의어 정규화
    assert interpret("Positive", qref) == "A"


# --- value[x] 분기 ---
def test_value_range_branch():
    field = value_field("5-10", "mg/dL")
    assert field["valueRange"]["low"]["value"] == 5.0
    assert field["valueRange"]["high"]["value"] == 10.0


def test_value_qualitative_branch():
    assert value_field("Negative", None) == {"valueCodeableConcept": {"text": "Negative"}}


def test_ucum_alias_applied():
    field = value_field("12.5", "10^3/uL", {"10^3/uL": "10*3/uL"})
    assert field["valueQuantity"]["code"] == "10*3/uL"  # UCUM 정규화
    assert field["valueQuantity"]["unit"] == "10^3/uL"  # 원본 표기 보존


# --- CBC end-to-end ---
def _cbc_bundle():
    from hera.mapper.value_parser import parse_lab_xml

    return lab.build_bundle(parse_lab_xml(SAMPLE.read_text(encoding="utf-8")))


def test_cbc_abnormal_count():
    normal, abnormal = lab.interpretation_summary(_cbc_bundle())
    assert (normal, abnormal) == (9, 3)  # 시나리오 3: 12개 중 비정상 3건


def test_cbc_specific_interpretations():
    bundle = _cbc_bundle()
    by_name = {
        e["resource"]["code"]["text"]: e["resource"]
        for e in bundle["entry"]
        if e["resource"]["resourceType"] == "Observation"
    }
    assert by_name["WBC"]["interpretation"][0]["coding"][0]["code"] == "H"
    assert by_name["Platelet"]["interpretation"][0]["coding"][0]["code"] == "L"
    assert by_name["Glucose"]["interpretation"][0]["coding"][0]["code"] == "H"
    # 정성 항목: valueCodeableConcept + N
    assert by_name["HBsAg"]["valueCodeableConcept"]["text"] == "Negative"
    assert by_name["HBsAg"]["interpretation"][0]["coding"][0]["code"] == "N"


def test_cbc_loinc_activated_from_ruleset():
    bundle = _cbc_bundle()
    hgb = next(
        e["resource"]
        for e in bundle["entry"]
        if e["resource"].get("code", {}).get("text") == "Hemoglobin"
    )
    coding = hgb["code"]["coding"][0]
    assert coding["system"] == "http://loinc.org"
    assert coding["code"] == "718-7"


def test_cbc_pipeline_r4_valid():
    result = pipeline.convert(SAMPLE.read_text(encoding="utf-8"))
    assert result["analysis"]["doc_kind"] == "lab"
    assert result["validation"]["r4_valid"] is True
