"""Router — form_type을 적절한 mapper로 디스패치한다.

    검사형 (lab / unknown / fallback) → mapper.lab        (collection)
    서사형 (anesthesia/외래/응급)      → mapper.narrative  (document)

새 서식 추가 = 라우팅 룰 추가.
"""
from __future__ import annotations

from . import lab, narrative
from .value_parser import parse_lab_xml

NARRATIVE_FORMS = {"anesthesia_record", "outpatient_first", "emergency_record"}


def route(form_type: str, xml: str) -> dict:
    """form_type에 따라 FHIR Bundle(dict)을 조립한다."""
    if form_type in NARRATIVE_FORMS:
        return narrative.build_bundle(xml, form_type)
    # 검사형 기본 경로 (lab / unknown / fallback)
    return lab.build_bundle(parse_lab_xml(xml))
