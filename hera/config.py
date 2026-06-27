"""환경설정 로딩 — API 키, 분류 모델 ID, 신뢰도 임계값.

`.env`(프로젝트 루트)를 로드한다. 비밀키는 저장소에 커밋하지 않는다(.gitignore).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # 루트 .env 로드 — 파일이 없으면 조용히 무시

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
CLASSIFIER_MODEL: str = os.getenv("HERA_CLASSIFIER_MODEL", "claude-sonnet-4-6")
CONFIDENCE_THRESHOLD: float = float(os.getenv("HERA_CONFIDENCE_THRESHOLD", "0.6"))


def api_key_present() -> bool:
    """ANTHROPIC_API_KEY가 설정되어 있는지 여부."""
    return bool(ANTHROPIC_API_KEY)
