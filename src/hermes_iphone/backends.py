from __future__ import annotations

import asyncio
import importlib.util
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class BackendResult:
    ok: bool
    data: Any = None
    error: str | None = None
    message: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {"ok": self.ok}
        if self.data is not None:
            payload["data"] = self.data
        if self.error:
            payload["error"] = self.error
        if self.message:
            payload["message"] = self.message
        if self.meta:
            payload["meta"] = self.meta
        return payload


class IphoneBackend(Protocol):
    name: str
    def list_devices(self) -> BackendResult: ...
    def screenshot(self, udid: str | None = None) -> BackendResult: ...
    def open_url(self, url: str, udid: str | None = None) -> BackendResult: ...
    def launch_app(self, bundle_id: str, udid: str | None = None) -> BackendResult: ...
    def tap(self, x: int, y: int, udid: str | None = None) -> BackendResult: ...
    def type_text(self, text: str, udid: str | None = None) -> BackendResult: ...
    def press_button(self, button: str, udid: str | None = None) -> BackendResult: ...


class NullBackend:
    name = "null"

    def __init__(self, reason: str):
        self.reason = reason

    def _unavailable(self, capability: str) -> BackendResult:
        return BackendResult(
            ok=False,
            error="backend_unavailable",
            message=f"iPhone backend is unavailable for {capability}: {self.reason}",
            meta={"backend": self.name},
        )

    def list_devices(self) -> BackendResult:
        return self._unavailable("list_devices")
    def screenshot(self, udid: str | None = None) -> BackendResult:
        return self._unavailable("screenshot")
    def open_url(self, url: str, udid: str | None = None) -> BackendResult:
        return self._unavailable("open_url")
    def launch_app(self, bundle_id: str, udid: str | None = None) -> BackendResult:
        return self._unavailable("launch_app")
    def tap(self, x: int, y: int, udid: str | None = None) -> BackendResult:
        return self._unavailable("tap")
    def type_text(self, text: str, udid: str | None = None) -> BackendResult:
        return self._unavailable("type_text")
    def press_button(self, button: str, udid: str | None = None) -> BackendResult:
        return self._unavailable("press_button")


class PyMobileDeviceBackend:
    """Native Python backend built around the pymobiledevice3 library.

    This intentionally imports pymobiledevice3 lazily and reflectively so the
    plugin can be installed and its status tool can run without the optional
    iPhone stack present. Runtime UI methods return controlled capability errors
    until the host has WebDriverAgent/device-control dependencies configured.
    """

    name = "pymobiledevice3"

    def __init__(self, artifact_root: Path | None = None):
        self.artifact_root = artifact_root or Path.home() / ".hermes" / "plugins" / "iphone" / "artifacts"

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("pymobiledevice3") is not None

    def list_devices(self) -> BackendResult:
        try:
            from pymobiledevice3.usbmux import list_devices  # type: ignore
            maybe_devices = list_devices()
            if inspect.isawaitable(maybe_devices):
                devices_iter = asyncio.run(maybe_devices)
            else:
                devices_iter = maybe_devices
            devices = []
            for dev in devices_iter:
                devices.append({
                    "udid": getattr(dev, "serial", None) or getattr(dev, "udid", None),
                    "connection_type": str(getattr(dev, "connection_type", "usb")),
                    "raw": repr(dev),
                })
            return BackendResult(ok=True, data=devices, meta={"backend": self.name})
        except Exception as exc:
            message = str(exc) or repr(exc) or exc.__class__.__name__
            if exc.__class__.__name__ == "ConnectionFailedToUsbmuxdError":
                message = "Could not connect to usbmuxd. Start/repair usbmuxd and make sure the iPhone is attached and trusted."
            elif isinstance(exc, PermissionError):
                message = (
                    "Permission denied connecting to usbmuxd. The iPhone is visible, but the usbmuxd socket is not writable "
                    "by this Hermes user. Fix the system usbmuxd/socket permissions, for example with a sudo systemd override "
                    "or socket mode/group change, then retry iphone_list_devices."
                )
            return BackendResult(ok=False, error="list_devices_failed", message=message, meta={"backend": self.name, "exception": exc.__class__.__name__})

    def _not_wired(self, capability: str) -> BackendResult:
        return BackendResult(
            ok=False,
            error="capability_not_implemented",
            message=(
                f"{capability} needs the native WebDriverAgent / device-control adapter wired. "
                "The plugin is installed and the backend is detected, but this MVP has only device discovery and safe tool plumbing."
            ),
            meta={"backend": self.name},
        )

    def screenshot(self, udid: str | None = None) -> BackendResult:
        return self._not_wired("screenshot")
    def open_url(self, url: str, udid: str | None = None) -> BackendResult:
        return self._not_wired("open_url")
    def launch_app(self, bundle_id: str, udid: str | None = None) -> BackendResult:
        return self._not_wired("launch_app")
    def tap(self, x: int, y: int, udid: str | None = None) -> BackendResult:
        return self._not_wired("tap")
    def type_text(self, text: str, udid: str | None = None) -> BackendResult:
        return self._not_wired("type_text")
    def press_button(self, button: str, udid: str | None = None) -> BackendResult:
        return self._not_wired("press_button")


def make_backend() -> IphoneBackend:
    if PyMobileDeviceBackend.available():
        return PyMobileDeviceBackend()
    return NullBackend("optional Python package pymobiledevice3 is not installed; install hermes-iphone-plugin[iphone] and ensure the iPhone is trusted/pairable")
