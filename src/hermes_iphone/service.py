from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .backends import IphoneBackend, make_backend
from .safety import SafetyPolicy
from .semantic import compact_tree_from_xml, find_elements, is_input
from .state import PluginState


class IphoneService:
    def __init__(
        self,
        backend: IphoneBackend | None = None,
        action_log_root: Path | None = None,
        trace_root: Path | None = None,
        state: PluginState | None = None,
    ):
        self.backend = backend or make_backend()
        self.action_log_root = action_log_root or Path.home() / "iphone-action-logs"
        self.trace_root = trace_root or Path.home() / "iphone-traces"
        self.state = state or PluginState(root=(self.action_log_root.parent / "iphone-state" if action_log_root else None))
        self.policy = SafetyPolicy(state=self.state)

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
            "backends": {"pymobiledevice3": self.backend.name == "pymobiledevice3"},
            "safety": {
                "external_actions_require_confirmation": ["send_text", "place_call", "delete", "purchase", "settings_change"],
                "safe_text_flow": "iphone_prepare_text composes and screenshots; iphone_confirm_prepared_action is the only tool that taps Send.",
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

    def _new_trace(self, action: str, payload: dict[str, Any] | None = None, udid: str | None = None) -> dict[str, Any]:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        safe_action = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in action).strip("-") or "action"
        trace_dir = self.trace_root / f"{stamp}-{safe_action}"
        trace_dir.mkdir(parents=True, exist_ok=True)
        meta = {"action": action, "timestamp": stamp, "udid": udid, **(payload or {})}
        tree = self._tree(udid=udid)
        if tree.get("ok"):
            (trace_dir / "tree-before.json").write_text(json.dumps(tree.get("data", {}).get("tree", {}), indent=2, sort_keys=True))
        try:
            shot = self.screenshot(udid=udid)
        except Exception as exc:
            shot = {"ok": False, "error": exc.__class__.__name__, "message": str(exc)}
        if shot.get("ok"):
            meta["screenshot"] = (shot.get("data") or {}).get("path")
        else:
            meta["screenshot_error"] = shot.get("error") or shot.get("message")
        (trace_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
        return {"trace_dir": str(trace_dir), "screenshot": meta.get("screenshot")}

    def tree(self, udid: str | None = None) -> dict[str, Any]:
        return self._tree(udid=udid)

    def describe_screen(self, udid: str | None = None, limit: int = 20) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        tree = tree_result["data"]["tree"]
        elements = tree.get("elements", [])[:limit]
        summary = "\n".join(f"{el.get('id')} {el.get('type')}: {el.get('label')}" for el in elements)
        return {"ok": True, "data": {"bundle_id": tree.get("bundle_id"), "name": tree.get("name"), "summary": summary, "elements": elements, "udid": udid}, "meta": {"backend": getattr(self.backend, "name", "unknown")}}

    def last_trace(self) -> dict[str, Any]:
        traces = sorted([p for p in self.trace_root.glob("*") if p.is_dir()], reverse=True)
        if not traces:
            return {"ok": False, "error": "trace_not_found", "message": "No iPhone trace folders found."}
        latest = traces[0]
        meta_path = latest / "meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        return {"ok": True, "data": {"trace_dir": str(latest), "meta": meta, "files": sorted(p.name for p in latest.iterdir())}}

    def action_logs(self, limit: int = 10) -> dict[str, Any]:
        logs = sorted(self.action_log_root.glob("iphone-action-*.json"), reverse=True)[:limit]
        entries = []
        for path in logs:
            try:
                entries.append({"path": str(path), "record": json.loads(path.read_text())})
            except Exception:
                entries.append({"path": str(path), "record": None})
        return {"ok": True, "data": {"logs": entries, "count": len(entries)}}

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
        trace = self._new_trace("tap_element", {"element": element}, udid=udid)
        result = self.tap(x=int(center["x"]), y=int(center["y"]), udid=udid)
        if result.get("ok"):
            result.setdefault("data", {})["element"] = element
            result.setdefault("meta", {})["action_log"] = self._log_action("tap_element", {"element": element, "udid": udid})
            result.setdefault("meta", {})["trace_dir"] = trace["trace_dir"]
        return result

    def tap_element_id(self, element_id: str, udid: str | None = None) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        for element in tree_result["data"]["tree"].get("elements", []):
            if element.get("id") == element_id:
                return self.tap_element(element, udid=udid)
        return {"ok": False, "error": "element_not_found", "message": f"No current element has id {element_id!r}", "data": {"element_id": element_id}}

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

    def prepare_text(self, to: str, body: str, udid: str | None = None) -> dict[str, Any]:
        launched = self.launch_or_focus("com.apple.MobileSMS", udid=udid)
        if not launched.get("ok"):
            return launched
        self.tap_text("Compose", udid=udid)
        typed_to = self.type_into_field("To:", to, udid=udid)
        if not typed_to.get("ok"):
            return typed_to
        selected_recipient = self._select_text_recipient_suggestion(to=to, udid=udid)
        if not selected_recipient.get("ok") and selected_recipient.get("error") != "recipient_suggestion_not_found":
            return selected_recipient
        body_field = None
        for candidate in ("iMessage", "Message", "messageBodyField"):
            typed_body = self.type_into_field(candidate, body, udid=udid)
            if typed_body.get("ok"):
                body_field = typed_body
                break
        if body_field is None:
            return typed_body
        recipient_check = self._verify_text_recipient(to=to, udid=udid)
        if not recipient_check.get("ok"):
            return recipient_check
        recipient = recipient_check.get("data") or {}
        screenshot = self.screenshot(udid=udid)
        screenshot_path = (screenshot.get("data") or {}).get("path") if screenshot.get("ok") else None
        send = self.find_element(text="Send", element_type="button", enabled=True, udid=udid)
        if not send.get("ok"):
            return send
        element = send["data"]["element"]
        payload = {"to": to, "body_length": len(body), "udid": udid, "send_element": element, "screenshot_before_send": screenshot_path, "recipient": recipient}
        prepared = self.policy.prepare("send_text", payload)
        self._log_action("prepare_text", payload)
        return {
            **prepared,
            "data": {"to": to, "body_length": len(body), "screenshot_before_send": screenshot_path, "send_element": element, "recipient": recipient, "udid": udid},
            "next_step": "Ask the user to approve sending this already-composed message, then call iphone_confirm_prepared_action with the token.",
        }

    def _select_text_recipient_suggestion(self, to: str, udid: str | None = None) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        elements = (tree_result.get("data") or {}).get("tree", {}).get("elements", [])
        query = to.strip().lower()
        for element in elements:
            label = str(element.get("label") or element.get("name") or "").strip()
            normalized = label.lower()
            if element.get("type") in {"cell", "button"} and query and query in normalized and ("maybe:" in normalized or normalized != query):
                tapped = self.tap_element(element, udid=udid)
                if not tapped.get("ok"):
                    return tapped
                display = label.split(":", 1)[1].strip() if ":" in label else label
                return {"ok": True, "data": {"verified_by": "contact_suggestion", "display": display, "element": element}}
        return {"ok": False, "error": "recipient_suggestion_not_found", "message": f"No Messages contact suggestion matched {to!r}"}

    def _verify_text_recipient(self, to: str, udid: str | None = None) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        elements = (tree_result.get("data") or {}).get("tree", {}).get("elements", [])
        query = to.strip().lower()
        for element in elements:
            label = str(element.get("label") or element.get("name") or "").strip().lower()
            value = str(element.get("value") or "").strip().lower()
            raw_value = str(element.get("value") or "").strip()
            if element.get("type") in {"textfield", "textview", "searchfield"} and label in {"to:", "to"}:
                if not value or query in value:
                    verified_by = "contact_suggestion" if value and value != query else "to_field"
                    return {"ok": True, "data": {"recipient_element": element, "verified_by": verified_by, "display": raw_value or to}}
        return {
            "ok": False,
            "error": "recipient_not_verified",
            "message": f"Recipient {to!r} is not visible as a verified Messages recipient; refusing to prepare Send.",
            "data": {"to": to, "tree": (tree_result.get("data") or {}).get("tree")},
        }

    def send_text(
        self,
        to: str,
        body: str,
        udid: str | None = None,
        approval_fn: Callable[..., str] | None = None,
    ) -> dict[str, Any]:
        prepared = self.prepare_text(to=to, body=body, udid=udid)
        if not prepared.get("ok"):
            return prepared

        command = f"Send iMessage/SMS to {to} ({len(body)} characters)"
        approval = self._request_send_approval(
            command=command,
            description="send_text",
            approval_fn=approval_fn,
        )
        if approval not in {"once", "session", "always"}:
            error = "approval_denied" if approval == "deny" else "approval_required"
            message = (
                "Hermes approval is not available in this interface. The draft is staged but unsent; "
                "use the fallback token with iphone_confirm_prepared_action only after explicit approval, "
                "or rerun from a gateway session / yolo-approved context."
            ) if approval == "unavailable" else "Hermes approval denied the staged send; the draft remains unsent."
            return {
                "ok": False,
                "error": error,
                "approval": approval,
                "message": message,
                "staged": True,
                "token": prepared.get("token"),
                "data": prepared.get("data"),
                "next_step": "Use the fallback token with iphone_confirm_prepared_action only after explicit approval.",
            }

        sent = self.confirm_prepared_action(prepared["token"], udid=udid)
        if sent.get("ok"):
            sent["approval"] = approval
        return sent

    def _request_send_approval(
        self,
        *,
        command: str,
        description: str,
        approval_fn: Callable[..., str] | None = None,
    ) -> str:
        fn = approval_fn
        if fn is None:
            try:
                from tools.approval import prompt_dangerous_approval  # type: ignore
                fn = prompt_dangerous_approval
            except Exception:
                return "unavailable"
        try:
            return str(fn(command, description, allow_permanent=True)).strip().lower()
        except Exception:
            return "deny"

    def confirm_prepared_action(self, token: str, udid: str | None = None) -> dict[str, Any]:
        confirmed = self.policy.confirm(token)
        if not confirmed.get("ok"):
            return confirmed
        action = confirmed.get("action")
        payload = confirmed.get("payload") or {}
        if action != "send_text":
            return confirmed
        actual_udid = udid or payload.get("udid")
        element = payload.get("send_element")
        result = self.tap_element(element, udid=actual_udid) if isinstance(element, dict) else self.tap_text("Send", element_type="button", udid=actual_udid)
        if result.get("ok"):
            self._log_action("confirm_send_text", {"to": payload.get("to"), "body_length": payload.get("body_length"), "udid": actual_udid})
            return {"ok": True, "action": action, "data": {"sent": True, "to": payload.get("to"), "body_length": payload.get("body_length"), "screenshot_before_send": payload.get("screenshot_before_send")}, "meta": result.get("meta", {})}
        return result
