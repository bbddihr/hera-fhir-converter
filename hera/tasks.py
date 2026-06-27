"""form_type → (target_task, target_role) 매핑 테이블.

분류 시점에 다운스트림 생성 TASK와 대상 의료인 역할을 함께 확정한다.

Phase 0: 스텁. Phase 3에서 표 확정.
"""
from __future__ import annotations

# TODO(Phase 3): TASK 매핑 테이블
# 예시 (PRD 3-매핑표):
#   lab              -> ("검사결과 판독/요약", "검사 의뢰의")
#   anesthesia_record-> ("마취통증의학과 협의진료 회신서", "마취과 전문의")
#   outpatient_first -> ("협진 의뢰/회신·초진 요약", "진료과 의사")
#   emergency_record -> ("응급진료기록", "응급의학과 의사")
