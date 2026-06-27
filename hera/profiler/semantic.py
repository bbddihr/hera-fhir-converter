"""의미 분류 — Claude Sonnet 4.6로 XML 텍스트 내용 기반 form_type 판별.

구조가 아닌 내용(semantic)을 읽어 어떤 서식인지 분류한다. structured output(tool use)으로
스키마를 강제해 파싱 안정성을 확보한다. 산출: form_type, confidence (+ target_task/role).

Phase 0: 스텁. Phase 3에서 구현.
"""
from __future__ import annotations

# TODO(Phase 3): classify(xml) -> {form_type, confidence}
