"""Profiler — signature/cache/analyze (실제 API 호출 없이 monkeypatch)."""
from __future__ import annotations

import pytest

from hera import config, pipeline
from hera.profiler import analysis, cache, signature

XML_A = "<LabReport><Specimen>Urine</Specimen><Test><Name>pH</Name><Value>6.0</Value><ReferenceRange>4.5-8.0</ReferenceRange></Test></LabReport>"
# 같은 구조, 값만 다름
XML_A2 = "<LabReport><Specimen>Blood</Specimen><Test><Name>WBC</Name><Value>12.5</Value><ReferenceRange>4-10</ReferenceRange></Test></LabReport>"
# 다른 구조
XML_B = "<AnesthesiaRecord><Vital><HeartRate>72</HeartRate></Vital></AnesthesiaRecord>"


def test_signature_ignores_values():
    assert signature.signature(XML_A) == signature.signature(XML_A2)


def test_signature_distinguishes_structure():
    assert signature.signature(XML_A) != signature.signature(XML_B)


def test_signature_rejects_malformed():
    with pytest.raises(ValueError):
        signature.signature("<a><b></a>")


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "c.json")
    assert cache.lookup("sig1") is None
    cache.write("sig1", {"doc_kind": "lab"})
    assert cache.lookup("sig1") == {"doc_kind": "lab"}


def test_analyze_cache_hit_skips_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "c.json")
    sig = signature.signature(XML_A)
    cache.write(sig, {"doc_kind": "lab", "document_label": "진단검사기록", "confidence": 0.88, "rationale": []})

    def _boom(_xml):
        raise AssertionError("cache hit인데 LLM이 호출됨")

    monkeypatch.setattr(analysis, "analyze", _boom)
    result = pipeline.analyze(XML_A)
    assert result["via"] == "cache"
    assert result["doc_kind"] == "lab"


def test_analyze_semantic_then_writes_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(config, "api_key_present", lambda: True)
    monkeypatch.setattr(
        analysis,
        "analyze",
        lambda _xml: {"doc_kind": "consult", "document_label": "협의진료의뢰서", "confidence": 0.96, "rationale": ["의뢰사유"]},
    )
    result = pipeline.analyze(XML_B)
    assert result["doc_kind"] == "consult"
    assert result["via"] == "semantic"
    assert cache.lookup(signature.signature(XML_B))["doc_kind"] == "consult"


def test_analyze_fallback_without_key_uses_heuristic(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(config, "api_key_present", lambda: False)
    result = pipeline.analyze(XML_A)
    assert result["via"] == "fallback"
    assert result["doc_kind"] == "lab"  # 구조 기반 폴백
