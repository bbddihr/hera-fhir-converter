"""Hera — FHIR Auto-Converter · Streamlit 데모 UI.

3패널 레이아웃: 좌(Source XML) · 중(변환 실행) · 우(출력 + 프로세싱 로그).
Phase 1: hera.pipeline.convert() 연결 — Lab 수직 슬라이스(시나리오 1).
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import streamlit as st

from hera import config, pipeline
from hera.mapper.lab import interpretation_summary

SAMPLES = Path(__file__).resolve().parent / "samples"

st.set_page_config(page_title="Hera — FHIR Auto-Converter", layout="wide")

st.title("⚕️ Hera — FHIR Auto-Converter")
st.caption("병원 EMR 의무기록(XML) → 의미 분류 → HL7 FHIR R4 계약 객체")

if "xml_input" not in st.session_state:
    st.session_state.xml_input = ""

# --- 사이드바: 환경 상태 / 샘플 로더 ---
with st.sidebar:
    st.subheader("환경")
    if config.api_key_present():
        st.success("ANTHROPIC_API_KEY 로드됨")
    else:
        st.warning("ANTHROPIC_API_KEY 미설정 — .env 확인")
    st.write(f"분류 모델: `{config.CLASSIFIER_MODEL}`")
    st.write(f"신뢰도 임계값: `{config.CONFIDENCE_THRESHOLD}`")
    st.divider()

    sample_files = ["—"] + sorted(p.name for p in SAMPLES.glob("*.xml"))
    choice = st.selectbox("샘플 선택", sample_files)
    if st.button("샘플 불러오기", use_container_width=True, disabled=choice == "—"):
        st.session_state.xml_input = (SAMPLES / choice).read_text(encoding="utf-8")
        st.rerun()
    st.caption("모든 샘플은 합성 데이터(synthetic)입니다.")


def _resource_summary(bundle: dict) -> str:
    counts = Counter(e["resource"]["resourceType"] for e in bundle.get("entry", []))
    return " + ".join(f"{rtype}×{n}" for rtype, n in counts.items())


# --- 3패널 ---
left, mid, right = st.columns([5, 2, 6])

with left:
    st.subheader("① Source XML")
    xml_input = st.text_area(
        "EMR 의무기록 서식을 붙여넣으세요",
        height=440,
        placeholder="<원본 EMR XML ...>",
        label_visibility="collapsed",
        key="xml_input",
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
    if not st.session_state.xml_input.strip():
        output_box.warning("XML을 먼저 입력하세요.")
    else:
        try:
            result = pipeline.convert(st.session_state.xml_input)
        except ValueError as exc:
            output_box.error(f"입력 오류: {exc}")
        except Exception as exc:  # noqa: BLE001 — 데모: 모든 오류를 사용자에게 노출
            output_box.error(f"변환 실패: {exc}")
        else:
            val = result["validation"]
            cls = result["classification"]
            badge = "✓ R4 Valid" if val["r4_valid"] else "✗ R4 Invalid"
            cols = output_box.columns(3)
            cols[0].metric("form_type", result["form_type"])
            cols[1].metric("target_role", result["target_role"])
            cols[2].metric("검증", badge)
            output_box.json(result)

            logs = [
                f"classify → form_type={result['form_type']} "
                f"(via {cls['via']}, conf {cls['confidence']})",
                f"target_task={result['target_task']} / role={result['target_role']}",
                f"resources: {_resource_summary(result['fhir_bundle'])}",
            ]
            normal, abnormal = interpretation_summary(result["fhir_bundle"])
            if normal or abnormal:
                logs.append(f"interpretation: 정상 {normal} / 비정상 {abnormal}")
            logs.append(f"R4 검증: {val['invariants']}")
            if val["errors"]:
                logs += [f"  ! {e}" for e in val["errors"]]
            log_box.code("\n".join(logs), language="text")
