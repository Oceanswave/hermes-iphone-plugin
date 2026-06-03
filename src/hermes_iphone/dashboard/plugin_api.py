from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from hermes_iphone.dashboard import ensure_dashboard_installed
from hermes_iphone.service import IphoneService

router = APIRouter()

_READS: dict[str, str] = {
    "status": "status",
    "devices": "list_devices",
    "screen": "screen_info",
    "current-app": "current_app",
    "snapshot": "snapshot_state",
    "tree": "tree",
    "describe": "describe_screen",
    "last-trace": "last_trace",
    "action-logs": "action_logs",
}

_ACTIONS: dict[str, str] = {
    "ensure-wda": "ensure_wda",
    "screenshot": "screenshot",
    "home": "press_button",
    "lock": "press_button",
    "launch-app": "launch_app",
    "launch-messages": "launch_app",
    "launch-safari": "launch_app",
    "open-url": "open_url",
    "dismiss-keyboard": "dismiss_keyboard",
    "go-back": "go_back",
    "recover-home": "recover_to_home_or_app",
}

_ACTION_DEFAULTS: dict[str, dict[str, Any]] = {
    "home": {"button": "home"},
    "lock": {"button": "lock"},
    "launch-messages": {"bundle_id": "com.apple.MobileSMS"},
    "launch-safari": {"bundle_id": "com.apple.mobilesafari"},
}

_ACTION_EXTRA_FIELDS: dict[str, tuple[str, ...]] = {
    "launch-app": ("bundle_id",),
    "open-url": ("url",),
    "recover-home": ("bundle_id",),
}

_SECRET_KEY_PARTS = ("token", "secret", "password", "authorization", "body")
_TEXT_VALUE_KEYS = {"text", "value", "message", "body", "recipient", "to"}


class QuickActionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., description="Quick action key, e.g. ensure-wda, home, launch-messages.")
    udid: str | None = None
    confirm: bool = False
    bundle_id: str | None = None
    url: str | None = None


def _service() -> IphoneService:
    return IphoneService()


def _call(method_name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    service = _service()
    method = getattr(service, method_name, None)
    if method is None:
        raise HTTPException(status_code=404, detail=f"Unknown iPhone service method: {method_name}")
    args = args or {}
    try:
        result = method(**args)
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        return {"ok": False, "error": exc.__class__.__name__, "message": str(exc)}
    if not isinstance(result, dict):
        return {"ok": False, "error": "unexpected_result", "message": "iPhone service returned a non-object payload", "data": result}
    return result


def _safe_call(method_name: str, args: dict[str, Any] | None = None, timeout_seconds: float = 3.0) -> dict[str, Any]:
    try:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_call, method_name, args)
        try:
            return future.result(timeout=timeout_seconds)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
    except FutureTimeoutError:
        return {
            "ok": False,
            "error": "timeout",
            "message": f"{method_name} did not return within {timeout_seconds:g}s; run the read directly for full detail.",
            "method": method_name,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "method": method_name}


def _display_payload(value: Any) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if any(part in lowered for part in _SECRET_KEY_PARTS):
                safe[key_text] = "[REDACTED]"
            elif lowered in _TEXT_VALUE_KEYS and isinstance(item, str) and len(item) > 16:
                safe[key_text] = f"[REDACTED_TEXT:{len(item)}]"
            elif lowered in {"source", "xml"} and isinstance(item, str) and len(item) > 500:
                safe[key_text] = f"[REDACTED_XML:{len(item)}]"
            else:
                safe[key_text] = _display_payload(item)
        return safe
    if isinstance(value, list):
        return [_display_payload(item) for item in value]
    return value


def _with_display_payload(payload: dict[str, Any]) -> dict[str, Any]:
    copy = dict(payload)
    copy["display_payload"] = _display_payload(copy)
    return copy


def _common_args(udid: str | None = None) -> dict[str, Any]:
    return {"udid": udid} if udid else {}


@router.get("/install")
def install_assets() -> dict[str, Any]:
    return ensure_dashboard_installed()


@router.get("/tools")
def tools() -> dict[str, Any]:
    return {
        "ok": True,
        "reads": _READS,
        "quick_actions": _ACTIONS,
        "action_defaults": _ACTION_DEFAULTS,
        "action_extra_fields": _ACTION_EXTRA_FIELDS,
        "safety": "Dashboard quick actions require confirm=true. Text-send prepare/confirm tools are intentionally excluded from this dashboard surface.",
    }


@router.get("/overview")
def overview(
    udid: str | None = None,
    include_tree: bool = Query(False, description="Include compact semantic tree. Defaults false to keep refreshes lightweight."),
) -> dict[str, Any]:
    args = _common_args(udid)
    sections: dict[str, Any] = {
        "status": _safe_call("status"),
        "devices": _safe_call("list_devices"),
        "screen": _safe_call("screen_info", args),
        "current_app": _safe_call("current_app", args),
        "snapshot": _safe_call("snapshot_state", {**args, "include_screenshot": False, "limit": 20}),
        "last_trace": _safe_call("last_trace"),
        "action_logs": _safe_call("action_logs", {"limit": 5}),
    }
    if include_tree:
        sections["tree"] = _safe_call("tree", args)
    return _with_display_payload({"ok": True, "udid": udid, "sections": sections})


@router.get("/read/{read_key}")
def read(read_key: str, udid: str | None = None, limit: int = 20, include_screenshot: bool = False) -> dict[str, Any]:
    method_name = _READS.get(read_key)
    if not method_name:
        raise HTTPException(status_code=404, detail=f"Unknown read key: {read_key}")
    args = _common_args(udid)
    if method_name == "describe_screen":
        args["limit"] = limit
    elif method_name == "action_logs":
        args = {"limit": limit}
    elif method_name == "snapshot_state":
        args.update({"include_screenshot": include_screenshot, "limit": limit})
    return _with_display_payload(_call(method_name, args))


@router.post("/quick-action")
def quick_action(body: QuickActionBody) -> dict[str, Any]:
    method_name = _ACTIONS.get(body.action)
    if not method_name:
        raise HTTPException(status_code=404, detail=f"Unknown quick action: {body.action}")
    if not body.confirm:
        return {
            "ok": False,
            "error": "confirmation_required",
            "message": "Dashboard iPhone quick actions require confirm=true. Check the confirmation box and retry.",
            "action": body.action,
        }
    args = _common_args(body.udid)
    args.update(_ACTION_DEFAULTS.get(body.action, {}))
    for field in _ACTION_EXTRA_FIELDS.get(body.action, ()):
        value = getattr(body, field)
        if value is not None:
            args[field] = value
    return _with_display_payload(_call(method_name, args))


# Keep a tiny self-check for import-time debugging from the dashboard loader.
def debug_catalog_json() -> str:
    return json.dumps({"reads": sorted(_READS), "actions": sorted(_ACTIONS)}, sort_keys=True)
