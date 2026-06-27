"""form_type → (target_task, target_role) 매핑 테이블.

분류 시점에 다운스트림 생성 TASK와 대상 의료인 역할을 함께 확정한다(PRD 3-매핑표).
"""
from __future__ import annotations

TASKS: dict[str, tuple[str, str]] = {
    "lab": ("검사결과 판독/요약", "검사 의뢰의"),
    "anesthesia_record": ("마취통증의학과 협의진료 회신서", "마취과 전문의"),
    "outpatient_first": ("협진 의뢰/회신·초진 요약", "진료과 의사"),
    "emergency_record": ("응급진료기록", "응급의학과 의사"),
}

DEFAULT_TASK: tuple[str, str] = ("미분류 서식 검토", "담당 의료인")


def task_for(form_type: str) -> tuple[str, str]:
    """form_type에 대응하는 (target_task, target_role). 미정의 시 기본값."""
    return TASKS.get(form_type, DEFAULT_TASK)
