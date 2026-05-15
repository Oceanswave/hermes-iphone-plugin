from __future__ import annotations

import asyncio
import importlib.util
import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
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

    def _run_async(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return asyncio.run(value)
        return value

    def _service_provider(self, udid: str | None = None) -> Any:
        from pymobiledevice3.lockdown import create_using_usbmux  # type: ignore

        return self._run_async(create_using_usbmux(serial=udid, autopair=True))

    async def _service_provider_async(self, udid: str | None = None) -> Any:
        from pymobiledevice3.lockdown import create_using_usbmux  # type: ignore

        provider = create_using_usbmux(serial=udid, autopair=True)
        if inspect.isawaitable(provider):
            return await provider
        return provider

    def _error(self, capability: str, exc: Exception) -> BackendResult:
        message = str(exc) or repr(exc) or exc.__class__.__name__
        if exc.__class__.__name__ == "WdaError":
            message = (
                f"{capability} requires a reachable WebDriverAgent (WDA) service on the iPhone. "
                f"pymobiledevice3 reported: {message}"
            )
        elif exc.__class__.__name__ == "InvalidServiceError":
            message = (
                f"{capability} requires an iOS developer/device-control service that this phone is not currently exposing. "
                "Enable Developer Mode / Web Inspector / Remote Automation as appropriate, ensure the device is trusted, "
                f"then retry. pymobiledevice3 reported: {message}"
            )
        return BackendResult(
            ok=False,
            error=f"{capability}_failed",
            message=message,
            meta={"backend": self.name, "exception": exc.__class__.__name__},
        )

    async def _wda_session(self, udid: str | None = None) -> tuple[Any, str]:
        from pymobiledevice3.services.wda import WdaServiceClient  # type: ignore

        client = WdaServiceClient(await self._service_provider_async(udid), timeout=10.0)
        session_id = await client.start_session()
        return client, session_id

    def screenshot(self, udid: str | None = None) -> BackendResult:
        async def run() -> bytes:
            from pymobiledevice3.services.screenshot import ScreenshotService  # type: ignore

            service = ScreenshotService(await self._service_provider_async(udid))
            return await service.take_screenshot()

        try:
            image = self._run_async(run())
            self.artifact_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            udid_part = udid or "default"
            path = self.artifact_root / f"iphone-screenshot-{udid_part}-{stamp}.png"
            path.write_bytes(image)
            return BackendResult(
                ok=True,
                data={"path": str(path), "size_bytes": len(image), "udid": udid},
                meta={"backend": self.name},
            )
        except Exception as exc:
            return self._error("screenshot", exc)

    def open_url(self, url: str, udid: str | None = None) -> BackendResult:
        async def run() -> None:
            from pymobiledevice3.cli.webinspector import launch_task  # type: ignore

            await launch_task(await self._service_provider_async(udid), url, 5.0)

        try:
            self._run_async(run())
            return BackendResult(ok=True, data={"url": url, "udid": udid}, meta={"backend": self.name})
        except Exception as exc:
            return self._error("open_url", exc)

    def launch_app(self, bundle_id: str, udid: str | None = None) -> BackendResult:
        async def run() -> int:
            from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider  # type: ignore
            from pymobiledevice3.services.dvt.instruments.process_control import ProcessControl  # type: ignore

            async with DvtProvider(await self._service_provider_async(udid)) as dvt:
                async with ProcessControl(dvt) as process_control:
                    return await process_control.launch(bundle_id)

        try:
            pid = self._run_async(run())
            return BackendResult(ok=True, data={"bundle_id": bundle_id, "pid": pid, "udid": udid}, meta={"backend": self.name})
        except Exception as exc:
            return self._error("launch_app", exc)

    def tap(self, x: int, y: int, udid: str | None = None) -> BackendResult:
        async def run() -> None:
            client, session_id = await self._wda_session(udid)
            await client._request_json("POST", f"/session/{session_id}/wda/tap/0", {"x": x, "y": y})

        try:
            self._run_async(run())
            return BackendResult(ok=True, data={"x": x, "y": y, "udid": udid}, meta={"backend": self.name})
        except Exception as exc:
            return self._error("tap", exc)

    def type_text(self, text: str, udid: str | None = None) -> BackendResult:
        async def run() -> None:
            client, session_id = await self._wda_session(udid)
            await client.send_keys(text, session_id=session_id)

        try:
            self._run_async(run())
            return BackendResult(ok=True, data={"text_length": len(text), "udid": udid}, meta={"backend": self.name})
        except Exception as exc:
            return self._error("type_text", exc)

    def press_button(self, button: str, udid: str | None = None) -> BackendResult:
        async def run() -> None:
            client, session_id = await self._wda_session(udid)
            await client.press_button(button, session_id=session_id)

        try:
            self._run_async(run())
            return BackendResult(ok=True, data={"button": button, "udid": udid}, meta={"backend": self.name})
        except Exception as exc:
            return self._error("press_button", exc)


def make_backend() -> IphoneBackend:
    if PyMobileDeviceBackend.available():
        return PyMobileDeviceBackend()
    return NullBackend("optional Python package pymobiledevice3 is not installed; install hermes-iphone-plugin[iphone] and ensure the iPhone is trusted/pairable")
