"""결과값/참고치/단위 파싱 + interpretation 부여 (검사형의 핵심 로직).

- 결과값 형태 분기: 단일 숫자 → valueQuantity / 범위 → valueRange / 정성 → valueCodeableConcept·valueString
- 참고치 파싱: 양방향·단방향·정성·결측
- 결과값↔참고치 비교 → interpretation H/L/N (HL7 v3)
- UCUM 단위 매핑

Phase 0: 스텁. Phase 1(단일 숫자)~Phase 2(전체)에서 구현.
"""
from __future__ import annotations

# TODO(Phase 1): 단일 숫자 → valueQuantity
# TODO(Phase 2): valueRange / 정성 분기, 참고치 비교, interpretation, UCUM
