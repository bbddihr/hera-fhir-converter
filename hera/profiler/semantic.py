"""의미 분류 — Claude Sonnet 4.6로 XML 텍스트 내용 기반 form_type 판별.

구조가 아닌 내용(semantic)을 읽어 어떤 서식인지 분류한다. tool use(structured output)로
출력 스키마를 강제해 파싱 안정성·재현성을 확보한다. 산출: form_type, confidence.
"""
from __future__ import annotations

import anthropic

from .. import config

FORM_TYPES = ["lab", "anesthesia_record", "outpatient_first", "emergency_record", "unknown"]

_SYSTEM = (
    "당신은 병원 의무기록 서식 분류기다. 입력으로 EMR 원본 XML이 주어진다. "
    "XML의 태그 구조가 아니라 '안의 텍스트 내용(semantic)'을 읽고, 어떤 의무기록 서식인지 분류하라.\n"
    "- lab: 진단검사기록(혈액·소변 등 검사 항목/결과값/참고치 중심)\n"
    "- anesthesia_record: 마취기록(마취 유도·술중 활력징후·투여 약물 중심)\n"
    "- outpatient_first: 외래초진기록(주호소·현병력·진단·소견 중심)\n"
    "- emergency_record: 응급진료기록(triage·응급 처치 중심)\n"
    "- unknown: 위 어디에도 해당하지 않거나 판단 불가\n"
    "반드시 classify_form 도구를 호출해 결과를 반환하라."
)

_TOOL = {
    "name": "classify_form",
    "description": "의무기록 XML의 서식 유형을 의미 기반으로 분류한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "form_type": {"type": "string", "enum": FORM_TYPES},
            "confidence": {
                "type": "number",
                "description": "0.0~1.0 분류 신뢰도",
                "minimum": 0,
                "maximum": 1,
            },
            "rationale": {"type": "string", "description": "한 줄 근거"},
        },
        "required": ["form_type", "confidence"],
    },
}


def classify(xml: str) -> dict:
    """XML → {form_type, confidence}. (실제 Claude API 호출)

    Raises:
        RuntimeError: API 키 미설정 또는 분류 실패.
    """
    if not config.api_key_present():
        raise RuntimeError("ANTHROPIC_API_KEY 미설정 — 의미 분류를 호출할 수 없습니다.")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=config.CLASSIFIER_MODEL,
        max_tokens=512,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "classify_form"},
        messages=[{"role": "user", "content": xml}],
    )

    for block in message.content:
        if block.type == "tool_use" and block.name == "classify_form":
            data = block.input
            return {
                "form_type": str(data["form_type"]),
                "confidence": float(data["confidence"]),
            }
    raise RuntimeError("의미 분류 실패 — 도구 호출 결과를 찾지 못했습니다.")
