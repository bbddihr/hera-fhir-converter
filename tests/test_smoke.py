"""스모크 테스트 — 패키지 import + 기본 동작."""
from __future__ import annotations

import pytest


def test_package_imports():
    import hera
    from hera import config, contract, pipeline, validator  # noqa: F401
    from hera.mapper import (  # noqa: F401
        consult,
        general_record,
        lab,
        narrative,
        router,
        value_parser,
    )
    from hera.profiler import analysis, cache, signature  # noqa: F401

    assert hera.__version__ == "0.0.0"


def test_convert_rejects_malformed_xml():
    from hera import pipeline

    with pytest.raises(ValueError):
        pipeline.convert("<LabReport><unclosed>")


def test_config_defaults():
    from hera import config

    assert config.CLASSIFIER_MODEL  # 기본값 claude-sonnet-4-6
    assert 0.0 <= config.CONFIDENCE_THRESHOLD <= 1.0
