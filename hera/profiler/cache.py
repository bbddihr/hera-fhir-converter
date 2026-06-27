"""시그니처 → 분류결과 영속 캐시.

cache hit 시 LLM 호출 없이 form_type/target_task 즉시 반환(결정론·고속).
MVP는 JSON 파일, 필요 시 SQLite로 전환.

Phase 0: 스텁. Phase 3에서 구현.
"""
from __future__ import annotations

# TODO(Phase 3): lookup(signature) -> dict | None ; write(signature, result)
