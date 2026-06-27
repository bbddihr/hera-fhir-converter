"""Phase 0 스모크 테스트 — 패키지가 import 가능하고 스켈레톤이 살아있는지 확인."""
from __future__ import annotations

import pytest


def test_package_imports():
    import hera
    from hera import config, contract, pipeline, tasks, validator  # noqa: F401
    from hera.mapper import lab, narrative, router, value_parser  # noqa: F401
    from hera.profiler import cache, semantic, signature  # noqa: F401

    assert hera.__version__ == "0.0.0"


def test_convert_is_stub():
    from hera import pipeline

    with pytest.raises(NotImplementedError):
        pipeline.convert("<x/>")


def test_config_defaults():
    from hera import config

    assert config.CLASSIFIER_MODEL  # 기본값 claude-sonnet-4-6
    assert 0.0 <= config.CONFIDENCE_THRESHOLD <= 1.0
