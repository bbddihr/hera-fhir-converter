"""Phase 3 — signature/cache/profile (실제 API 호출 없이 monkeypatch)."""
from __future__ import annotations

import pytest

from hera import config, pipeline
from hera.profiler import cache, signature
from hera.profiler import semantic

XML_A = "<LabReport><Specimen>Urine</Specimen><Test><Name>pH</Name><Value>6.0</Value></Test></LabReport>"
# 같은 구조, 값만 다름
XML_A2 = "<LabReport><Specimen>Blood</Specimen><Test><Name>WBC</Name><Value>12.5</Value></Test></LabReport>"
# 다른 구조
XML_B = "<AnesthesiaRecord><Procedure>전신마취</Procedure></AnesthesiaRecord>"


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
    cache.write("sig1", {"form_type": "lab", "confidence": 0.9})
    assert cache.lookup("sig1") == {"form_type": "lab", "confidence": 0.9}


def test_profile_cache_hit_skips_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "c.json")
    sig = signature.signature(XML_A)
    cache.write(sig, {"form_type": "lab", "confidence": 0.88})

    # semantic이 호출되면 실패 — cache hit이면 호출 안 됨
    def _boom(_xml):
        raise AssertionError("cache hit인데 LLM이 호출됨")

    monkeypatch.setattr(semantic, "classify", _boom)

    result = pipeline.profile(XML_A)
    assert result == {"form_type": "lab", "confidence": 0.88, "via": "cache"}


def test_profile_semantic_then_writes_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(config, "api_key_present", lambda: True)
    monkeypatch.setattr(
        semantic, "classify", lambda _xml: {"form_type": "anesthesia_record", "confidence": 0.95}
    )

    result = pipeline.profile(XML_B)
    assert result["form_type"] == "anesthesia_record"
    assert result["via"] == "semantic"
    # 캐시에 적재되어 다음엔 cache hit
    assert cache.lookup(signature.signature(XML_B)) == {
        "form_type": "anesthesia_record",
        "confidence": 0.95,
    }


def test_profile_fallback_without_key(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(config, "api_key_present", lambda: False)
    result = pipeline.profile(XML_A)
    assert result == {"form_type": "lab", "confidence": 0.0, "via": "fallback"}


def test_profile_semantic_failure_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(config, "api_key_present", lambda: True)

    def _fail(_xml):
        raise RuntimeError("API 오류")

    monkeypatch.setattr(semantic, "classify", _fail)
    result = pipeline.profile(XML_A)
    assert result["via"] == "fallback"
