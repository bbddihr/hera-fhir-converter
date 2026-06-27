"""구조 시그니처 해시 — 반복 입력 가속용 캐시 키.

XML 트리 구조를 정규화(태그 경로 집합 기준, 텍스트값·속성순서·공백 무시)해
안정적 해시를 만든다. 동일 구조 반복 시 LLM 분류를 건너뛴다.

Phase 0: 스텁. Phase 3에서 구현.
"""
from __future__ import annotations

# TODO(Phase 3): signature(xml) -> str(hash)
