"""FHIR R4 invariant 검증 — `fhir.resources`(Pydantic) 기반.

모든 출력 Bundle은 검증을 통과해야 계약 객체의 validation.r4_valid=true가 된다.
실패 시 errors 목록을 채워 UI 배지와 연동한다.

Phase 0: 스텁. Phase 1에서 구현.
"""
from __future__ import annotations

# TODO(Phase 1): validate(bundle_dict) -> {r4_valid, invariants, errors}
