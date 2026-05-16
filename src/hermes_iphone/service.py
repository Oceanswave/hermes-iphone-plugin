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

    def snapshot_state(self, udid: str | None = None, include_screenshot: bool = False, limit: int = 30) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        tree = tree_result["data"]["tree"]
        payload: dict[str, Any] = {
            "bundle_id": tree.get("bundle_id"),
            "name": tree.get("name"),
            "element_count": tree.get("element_count"),
            "truncated": tree.get("truncated"),
            "elements": tree.get("elements", [])[:limit],
            "udid": udid,
        }
        if include_screenshot:
            shot = self.screenshot(udid=udid)
            payload["screenshot"] = (shot.get("data") or {}).get("path") if shot.get("ok") else None
            if not shot.get("ok"):
                payload["screenshot_error"] = shot.get("error") or shot.get("message")
        return {"ok": True, "data": payload, "meta": {"backend": getattr(self.backend, "name", "unknown")}}

    def select_suggestion(self, query: str, udid: str | None = None) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        elements = (tree_result.get("data") or {}).get("tree", {}).get("elements", [])
        normalized_query = query.strip().casefold()
        candidates = []
        for element in elements:
            if element.get("type") not in {"cell", "button", "statictext"}:
                continue
            label = str(element.get("label") or element.get("name") or element.get("value") or "").strip()
            normalized_label = label.casefold()
            if normalized_query and normalized_query in normalized_label:
                score = 0
                if normalized_label == normalized_query:
                    score += 100
                elif normalized_label.startswith(normalized_query):
                    score += 60
                else:
                    score += 25
                if "maybe:" in normalized_label:
                    score += 20
                if element.get("type") == "cell":
                    score += 10
                candidates.append((score, element, label))
        if not candidates:
            return {"ok": False, "error": "suggestion_not_found", "message": f"No visible suggestion matched {query!r}", "data": {"query": query}}
        candidates.sort(key=lambda item: -item[0])
        _score, element, label = candidates[0]
        tapped = self.tap_element(element, udid=udid)
        if tapped.get("ok"):
            tapped.setdefault("data", {})["suggestion"] = {"label": label, "element": element}
        return tapped

    def dismiss_keyboard(self, udid: str | None = None) -> dict[str, Any]:
        for text in ("Done", "Hide keyboard", "Return"):
            tapped = self.tap_text(text, udid=udid)
            if tapped.get("ok"):
                tapped.setdefault("data", {})["dismissed_by"] = text
                return tapped
        return {"ok": False, "error": "keyboard_dismiss_control_not_found", "message": "No visible Done/Hide keyboard/Return control was found.", "data": {"udid": udid}}

    def go_back(self, udid: str | None = None) -> dict[str, Any]:
        for text in ("Back", "Messages", "Cancel", "Close"):
            found = self.find_element(text=text, element_type="button", enabled=True, udid=udid)
            if found.get("ok"):
                tapped = self.tap_element(found["data"]["element"], udid=udid)
                if tapped.get("ok"):
                    tapped.setdefault("data", {})["back_control"] = text
                return tapped
        return {"ok": False, "error": "back_control_not_found", "message": "No visible Back/Messages/Cancel/Close button was found.", "data": {"udid": udid}}

    def recover_to_home_or_app(self, bundle_id: str | None = None, udid: str | None = None) -> dict[str, Any]:
        home = self.press_button("home", udid=udid)
        if not home.get("ok"):
            return home
        if not bundle_id:
            return {"ok": True, "data": {"recovered_to": "home", "udid": udid}, "meta": home.get("meta", {})}
        launched = self.launch_app(bundle_id=bundle_id, udid=udid)
        if launched.get("ok"):
            launched.setdefault("data", {})["recovered_from_home"] = True
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

    def open_messages_thread(self, contact: str, udid: str | None = None) -> dict[str, Any]:
        launched = self.launch_or_focus("com.apple.MobileSMS", udid=udid)
        if not launched.get("ok"):
            return launched
        visible = self.find_element(text=contact, element_type="cell", enabled=True, udid=udid)
        if visible.get("ok"):
            tapped = self.tap_element(visible["data"]["element"], udid=udid)
            if tapped.get("ok"):
                tapped.setdefault("data", {})["opened_thread"] = contact
                tapped.setdefault("data", {})["method"] = "visible_thread_cell"
            return tapped
        search = self.find_element(text="Search", enabled=True, udid=udid)
        if not search.get("ok"):
            return {"ok": False, "error": "messages_thread_not_found", "message": f"No visible Messages thread or Search field matched {contact!r}.", "data": {"contact": contact, "launch": launched}}
        tapped_search = self.tap_element(search["data"]["element"], udid=udid)
        if not tapped_search.get("ok"):
            return tapped_search
        typed = self.type_text(contact, udid=udid)
        if not typed.get("ok"):
            return typed
        time.sleep(0.5)
        result = self.select_suggestion(contact, udid=udid)
        if result.get("ok"):
            result.setdefault("data", {})["opened_thread"] = contact
            result.setdefault("data", {})["method"] = "search_suggestion"
            return result
        return {"ok": False, "error": "messages_thread_not_found", "message": f"Could not open Messages thread for {contact!r} after searching.", "data": {"contact": contact, "last": result}}

    def read_recent_messages(self, limit: int = 10, udid: str | None = None) -> dict[str, Any]:
        tree_result = self._tree(udid=udid)
        if not tree_result.get("ok"):
            return tree_result
        tree = tree_result["data"]["tree"]
        if tree.get("bundle_id") != "com.apple.MobileSMS":
            return {"ok": False, "error": "messages_not_foreground", "message": "Messages is not the foreground app.", "data": {"bundle_id": tree.get("bundle_id"), "name": tree.get("name")}}
        ignored = {"messages", "compose", "edit", "search", "send", "message", "imessage", "to:", "to", "back", "cancel"}
        messages: list[dict[str, Any]] = []
        for element in tree.get("elements", []):
            label = str(element.get("label") or element.get("value") or element.get("name") or "").strip()
            if not label or label.casefold() in ignored:
                continue
            if element.get("type") not in {"statictext", "cell", "textview", "textfield"}:
                continue
            bounds = element.get("bounds") or {}
            try:
                if int(bounds.get("y", 0)) < 120:
                    continue
            except Exception:
                pass
            direction = "unknown"
            try:
                center_x = int((element.get("center") or {}).get("x", 0))
                width = int(bounds.get("width", 0))
                if center_x and width:
                    screen_mid = 390 / 2
                    direction = "outbound" if center_x > screen_mid else "inbound"
            except Exception:
                direction = "unknown"
            messages.append({"text": label, "direction": direction, "element": element})
        recent = messages[-max(0, limit):]
        return {"ok": True, "data": {"messages": recent, "count": len(recent), "available_count": len(messages), "udid": udid}, "meta": {"backend": getattr(self.backend, "name", "unknown")}}

    def prepare_current_message_reply(self, body: str, udid: str | None = None) -> dict[str, Any]:
        current = self.current_app(udid=udid)
        if not current.get("ok"):
            return current
        if (current.get("data") or {}).get("bundle_id") != "com.apple.MobileSMS":
            return {"ok": False, "error": "messages_not_foreground", "message": "Open a Messages thread before preparing a reply.", "data": current.get("data")}
        body_field = None
        for candidate in ("iMessage", "Message", "messageBodyField"):
            typed_body = self.type_into_field(candidate, body, udid=udid)
            if typed_body.get("ok"):
                body_field = typed_body
                break
        if body_field is None:
            return typed_body
        screenshot = self.screenshot(udid=udid)
        screenshot_path = (screenshot.get("data") or {}).get("path") if screenshot.get("ok") else None
        send = self.find_element(text="Send", element_type="button", enabled=True, udid=udid)
        if not send.get("ok"):
            return send
        element = send["data"]["element"]
        context = self.read_recent_messages(limit=5, udid=udid)
        payload = {"to": "current Messages thread", "body_length": len(body), "udid": udid, "send_element": element, "screenshot_before_send": screenshot_path, "thread_context": (context.get("data") or {})}
        prepared = self.policy.prepare("send_text", payload)
        self._log_action("prepare_current_message_reply", {"to": payload["to"], "body_length": len(body), "udid": udid, "send_element": element, "screenshot_before_send": screenshot_path})
        return {
            **prepared,
            "data": {"to": payload["to"], "body_length": len(body), "screenshot_before_send": screenshot_path, "send_element": element, "thread_context": payload["thread_context"], "udid": udid},
            "next_step": "Ask the user to approve sending this reply, then call iphone_confirm_prepared_action with the token.",
        }

    def reply_current_message_thread(
        self,
        body: str,
        udid: str | None = None,
        approval_fn: Callable[..., str] | None = None,
    ) -> dict[str, Any]:
        prepared = self.prepare_current_message_reply(body=body, udid=udid)
        if not prepared.get("ok"):
            return prepared
        approval = self._request_send_approval(
            command=f"Send iMessage/SMS reply in current thread ({len(body)} characters)",
            description="reply_current_message_thread",
            approval_fn=approval_fn,
        )
        if approval not in {"once", "session", "always"}:
            error = "approval_denied" if approval == "deny" else "approval_required"
            return {
                "ok": False,
                "error": error,
                "approval": approval,
                "message": "Hermes approval denied or is unavailable; the reply draft remains unsent.",
                "staged": True,
                "token": prepared.get("token"),
                "data": prepared.get("data"),
                "next_step": "Use the fallback token with iphone_confirm_prepared_action only after explicit approval.",
            }
        sent = self.confirm_prepared_action(prepared["token"], udid=udid)
        if sent.get("ok"):
            sent["approval"] = approval
        return sent

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
