"""value_parser 단위 테스트 — 파싱·value[x] 분기."""
from __future__ import annotations

from pathlib import Path

import pytest

from hera.mapper.value_parser import parse_lab_xml, value_field

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "random_urine.xml"


def test_parse_random_urine():
    parsed = parse_lab_xml(SAMPLE.read_text(encoding="utf-8"))
    assert parsed["specimen"] == "Random Urine"
    assert len(parsed["items"]) == 5
    names = [i["name"] for i in parsed["items"]]
    assert "Specific Gravity" in names and "pH" in names


def test_value_field_numeric_with_unit():
    field = value_field("120", "mg/dL")
    assert field["valueQuantity"]["value"] == 120.0
    assert field["valueQuantity"]["code"] == "mg/dL"
    assert field["valueQuantity"]["system"] == "http://unitsofmeasure.org"


def test_value_field_numeric_no_unit():
    field = value_field("6.0", None)
    assert field["valueQuantity"] == {"value": 6.0}


def test_value_field_non_numeric_falls_back_to_string():
    field = value_field("Negative", None)
    assert field == {"valueString": "Negative"}


def test_malformed_xml_raises():
    with pytest.raises(ValueError):
        parse_lab_xml("<LabReport><unclosed>")
