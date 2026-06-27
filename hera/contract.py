"""변환 결과 모델 — Hera 컨버터의 출력.

컨버터의 책임은 FHIR 변환 + R4 검증까지다. (다운스트림 TASK/역할 결정은 별도 시스템 일)
출력은 사람이 읽는 ② 분석 · ③ 매핑 · ④ 변환 결과(bundle+validation)로 구성된다.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Analysis(BaseModel):
    """② 분석 결과 — 판별 결론 + 근거 + 권장 리소스."""

    doc_kind: str  # 내부 라우팅 키 (출력 표시는 document_label)
    document_label: str  # 판별된 서식명 (예: 협의진료의뢰서)
    confidence: float
    via: str  # semantic | cache | fallback
    rationale: list[str] = Field(default_factory=list)  # 판별 근거 칩
    primary_resource: str  # 주 FHIR 리소스 (예: Composition)
    primary_note: str | None = None
    companion_resources: list[dict] = Field(default_factory=list)  # 동반 리소스
    alternative_resources: list[dict] = Field(default_factory=list)  # 대안
    bundle_type: str  # collection | document


class MappingRow(BaseModel):
    """③ 프로파일링 매핑 한 줄 — XML 항목 → FHIR 요소."""

    xml_item: str
    raw_value: str
    fhir_target: str
    resource_group: str
    status: str  # mapped | inferred | unmapped


class Validation(BaseModel):
    r4_valid: bool
    invariants: str
    errors: list[str] = Field(default_factory=list)


class ConversionResult(BaseModel):
    analysis: Analysis
    mapping: list[MappingRow] = Field(default_factory=list)
    coverage: dict = Field(default_factory=dict)  # {total, mapped}
    fhir_bundle: dict = Field(default_factory=dict)
    validation: Validation
