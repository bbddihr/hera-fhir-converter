"""서사형 매퍼 — Composition(문서 골격) 중심 → Bundle(document).

마취: Composition + Procedure + Observation(術中 vitals) + MedicationAdministration.
본문 섹션을 의미 단위로 분할해 Composition.section에 매핑.

Phase 0: 스텁. Phase 4에서 구현.
"""
from __future__ import annotations

# TODO(Phase 4): build(parsed, form_type) -> Bundle(document) dict
