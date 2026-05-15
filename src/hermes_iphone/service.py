from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .backends import IphoneBackend, make_backend
from .semantic import compact_tree_from_xml, find_elements, first_element, is_input


class IphoneService:
    def __init__(self, backend: IphoneBackend | None = None, action_log_root: Path | None = None):
        self.backend = backend or make_backend()
        self.action_log_root = action_log_root or Path.home() / "iphone-action-logs"

    def _result(self, result) -> dict[str, Any]:
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        payload.setdefault("meta", {})
        payload["meta"].setdefault("backend", getattr(self.backend, "name", "unknown"))
        return payload

    def status(self) -> dict[str, Any]:
        payload = {
            "ok": True,
            "plugin": "hermes-iphone-plugin",
            "backend": getattr(self.backend, "name", "unknown"),
            "backends": {
                "pymobiledevice3": self.backend.name == "pymobiledevice3",
            },
            "safety": {
                "external_actions_require_confirmation": ["send_text", "place_call", "delete", "purchase", "settings_change"],
            },
        }
        diagnostics = getattr(self.backend, "diagnostics", None)
        if diagnostics:
            try:
                payload["diagnostics"] = self._result(diagnostics()).get("data", {})
            except Exception as exc:
                payload["diagnostics_error"] = str(exc) or exc.__class__.__name__
        return payload

    def list_devices(self) -> dict[str, Any]:
        return self._result(self.backend.list_devices())
    def ensure_wda(self, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.ensure_wda(udid=udid))
    def screenshot(self, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.screenshot(udid=udid))
    def screen_info(self, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.screen_info(udid=udid))
    def source(self, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.source(udid=udid))
    def open_url(self, url: str, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.open_url(url=url, udid=udid))
    def launch_app(self, bundle_id: str, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.launch_app(bundle_id=bundle_id, udid=udid))
    def tap(self, x: int, y: int, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.tap(x=x, y=y, udid=udid))
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.2, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.swipe(start_x=start_x, start_y=start_y, end_x=end_x, end_y=end_y, duration=duration, udid=udid))
    def type_text(self, text: str, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.type_text(text=text, udid=udid))
    def press_button(self, button: str, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.press_button(button=button, udid=udid))

    def _tree(self, udid: str | None = None) -> dict[str, Any]:
        source = self.source(udid=udid)
        if not source.get("ok"):
            return source
        xml = (source.get("data") or {}).get("source", "")
        return {"ok": True, "data": {"tree": compact_tree_from_xml(xml), "udid": udid}, "meta": source.get("meta", {})}

    def _log_action(self, action: str, payload: dict[str, Any]) -> str:
        self.action_log_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        path = self.action_log_root / f"iphone-action-{stamp}.json"
        record = {"action": action, "timestamp": stamp, **payload}
        path.write_text(json.dumps(record, sort_keys=True, indent=2))
        return str(path)

    def tree(self, udid: str | None = None) -> dict[str, Any]:
        return self._tree(udid=udid)

    def find_element(self, text: str | None = None, element_type: str | None = None, enabled: bool | None = None, visible: bool | None = True, udid: str | None = None) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        tree = tree_result["data"]["tree"]
        matches = find_elements(tree, text=text, element_type=element_type, enabled=enabled, visible=visible)
        if not matches:
            return {"ok": False, "error": "element_not_found", "message": f"No visible element matched text={text!r} type={element_type!r}", "data": {"matches": [], "tree": tree}}
        return {"ok": True, "data": {"element": matches[0], "matches": matches, "udid": udid}, "meta": {"backend": getattr(self.backend, "name", "unknown")}}

    def tap_element(self, element: dict[str, Any], udid: str | None = None) -> dict[str, Any]:
        center = element.get("center") or {}
        result = self.tap(x=int(center["x"]), y=int(center["y"]), udid=udid)
        if result.get("ok"):
            result.setdefault("data", {})["element"] = element
            result.setdefault("meta", {})["action_log"] = self._log_action("tap_element", {"element": element, "udid": udid})
        return result

    def tap_text(self, text: str, element_type: str | None = None, udid: str | None = None) -> dict[str, Any]:
        found = self.find_element(text=text, element_type=element_type, enabled=True, udid=udid)
        if not found.get("ok"):
            return found
        return self.tap_element(found["data"]["element"], udid=udid)

    def wait_for_text(self, text: str, timeout_seconds: float = 10.0, poll_seconds: float = 0.5, udid: str | None = None) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        attempts = 0
        last = None
        while time.monotonic() <= deadline:
            attempts += 1
            last = self.find_element(text=text, udid=udid)
            if last.get("ok"):
                last.setdefault("data", {})["attempts"] = attempts
                return last
            time.sleep(max(0.0, poll_seconds))
        return {"ok": False, "error": "wait_timeout", "message": f"Timed out waiting for text {text!r}", "data": {"attempts": attempts, "last": last}}

    def type_into_field(self, field: str, text: str, udid: str | None = None) -> dict[str, Any]:
        found = self.find_element(text=field, udid=udid)
        if not found.get("ok"):
            return found
        element = found["data"]["element"]
        if not is_input(element):
            # Still allow named fields represented as static labels by tapping their center; WDA focus behavior decides success.
            pass
        tapped = self.tap_element(element, udid=udid)
        if not tapped.get("ok"):
            return tapped
        typed = self.type_text(text=text, udid=udid)
        if typed.get("ok"):
            typed.setdefault("data", {})["field"] = element
            typed.setdefault("meta", {})["action_log"] = self._log_action("type_into_field", {"field": element, "text_length": len(text), "udid": udid})
        return typed

    def current_app(self, udid: str | None = None) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        tree = tree_result["data"]["tree"]
        return {"ok": True, "data": {"bundle_id": tree.get("bundle_id"), "name": tree.get("name"), "udid": udid}, "meta": {"backend": getattr(self.backend, "name", "unknown")}}

    def launch_or_focus(self, bundle_id: str, udid: str | None = None) -> dict[str, Any]:
        current = self.current_app(udid=udid)
        if current.get("ok") and (current.get("data") or {}).get("bundle_id") == bundle_id:
            return {"ok": True, "data": {**current["data"], "already_foreground": True}, "meta": current.get("meta", {})}
        launched = self.launch_app(bundle_id=bundle_id, udid=udid)
        if launched.get("ok"):
            launched.setdefault("data", {})["already_foreground"] = False
        return launched
