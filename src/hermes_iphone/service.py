from __future__ import annotations

from typing import Any

from .backends import IphoneBackend, make_backend


class IphoneService:
    def __init__(self, backend: IphoneBackend | None = None):
        self.backend = backend or make_backend()

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
