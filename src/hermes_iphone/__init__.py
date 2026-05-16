from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .safety import SafetyPolicy
from .schemas import UDID, schema
from .service import IphoneService
from .state import PluginState

TOOLSET = "iphone"


def _json(fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], str]:
    def handler(args: dict[str, Any], **kwargs: Any) -> str:
        try:
            return json.dumps(fn(args or {}), sort_keys=True)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "handler_exception", "message": str(exc)}, sort_keys=True)
    return handler


def _service() -> IphoneService:
    return IphoneService()


def _policy() -> SafetyPolicy:
    return SafetyPolicy(state=PluginState())


def _register(ctx, name: str, description: str, properties: dict | None, required: list[str] | None, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    ctx.register_tool(
        name=name,
        toolset=TOOLSET,
        schema=schema(name, description, properties, required),
        handler=_json(fn),
        description=description,
        emoji="📱",
    )


def register(ctx) -> None:
    _register(ctx, "iphone_status", "Report iPhone plugin/backend readiness and safety policy.", {}, [], lambda a: _service().status())
    _register(ctx, "iphone_list_devices", "List attached/trusted iPhones visible to the native backend.", {}, [], lambda a: _service().list_devices())
    _register(ctx, "iphone_ensure_wda", "Ensure RemoteXPC/tunneld and WebDriverAgent are ready for WDA-backed iPhone controls.", {"udid": UDID}, [], lambda a: _service().ensure_wda(udid=a.get("udid")))
    _register(ctx, "iphone_screenshot", "Capture a screenshot from the attached iPhone when backend support is available.", {"udid": UDID}, [], lambda a: _service().screenshot(udid=a.get("udid")))
    _register(ctx, "iphone_screen_info", "Return iPhone screen/window size, orientation, and WDA status.", {"udid": UDID}, [], lambda a: _service().screen_info(udid=a.get("udid")))
    _register(ctx, "iphone_source", "Return the current WebDriverAgent XML UI hierarchy/source tree.", {"udid": UDID}, [], lambda a: _service().source(udid=a.get("udid")))
    _register(ctx, "iphone_tree", "Return a compact semantic accessibility tree parsed from WDA source.", {"udid": UDID}, [], lambda a: _service().tree(udid=a.get("udid")))
    _register(ctx, "iphone_find_element", "Find visible iPhone UI elements by text/type/enabled state.", {"text": {"type": "string"}, "element_type": {"type": "string"}, "enabled": {"type": "boolean"}, "visible": {"type": "boolean", "default": True}, "udid": UDID}, [], lambda a: _service().find_element(text=a.get("text"), element_type=a.get("element_type"), enabled=a.get("enabled"), visible=a.get("visible", True), udid=a.get("udid")))
    _register(ctx, "iphone_tap_text", "Tap the center of the first visible enabled UI element matching text.", {"text": {"type": "string"}, "element_type": {"type": "string"}, "udid": UDID}, ["text"], lambda a: _service().tap_text(text=a["text"], element_type=a.get("element_type"), udid=a.get("udid")))
    _register(ctx, "iphone_tap_element", "Tap an element by id from the current semantic tree.", {"element_id": {"type": "string"}, "udid": UDID}, ["element_id"], lambda a: _service().tap_element_id(element_id=a["element_id"], udid=a.get("udid")))
    _register(ctx, "iphone_describe_screen", "Return a compact human-readable summary of the current screen.", {"limit": {"type": "integer", "default": 20}, "udid": UDID}, [], lambda a: _service().describe_screen(limit=int(a.get("limit", 20)), udid=a.get("udid")))
    _register(ctx, "iphone_last_trace", "Return the most recent iPhone automation trace folder and metadata.", {}, [], lambda a: _service().last_trace())
    _register(ctx, "iphone_action_logs", "Return recent redacted iPhone action log entries.", {"limit": {"type": "integer", "default": 10}}, [], lambda a: _service().action_logs(limit=int(a.get("limit", 10))))
    _register(ctx, "iphone_wait_for_text", "Wait until text appears in the iPhone UI hierarchy.", {"text": {"type": "string"}, "timeout_seconds": {"type": "number", "default": 10.0}, "poll_seconds": {"type": "number", "default": 0.5}, "udid": UDID}, ["text"], lambda a: _service().wait_for_text(text=a["text"], timeout_seconds=float(a.get("timeout_seconds", 10.0)), poll_seconds=float(a.get("poll_seconds", 0.5)), udid=a.get("udid")))
    _register(ctx, "iphone_type_into_field", "Tap a field by label/name and type text into it.", {"field": {"type": "string"}, "text": {"type": "string"}, "udid": UDID}, ["field", "text"], lambda a: _service().type_into_field(field=a["field"], text=a["text"], udid=a.get("udid")))
    _register(ctx, "iphone_current_app", "Return the foreground app name and bundle identifier from WDA source.", {"udid": UDID}, [], lambda a: _service().current_app(udid=a.get("udid")))
    _register(ctx, "iphone_launch_or_focus", "Launch an app unless it is already foreground according to WDA source.", {"bundle_id": {"type": "string"}, "udid": UDID}, ["bundle_id"], lambda a: _service().launch_or_focus(bundle_id=a["bundle_id"], udid=a.get("udid")))
    _register(ctx, "iphone_open_url", "Open a URL on the attached iPhone.", {"url": {"type": "string"}, "udid": UDID}, ["url"], lambda a: _service().open_url(url=a["url"], udid=a.get("udid")))
    _register(ctx, "iphone_launch_app", "Launch an iOS app by bundle identifier.", {"bundle_id": {"type": "string"}, "udid": UDID}, ["bundle_id"], lambda a: _service().launch_app(bundle_id=a["bundle_id"], udid=a.get("udid")))
    _register(ctx, "iphone_tap", "Tap a screen coordinate on the attached iPhone.", {"x": {"type": "integer"}, "y": {"type": "integer"}, "udid": UDID}, ["x", "y"], lambda a: _service().tap(x=int(a["x"]), y=int(a["y"]), udid=a.get("udid")))
    _register(ctx, "iphone_swipe", "Swipe from one screen coordinate to another on the attached iPhone.", {"start_x": {"type": "integer"}, "start_y": {"type": "integer"}, "end_x": {"type": "integer"}, "end_y": {"type": "integer"}, "duration": {"type": "number", "default": 0.2}, "udid": UDID}, ["start_x", "start_y", "end_x", "end_y"], lambda a: _service().swipe(start_x=int(a["start_x"]), start_y=int(a["start_y"]), end_x=int(a["end_x"]), end_y=int(a["end_y"]), duration=float(a.get("duration", 0.2)), udid=a.get("udid")))
    _register(ctx, "iphone_type_text", "Type text into the currently focused iPhone field.", {"text": {"type": "string"}, "udid": UDID}, ["text"], lambda a: _service().type_text(text=a["text"], udid=a.get("udid")))
    _register(ctx, "iphone_press_button", "Press an iPhone system button such as home, lock, volume_up, or volume_down.", {"button": {"type": "string", "enum": ["home", "lock", "volume_up", "volume_down"]}, "udid": UDID}, ["button"], lambda a: _service().press_button(button=a["button"], udid=a.get("udid")))
    _register(ctx, "iphone_prepare_text", "Compose a text message in Messages and stage the Send tap behind a one-time confirmation token. This never taps Send.", {"to": {"type": "string"}, "body": {"type": "string"}, "udid": UDID}, ["to", "body"], lambda a: _service().prepare_text(to=a["to"], body=a["body"], udid=a.get("udid")))
    _register(ctx, "iphone_send_text", "Send a text message via Messages after Hermes built-in approval (/approve, /approve session, /approve always, or /yolo). Stages and verifies the draft before tapping Send.", {"to": {"type": "string"}, "body": {"type": "string"}, "udid": UDID}, ["to", "body"], lambda a: _service().send_text(to=a["to"], body=a["body"], udid=a.get("udid")))
    _register(ctx, "iphone_confirm_prepared_action", "Confirm a prepared external action after explicit user approval. Tokens are one-time use; send_text taps Send.", {"token": {"type": "string"}, "udid": UDID}, ["token"], lambda a: _service().confirm_prepared_action(token=a["token"], udid=a.get("udid")))

    skill_path = Path(__file__).parent / "skills" / "operator" / "SKILL.md"
    if skill_path.exists():
        ctx.register_skill("operator", skill_path, description="Operate attached iPhones safely through hermes-iphone-plugin tools.")
