"""연세(yuhs.ac) GeneralRecord XML 파서.

구조:
  <GeneralRecord>
    <ATTRIBUTE NAME="응급실 협진"> <ATTR NAME="Yes" TYPE="RA">True</ATTR> ... </ATTRIBUTE>  # 라디오(선택형)
    <ATTR NAME="의뢰사유" TYPE="TE">...</ATTR>                                            # 단일 항목
    <GRID> <GRIDATTR DataCd="DI015840">S/P kidney transplant</GRIDATTR> ... </GRID>       # 표(진단 등)
  </GeneralRecord>

태그가 네임스페이스(http://yuhs.ac/ClinicalRecord.xsd)에 있으므로 localname으로 매칭한다.
"""
from __future__ import annotations

import re

from lxml import etree


def _local(tag) -> str | None:
    if not isinstance(tag, str):
        return None
    return tag.split("}", 1)[1] if "}" in tag else tag


def _norm_text(s: str | None) -> str:
    if not s:
        return ""
    # 원본의 줄바꿈 아티팩트('n') 및 공백 정리 — 텍스트 끝의 'n' 반복 제거
    s = s.strip()
    s = re.sub(r"n+\s*$", "", s)  # 말미 'n','nnn' 아티팩트
    return s.strip()


def parse_general_record(xml: str) -> dict:
    """GeneralRecord XML → 정규화 구조.

    Returns:
        {
          "attributes": [{"name","value","type","code","datacode"}],  # 단일 ATTR
          "choices":    [{"name","selected"}],                          # ATTRIBUTE 라디오
          "diagnoses":  [{"text","code"}],                              # GRID
        }

    Raises:
        ValueError: well-formed XML이 아닐 때.
    """
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(data)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"well-formed XML이 아닙니다: {exc}") from exc

    record = None
    for el in root.iter():
        if _local(el.tag) == "GeneralRecord":
            record = el
            break
    if record is None:
        record = root

    attributes: list[dict] = []
    choices: list[dict] = []
    diagnoses: list[dict] = []

    for child in record:
        tag = _local(child.tag)
        if tag == "ATTRIBUTE":
            # 라디오: text=="True"인 ATTR의 NAME이 선택값
            selected = None
            for sub in child:
                if _local(sub.tag) == "ATTR" and (sub.text or "").strip() == "True":
                    selected = sub.get("NAME")
                    break
            choices.append({"name": child.get("NAME"), "selected": selected})
        elif tag == "ATTR":
            attributes.append(
                {
                    "name": child.get("NAME"),
                    "value": _norm_text(child.text),
                    "type": child.get("TYPE"),
                    "code": child.get("CODE"),
                    "datacode": child.get("DATACODE"),
                }
            )
        elif tag == "GRID":
            for g in child:
                if _local(g.tag) == "GRIDATTR":
                    diagnoses.append(
                        {"text": _norm_text(g.text), "code": g.get("DataCd")}
                    )

    return {"attributes": attributes, "choices": choices, "diagnoses": diagnoses}


def index(parsed: dict) -> dict:
    """이름 기반 조회 헬퍼 — {attr_name: attr_dict}, {choice_name: selected}."""
    attrs = {a["name"]: a for a in parsed["attributes"] if a.get("name")}
    chs = {c["name"]: c.get("selected") for c in parsed["choices"] if c.get("name")}
    return {"attrs": attrs, "choices": chs, "diagnoses": parsed["diagnoses"]}
