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
    _register(ctx, "iphone_screenshot", "Capture a screenshot from the attached iPhone when backend support is available.", {"udid": UDID}, [], lambda a: _service().screenshot(udid=a.get("udid")))
    _register(ctx, "iphone_open_url", "Open a URL on the attached iPhone.", {"url": {"type": "string"}, "udid": UDID}, ["url"], lambda a: _service().open_url(url=a["url"], udid=a.get("udid")))
    _register(ctx, "iphone_launch_app", "Launch an iOS app by bundle identifier.", {"bundle_id": {"type": "string"}, "udid": UDID}, ["bundle_id"], lambda a: _service().launch_app(bundle_id=a["bundle_id"], udid=a.get("udid")))
    _register(ctx, "iphone_tap", "Tap a screen coordinate on the attached iPhone.", {"x": {"type": "integer"}, "y": {"type": "integer"}, "udid": UDID}, ["x", "y"], lambda a: _service().tap(x=int(a["x"]), y=int(a["y"]), udid=a.get("udid")))
    _register(ctx, "iphone_type_text", "Type text into the currently focused iPhone field.", {"text": {"type": "string"}, "udid": UDID}, ["text"], lambda a: _service().type_text(text=a["text"], udid=a.get("udid")))
    _register(ctx, "iphone_press_button", "Press an iPhone system button such as home, lock, volume_up, or volume_down.", {"button": {"type": "string", "enum": ["home", "lock", "volume_up", "volume_down"]}, "udid": UDID}, ["button"], lambda a: _service().press_button(button=a["button"], udid=a.get("udid")))
    _register(ctx, "iphone_prepare_text", "Prepare a text-message action. This never sends; it returns a one-time confirmation token.", {"to": {"type": "string"}, "body": {"type": "string"}}, ["to", "body"], lambda a: _policy().prepare("send_text", {"to": a["to"], "body": a["body"]}))
    _register(ctx, "iphone_confirm_prepared_action", "Confirm a prepared external action after explicit user approval. Tokens are one-time use.", {"token": {"type": "string"}}, ["token"], lambda a: _policy().confirm(token=a["token"]))

    skill_path = Path(__file__).parent / "skills" / "operator" / "SKILL.md"
    if skill_path.exists():
        ctx.register_skill("operator", skill_path, description="Operate attached iPhones safely through hermes-iphone-plugin tools.")
