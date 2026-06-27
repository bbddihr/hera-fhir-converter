"""Hera — FHIR Auto-Converter · Streamlit 데모 UI.

흐름: ① 원본 XML → ② 분석 결과(판별·근거·권장 리소스) → ③ 프로파일링 매핑 → ④ 변환 결과(+R4 검증).
LLM은 ② 의미 분석만, ③④ FHIR 조립·검증은 결정론적 엔진(hera.pipeline)이 담당.
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

import streamlit as st
from lxml import etree

from hera import config, pipeline

SAMPLES = Path(__file__).resolve().parent / "samples"

st.set_page_config(page_title="Hera — FHIR Auto-Converter", layout="wide")

st.markdown(
    """
    <style>
    .chip {display:inline-block;padding:4px 11px;margin:3px 4px;border-radius:14px;
           background:#eef2f7;font-size:13px;color:#334;border:1px solid #e2e8f0;}
    .chip-warn {background:#fdf0d5;border-color:#f0d9a0;}
    .res-primary {border:1.5px solid #6b8afd;border-radius:10px;padding:14px 16px;margin:6px 0;background:#fafbff;}
    .res-chip {display:inline-block;padding:6px 12px;margin:4px;border-radius:8px;
               background:#f3f5f9;font-size:13px;border:1px solid #e2e8f0;}
    .maprow {display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px dashed #eef0f4;}
    .mapsrc {min-width:160px;font-weight:600;font-size:13px;}
    .maparrow {color:#aab;}
    .maptgt {background:#eef2ff;padding:2px 8px;border-radius:6px;font-family:monospace;font-size:12px;color:#345;}
    .mapraw {color:#889;font-size:12px;margin-left:auto;max-width:260px;
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
    .badge-ok {background:#e7f6ec;color:#1a7f37;padding:4px 10px;border-radius:12px;font-size:13px;}
    .badge-warn {color:#9a6700;font-size:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚕️ Hera — FHIR Auto-Converter")
st.caption("병원 EMR 의무기록(XML)을 읽고 → 서식 판별 → FHIR 리소스 프로파일링 → R4 변환·검증")

if "xml_input" not in st.session_state:
    st.session_state.xml_input = ""


def _prettify(xml: str) -> str:
    try:
        root = etree.fromstring(xml.encode("utf-8"))
        return etree.tostring(root, pretty_print=True, encoding="unicode")
    except etree.XMLSyntaxError:
        return xml


# --- 사이드바 ---
with st.sidebar:
    st.subheader("환경")
    if config.api_key_present():
        st.success("ANTHROPIC_API_KEY 로드됨")
    else:
        st.warning("ANTHROPIC_API_KEY 미설정 — 구조 기반 폴백으로 동작")
    st.write(f"분석 모델: `{config.CLASSIFIER_MODEL}`")
    st.divider()
    files = ["—"] + sorted(p.name for p in SAMPLES.glob("*.xml"))
    choice = st.selectbox("샘플 선택", files)
    if st.button("샘플 불러오기", use_container_width=True, disabled=choice == "—"):
        st.session_state.xml_input = _prettify((SAMPLES / choice).read_text(encoding="utf-8"))
        st.session_state.pop("result", None)
        st.rerun()
    st.caption("모든 샘플은 합성/예시 데이터입니다.")


# --- ① 원본 XML ---
st.subheader("① 원본 XML")
xml_input = st.text_area(
    "EMR 의무기록 서식을 붙여넣으세요",
    height=240,
    key="xml_input",
    label_visibility="collapsed",
    placeholder="<원본 EMR XML ...>",
)
run = st.button("▶ FHIR 변환 실행", type="primary")

if run:
    if not st.session_state.xml_input.strip():
        st.warning("XML을 먼저 입력하세요.")
    else:
        try:
            st.session_state.result = pipeline.convert(st.session_state.xml_input)
        except ValueError as exc:
            st.session_state.result = {"error": str(exc)}

result = st.session_state.get("result")
if result and "error" in result:
    st.error(f"입력 오류: {result['error']}")
elif result:
    analysis = result["analysis"]
    coverage = result["coverage"]
    validation = result["validation"]

    # --- ② 분석 결과 ---
    st.subheader("② 분석 결과")
    conf = analysis["confidence"]
    via = {"semantic": "LLM 분석", "cache": "캐시", "fallback": "구조 기반"}.get(analysis["via"], analysis["via"])
    st.markdown(
        f"이 의무기록은 **{html.escape(analysis['document_label'])}** "
        f"<span class='badge-ok'>✓ 신뢰도 {conf:.2f} · {via}</span>",
        unsafe_allow_html=True,
    )
    if analysis["rationale"]:
        chips = "".join(f"<span class='chip'>○ {html.escape(str(r))}</span>" for r in analysis["rationale"])
        st.markdown("판별 근거", help="LLM이 이 항목들의 존재를 근거로 판별")
        st.markdown(chips, unsafe_allow_html=True)

    st.markdown("**권장 FHIR 리소스** · HL7 FHIR R4 resourcelist 기반")
    note = f" — {html.escape(analysis['primary_note'])}" if analysis.get("primary_note") else ""
    st.markdown(
        f"<div class='res-primary'>📄 <b>{analysis['primary_resource']}</b> "
        f"<span class='chip'>주 리소스 · {analysis['bundle_type']}</span>{note}</div>",
        unsafe_allow_html=True,
    )
    if analysis["companion_resources"]:
        comp = "".join(
            f"<span class='res-chip'>{html.escape(c['resource'])} · {html.escape(c.get('role',''))}</span>"
            for c in analysis["companion_resources"]
        )
        st.markdown("동반 리소스", unsafe_allow_html=True)
        st.markdown(comp, unsafe_allow_html=True)
    for alt in analysis["alternative_resources"]:
        st.info(f"💡 대안: **{alt['resource']}** — {alt.get('note','')}")

    # --- ③ 프로파일링 매핑 ---
    st.subheader("③ 프로파일링 매핑")
    st.markdown(
        f"<span class='badge-ok'>{coverage.get('total',0)}개 중 "
        f"{coverage.get('mapped',0)}개 매핑</span>",
        unsafe_allow_html=True,
    )
    groups: dict[str, list] = defaultdict(list)
    for row in result["mapping"]:
        groups[row["resource_group"]].append(row)
    for group, rows in groups.items():
        st.markdown(f"**● {html.escape(group)}**")
        for r in rows:
            raw = html.escape((r["raw_value"] or "")[:60])
            if r["status"] == "inferred":
                tgt = f"<span class='badge-warn'>⚠ 추론 필요 · {html.escape(r['fhir_target'])}</span>"
            else:
                tgt = f"<span class='maptgt'>{html.escape(r['fhir_target'])}</span>"
            st.markdown(
                f"<div class='maprow'><span class='mapsrc'>{html.escape(r['xml_item'])}</span>"
                f"<span class='maparrow'>→</span>{tgt}"
                f"<span class='mapraw'>{raw}</span></div>",
                unsafe_allow_html=True,
            )

    # --- ④ 변환 결과 ---
    st.subheader("④ 변환 결과")
    if validation["r4_valid"]:
        st.markdown(
            f"<span class='badge-ok'>✓ R4 Valid · {html.escape(validation['invariants'])}</span>",
            unsafe_allow_html=True,
        )
    else:
        st.error("✗ R4 Invalid")
        for e in validation["errors"]:
            st.caption(f"• {e}")
    st.json(result["fhir_bundle"], expanded=False)
    st.download_button(
        "FHIR Bundle 다운로드 (JSON)",
        data=json.dumps(result["fhir_bundle"], ensure_ascii=False, indent=2),
        file_name="fhir_bundle.json",
        mime="application/json",
    )
