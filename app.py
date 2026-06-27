"""Hera — FHIR Auto-Converter · Streamlit 데모 UI (Phase 0 스캐폴드).

3패널 레이아웃: 좌(Source XML) · 중(변환 실행) · 우(출력 + 프로세싱 로그).
실제 변환 로직은 Phase 1부터 hera.pipeline.convert()에 연결된다.
"""
from __future__ import annotations

import streamlit as st

from hera import config, pipeline

st.set_page_config(page_title="Hera — FHIR Auto-Converter", layout="wide")

st.title("⚕️ Hera — FHIR Auto-Converter")
st.caption("병원 EMR 의무기록(XML) → 의미 분류 → HL7 FHIR R4 계약 객체")

# --- 사이드바: 환경 상태 / 샘플 로더(Phase 5) ---
with st.sidebar:
    st.subheader("환경")
    if config.api_key_present():
        st.success("ANTHROPIC_API_KEY 로드됨")
    else:
        st.warning("ANTHROPIC_API_KEY 미설정 — .env 확인")
    st.write(f"분류 모델: `{config.CLASSIFIER_MODEL}`")
    st.write(f"신뢰도 임계값: `{config.CONFIDENCE_THRESHOLD}`")
    st.divider()
    st.selectbox("샘플 로드 (Phase 5)", ["—"], disabled=True)
    st.caption("Phase 0 — 스캐폴드. 변환 로직은 Phase 1부터 연결됩니다.")

# --- 3패널 ---
left, mid, right = st.columns([5, 2, 6])

with left:
    st.subheader("① Source XML")
    xml_input = st.text_area(
        "EMR 의무기록 서식을 붙여넣으세요",
        height=440,
        placeholder="<원본 EMR XML ...>",
        label_visibility="collapsed",
    )

with mid:
    st.subheader("② 실행")
    run = st.button("▶ FHIR 변환 실행", use_container_width=True, type="primary")
    st.caption("캐시 적중 시 1초 이내")

with right:
    st.subheader("③ 계약 객체 (Output)")
    output_box = st.container()
    st.subheader("프로세싱 로그")
    log_box = st.container()

if run:
    if not xml_input.strip():
        output_box.warning("XML을 먼저 입력하세요.")
    else:
        try:
            result = pipeline.convert(xml_input)
            output_box.json(result)
        except NotImplementedError as exc:
            output_box.info(f"🚧 {exc}")
            log_box.code(
                "pipeline.convert() — Phase 1(Lab 수직 슬라이스)에서 구현 예정",
                language="text",
            )
