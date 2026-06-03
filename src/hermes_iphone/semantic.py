from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


INTERESTING_TYPES = {
    "XCUIElementTypeApplication",
    "XCUIElementTypeButton",
    "XCUIElementTypeTextField",
    "XCUIElementTypeSecureTextField",
    "XCUIElementTypeTextView",
    "XCUIElementTypeStaticText",
    "XCUIElementTypeCell",
    "XCUIElementTypeLink",
    "XCUIElementTypeSwitch",
    "XCUIElementTypeSearchField",
    "XCUIElementTypeTabBar",
    "XCUIElementTypeIcon",
}

INPUT_TYPES = {"textfield", "securetextfield", "textview", "searchfield"}


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).lower() == "true"


def _int(value: str | None, default: int = 0) -> int:
    try:
        return int(float(value or default))
    except (TypeError, ValueError):
        return default


def _short_type(raw: str) -> str:
    return raw.replace("XCUIElementType", "").lower()


def _label(attrs: dict[str, str]) -> str:
    for key in ("label", "name", "value"):
        value = attrs.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def compact_tree_from_xml(
    xml: str, *, visible_only: bool = True, limit: int = 250
) -> dict[str, Any]:
    root = ET.fromstring(xml)
    elements: list[dict[str, Any]] = []
    bundle_id = root.attrib.get("bundleId")
    app_name = _label(root.attrib)

    def walk(node: ET.Element, path: str) -> None:
        if len(elements) >= limit:
            return
        attrs = dict(node.attrib)
        raw_type = attrs.get("type") or node.tag
        visible = _bool(attrs.get("visible"), True)
        label = _label(attrs)
        width = _int(attrs.get("width"))
        height = _int(attrs.get("height"))
        x = _int(attrs.get("x"))
        y = _int(attrs.get("y"))
        include = raw_type in INTERESTING_TYPES and label and width >= 0 and height >= 0
        if visible_only and not visible:
            include = False
        if include:
            elements.append(
                {
                    "id": f"e{len(elements)}",
                    "type": _short_type(raw_type),
                    "raw_type": raw_type,
                    "label": label,
                    "name": attrs.get("name"),
                    "value": attrs.get("value"),
                    "enabled": _bool(attrs.get("enabled"), True),
                    "visible": visible,
                    "accessible": _bool(attrs.get("accessible"), False),
                    "bounds": {"x": x, "y": y, "width": width, "height": height},
                    "center": {"x": x + width // 2, "y": y + height // 2},
                    "traits": attrs.get("traits", ""),
                    "path": path,
                }
            )
        for idx, child in enumerate(list(node)):
            walk(child, f"{path}/{idx}")

    walk(root, "0")
    return {
        "bundle_id": bundle_id,
        "name": app_name,
        "element_count": len(elements),
        "truncated": len(elements) >= limit,
        "elements": elements,
    }


def _match_score(element: dict[str, Any], query: str) -> int:
    if not query:
        return 0
    values = [str(element.get(k) or "").casefold() for k in ("label", "name", "value")]
    element_type = str(element.get("type", "")).casefold()
    score = 0
    if any(value == query for value in values):
        score += 100
    elif any(value.startswith(query) for value in values):
        score += 60
    elif any(query in value for value in values):
        score += 25
    if element_type in INPUT_TYPES:
        score += 20
    if element.get("accessible"):
        score += 5
    return score


def find_elements(
    tree: dict[str, Any],
    *,
    text: str | None = None,
    element_type: str | None = None,
    enabled: bool | None = None,
    visible: bool | None = True,
    limit: int = 10,
) -> list[dict[str, Any]]:
    query = (text or "").casefold()
    wanted_type = (
        element_type.replace("XCUIElementType", "").casefold() if element_type else None
    )
    scored_matches: list[tuple[int, int, dict[str, Any]]] = []
    for idx, element in enumerate(tree.get("elements", [])):
        if visible is not None and bool(element.get("visible")) is not visible:
            continue
        if enabled is not None and bool(element.get("enabled")) is not enabled:
            continue
        if wanted_type and wanted_type not in str(element.get("type", "")).casefold():
            continue
        haystack = " ".join(
            str(element.get(k) or "") for k in ("label", "name", "value")
        ).casefold()
        if query and query not in haystack:
            continue
        scored_matches.append((_match_score(element, query), idx, element))
    scored_matches.sort(key=lambda item: (-item[0], item[1]))
    return [element for _score, _idx, element in scored_matches[:limit]]


def first_element(tree: dict[str, Any], **kwargs: Any) -> dict[str, Any] | None:
    matches = find_elements(tree, limit=1, **kwargs)
    return matches[0] if matches else None


def is_input(element: dict[str, Any]) -> bool:
    return str(element.get("type", "")).casefold() in INPUT_TYPES
