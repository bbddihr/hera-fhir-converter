"""구조 시그니처 해시 — 반복 입력 가속용 캐시 키.

XML 트리 구조를 정규화(루트→노드 태그 경로 집합 기준, 텍스트값·속성·순서·반복 무시)해
안정적 해시를 만든다. 같은 구조면 값이 달라도 같은 시그니처 → cache hit로 LLM 건너뜀.
"""
from __future__ import annotations

import hashlib

from lxml import etree


def _localname(tag) -> str | None:
    """네임스페이스 제거. 주석/PI 등 비요소는 None."""
    if not isinstance(tag, str):
        return None
    return tag.split("}", 1)[1] if "}" in tag else tag


def signature(xml: str) -> str:
    """XML → 구조 시그니처(sha256 hex).

    Raises:
        ValueError: well-formed XML이 아닐 때.
    """
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(data)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"well-formed XML이 아닙니다: {exc}") from exc

    paths: set[str] = set()

    def walk(node, prefix: str) -> None:
        name = _localname(node.tag)
        if name is None:  # 주석/PI 건너뜀
            return
        path = f"{prefix}/{name}" if prefix else name
        paths.add(path)
        for child in node:
            walk(child, path)

    walk(root, "")
    canonical = "\n".join(sorted(paths))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
