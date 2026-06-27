"""FHIR R4 invariant 검증 — `fhir.resources`(Pydantic) 기반.

Bundle dict를 R4 모델로 검증해 {r4_valid, invariants, errors}를 반환한다.
실패 시 errors를 채워 UI 배지/로그와 연동한다.
"""
from __future__ import annotations

from fhir.resources.bundle import Bundle
from pydantic import ValidationError


def validate(bundle: dict) -> dict:
    """collection/document Bundle dict의 R4 유효성 검증.

    Returns:
        {"r4_valid": bool, "invariants": str, "errors": list[str]}
    """
    try:
        Bundle.model_validate(bundle)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        ]
        return {"r4_valid": False, "invariants": f"0/{_count(bundle)}", "errors": errors}

    n = _count(bundle)
    return {"r4_valid": True, "invariants": f"{n}/{n} resources R4-valid", "errors": []}


def _count(bundle: dict) -> int:
    return len(bundle.get("entry", []))
