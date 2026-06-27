"""Router — doc_kind를 적절한 조립기(mapper 모듈)로 디스패치한다.

각 조립기 모듈은 동일 인터페이스를 노출한다:
    assemble(xml) -> {bundle, mapping, coverage}
    PRIMARY_RESOURCE / PRIMARY_NOTE / BUNDLE_TYPE / COMPANION_RESOURCES / ALTERNATIVE_RESOURCES

새 서식 추가 = 새 조립기 모듈 + 레지스트리 한 줄.
"""
from __future__ import annotations

from types import ModuleType

from . import consult, lab, narrative

REGISTRY: dict[str, ModuleType] = {
    "consult": consult,
    "lab": lab,
    "anesthesia": narrative,
}


def get_assembler(doc_kind: str) -> ModuleType:
    """doc_kind → 조립기 모듈. 미지/미등록은 lab(검사형)으로 폴백."""
    return REGISTRY.get(doc_kind, lab)
