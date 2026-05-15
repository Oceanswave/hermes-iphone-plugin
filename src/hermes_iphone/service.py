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
        return {
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

    def list_devices(self) -> dict[str, Any]:
        return self._result(self.backend.list_devices())
    def screenshot(self, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.screenshot(udid=udid))
    def open_url(self, url: str, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.open_url(url=url, udid=udid))
    def launch_app(self, bundle_id: str, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.launch_app(bundle_id=bundle_id, udid=udid))
    def tap(self, x: int, y: int, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.tap(x=x, y=y, udid=udid))
    def type_text(self, text: str, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.type_text(text=text, udid=udid))
    def press_button(self, button: str, udid: str | None = None) -> dict[str, Any]:
        return self._result(self.backend.press_button(button=button, udid=udid))
