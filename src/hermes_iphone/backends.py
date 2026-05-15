from __future__ import annotations

import asyncio
import importlib.util
import inspect
import os
import subprocess
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
    def diagnostics(self, udid: str | None = None) -> BackendResult: ...
    def list_devices(self) -> BackendResult: ...
    def ensure_wda(self, udid: str | None = None) -> BackendResult: ...
    def screenshot(self, udid: str | None = None) -> BackendResult: ...
    def screen_info(self, udid: str | None = None) -> BackendResult: ...
    def source(self, udid: str | None = None) -> BackendResult: ...
    def open_url(self, url: str, udid: str | None = None) -> BackendResult: ...
    def launch_app(self, bundle_id: str, udid: str | None = None) -> BackendResult: ...
    def tap(self, x: int, y: int, udid: str | None = None) -> BackendResult: ...
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.2, udid: str | None = None) -> BackendResult: ...
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
    def diagnostics(self, udid: str | None = None) -> BackendResult:
        return self._unavailable("diagnostics")
    def ensure_wda(self, udid: str | None = None) -> BackendResult:
        return self._unavailable("ensure_wda")
    def screenshot(self, udid: str | None = None) -> BackendResult:
        return self._unavailable("screenshot")
    def screen_info(self, udid: str | None = None) -> BackendResult:
        return self._unavailable("screen_info")
    def source(self, udid: str | None = None) -> BackendResult:
        return self._unavailable("source")
    def open_url(self, url: str, udid: str | None = None) -> BackendResult:
        return self._unavailable("open_url")
    def launch_app(self, bundle_id: str, udid: str | None = None) -> BackendResult:
        return self._unavailable("launch_app")
    def tap(self, x: int, y: int, udid: str | None = None) -> BackendResult:
        return self._unavailable("tap")
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.2, udid: str | None = None) -> BackendResult:
        return self._unavailable("swipe")
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
        # User-visible artifacts should default under the home directory rather
        # than hidden Hermes internals so screenshots are easy to find.
        self.artifact_root = artifact_root or Path.home() / "iphone-screenshots"

    def _default_udid(self, udid: str | None = None) -> str | None:
        return udid or os.environ.get("HERMES_IPHONE_UDID") or None

    def _wda_bundle_id(self) -> str:
        return os.environ.get("HERMES_IPHONE_WDA_BUNDLE_ID", "com.baristalabs.WebDriverAgentRunner.xctrunner")

    def _helper_path(self) -> Path:
        return Path(os.environ.get("HERMES_IPHONE_WDA_HELPER", str(Path.home() / "ensure-iphone-wda.sh")))

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("pymobiledevice3") is not None

    def _wda_ready(self, udid: str | None = None) -> tuple[bool, dict[str, Any] | None, str | None]:
        async def run() -> dict[str, Any]:
            from pymobiledevice3.services.wda import WdaServiceClient  # type: ignore

            client = WdaServiceClient(await self._service_provider_async(udid), timeout=5.0)
            return await client.get_status()

        try:
            status = self._run_async(run())
            return True, status if isinstance(status, dict) else {"status": status}, None
        except Exception as exc:
            return False, None, str(exc) or exc.__class__.__name__

    def _tunneld_ready(self, udid: str | None = None) -> tuple[bool, list[str], str | None]:
        async def run() -> list[str]:
            from pymobiledevice3.tunneld.api import TUNNELD_DEFAULT_ADDRESS, get_tunneld_devices  # type: ignore

            rsds = await get_tunneld_devices(TUNNELD_DEFAULT_ADDRESS)
            ids = [str(getattr(rsd, "udid", "")) for rsd in rsds if getattr(rsd, "udid", None)]
            for rsd in rsds:
                close = getattr(rsd, "close", None)
                if close:
                    maybe = close()
                    if inspect.isawaitable(maybe):
                        await maybe
            return ids

        try:
            ids = self._run_async(run())
            return (self._default_udid(udid) in ids if self._default_udid(udid) else bool(ids)), ids, None
        except Exception as exc:
            return False, [], str(exc) or exc.__class__.__name__

    def diagnostics(self, udid: str | None = None) -> BackendResult:
        resolved_udid = self._default_udid(udid)
        helper = self._helper_path()
        tunneld_ready, tunneld_udids, tunneld_error = self._tunneld_ready(resolved_udid)
        wda_ready, wda_status, wda_error = self._wda_ready(resolved_udid)
        return BackendResult(
            ok=True,
            data={
                "udid": resolved_udid,
                "pymobiledevice3_available": self.available(),
                "artifact_root": str(self.artifact_root),
                "auto_wda_enabled": os.environ.get("HERMES_IPHONE_AUTO_WDA", "1").lower() not in {"0", "false", "no", "off"},
                "wda_helper": {"path": str(helper), "exists": helper.exists(), "executable": os.access(helper, os.X_OK)},
                "wda_bundle_id": self._wda_bundle_id(),
                "tunneld": {"ready": tunneld_ready, "udids": tunneld_udids, "error": tunneld_error},
                "wda": {"ready": wda_ready, "status": wda_status, "error": wda_error},
            },
            meta={"backend": self.name},
        )

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
        # Developer services on iOS 17+ are exposed through RemoteXPC/tunneld.
        # Prefer an already-running tunneld instance when available, then fall
        # back to classic usbmux lockdown for older devices / non-developer APIs.
        try:
            from pymobiledevice3.tunneld.api import TUNNELD_DEFAULT_ADDRESS, get_tunneld_devices  # type: ignore

            rsds = await get_tunneld_devices(TUNNELD_DEFAULT_ADDRESS)
            if rsds:
                if udid:
                    match = next((rsd for rsd in rsds if getattr(rsd, "udid", None) == udid), None)
                    if match is not None:
                        for rsd in rsds:
                            if rsd is not match:
                                await rsd.close()
                        return match
                if len(rsds) == 1 or not udid:
                    selected = rsds[0]
                    for rsd in rsds[1:]:
                        await rsd.close()
                    return selected
        except Exception:
            pass

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
        elif exc.__class__.__name__ == "ConnectionFailedError":
            message = (
                f"{capability} could not connect to the iPhone device-control port. "
                "For WDA-backed actions, make sure WebDriverAgent is installed/running on the phone "
                "and reachable on device port 8100; also verify Developer Mode and pairing. "
                f"pymobiledevice3 reported: {message}"
            )
        elif exc.__class__.__name__ == "InvalidServiceError":
            message = (
                f"{capability} requires an iOS developer/device-control service that this phone is not currently exposing. "
                "Enable Developer Mode / Web Inspector / Remote Automation as appropriate, ensure the device is trusted, "
                "mount the DeveloperDiskImage, and on iOS 17+ start pymobiledevice3 remote tunneld with sudo. "
                f"pymobiledevice3 reported: {message}"
            )
        return BackendResult(
            ok=False,
            error=f"{capability}_failed",
            message=message,
            meta={"backend": self.name, "exception": exc.__class__.__name__},
        )

    def _ensure_wda(self, udid: str | None = None) -> bool:
        return self.ensure_wda(udid).ok

    def ensure_wda(self, udid: str | None = None) -> BackendResult:
        """Best-effort local recovery for WDA-backed controls.

        The helper is intentionally outside the plugin package so the user can
        tune the exact tunneld/WDA commands for their host without editing
        Python code. It must be safe to call repeatedly and avoid duplicate
        runners.
        """
        resolved_udid = self._default_udid(udid)
        ready, status, error = self._wda_ready(resolved_udid)
        if ready:
            return BackendResult(
                ok=True,
                data={"udid": resolved_udid, "wda_ready": True, "already_ready": True, "status": status},
                meta={"backend": self.name},
            )
        if os.environ.get("HERMES_IPHONE_AUTO_WDA", "1").lower() in {"0", "false", "no", "off"}:
            return BackendResult(ok=False, error="auto_wda_disabled", message=error or "WDA is not ready and auto-WDA is disabled", meta={"backend": self.name})
        helper = self._helper_path()
        if not helper.exists():
            return BackendResult(ok=False, error="wda_helper_missing", message=f"WDA helper not found at {helper}", meta={"backend": self.name})
        cmd = [str(helper)]
        if resolved_udid:
            cmd.append(resolved_udid)
        try:
            completed = subprocess.run(cmd, text=True, capture_output=True, timeout=45, check=False)
        except subprocess.TimeoutExpired as exc:
            return BackendResult(ok=False, error="wda_helper_timeout", message=f"WDA helper timed out after {exc.timeout}s", meta={"backend": self.name, "helper": str(helper)})
        except Exception as exc:
            return self._error("ensure_wda", exc)
        retry_ready, retry_status, retry_error = self._wda_ready(resolved_udid)
        return BackendResult(
            ok=completed.returncode == 0 and retry_ready,
            data={
                "udid": resolved_udid,
                "wda_ready": retry_ready,
                "already_ready": False,
                "helper": str(helper),
                "helper_returncode": completed.returncode,
                "helper_stdout": completed.stdout.strip()[-4000:],
                "helper_stderr": completed.stderr.strip()[-4000:],
                "status": retry_status,
            },
            error=None if completed.returncode == 0 and retry_ready else "ensure_wda_failed",
            message="" if completed.returncode == 0 and retry_ready else (retry_error or completed.stderr.strip() or completed.stdout.strip()),
            meta={"backend": self.name},
        )

    async def _wda_session(self, udid: str | None = None) -> tuple[Any, str]:
        from pymobiledevice3.services.wda import WdaServiceClient  # type: ignore

        client = WdaServiceClient(await self._service_provider_async(self._default_udid(udid)), timeout=10.0)
        session_id = await client.start_session()
        return client, session_id

    def screenshot(self, udid: str | None = None) -> BackendResult:
        async def run_wda() -> bytes:
            client, session_id = await self._wda_session(udid)
            return await client.get_screenshot(session_id=session_id)

        async def run_dvt() -> bytes:
            from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider  # type: ignore
            from pymobiledevice3.services.dvt.instruments.screenshot import Screenshot  # type: ignore

            async with DvtProvider(await self._service_provider_async(udid)) as dvt:
                async with Screenshot(dvt) as screenshot:
                    return await screenshot.get_screenshot()

        try:
            transport = "wda"
            try:
                image = self._run_async(run_wda())
            except Exception:
                # WDA is required for interaction, but DVT screenshots are often
                # available as soon as Developer Mode + DDI + tunneld are ready.
                transport = "dvt"
                image = self._run_async(run_dvt())
            self.artifact_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            udid_part = udid or "default"
            path = self.artifact_root / f"iphone-screenshot-{udid_part}-{stamp}.png"
            path.write_bytes(image)
            return BackendResult(
                ok=True,
                data={"path": str(path), "size_bytes": len(image), "udid": udid, "transport": transport},
                meta={"backend": self.name},
            )
        except Exception as exc:
            return self._error("screenshot", exc)

    def screen_info(self, udid: str | None = None) -> BackendResult:
        async def run() -> dict[str, Any]:
            client, session_id = await self._wda_session(udid)
            status = await client.get_status()
            size = await client.get_window_size(session_id=session_id)
            orientation_payload = await client._request_json("GET", f"/session/{session_id}/orientation", None)
            return {
                "window_size": size,
                "orientation": orientation_payload.get("value"),
                "wda_status": status,
                "udid": self._default_udid(udid),
            }

        try:
            return BackendResult(ok=True, data=self._run_async(run()), meta={"backend": self.name})
        except Exception as exc:
            if self._ensure_wda(udid):
                try:
                    return BackendResult(ok=True, data=self._run_async(run()), meta={"backend": self.name, "self_healed_wda": True})
                except Exception as retry_exc:
                    return self._error("screen_info", retry_exc)
            return self._error("screen_info", exc)

    def source(self, udid: str | None = None) -> BackendResult:
        async def run() -> str:
            client, session_id = await self._wda_session(udid)
            return await client.get_source(session_id=session_id)

        try:
            xml = self._run_async(run())
            return BackendResult(ok=True, data={"source": xml, "length": len(xml), "udid": self._default_udid(udid)}, meta={"backend": self.name})
        except Exception as exc:
            if self._ensure_wda(udid):
                try:
                    xml = self._run_async(run())
                    return BackendResult(ok=True, data={"source": xml, "length": len(xml), "udid": self._default_udid(udid)}, meta={"backend": self.name, "self_healed_wda": True})
                except Exception as retry_exc:
                    return self._error("source", retry_exc)
            return self._error("source", exc)

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
            await client._request_json("POST", f"/session/{session_id}/wda/tap", {"x": x, "y": y})

        try:
            self._run_async(run())
            return BackendResult(ok=True, data={"x": x, "y": y, "udid": udid}, meta={"backend": self.name})
        except Exception as exc:
            if self._ensure_wda(udid):
                try:
                    self._run_async(run())
                    return BackendResult(ok=True, data={"x": x, "y": y, "udid": udid}, meta={"backend": self.name, "self_healed_wda": True})
                except Exception as retry_exc:
                    return self._error("tap", retry_exc)
            return self._error("tap", exc)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.2, udid: str | None = None) -> BackendResult:
        async def run() -> None:
            client, session_id = await self._wda_session(udid)
            await client.swipe(start_x, start_y, end_x, end_y, duration=duration, session_id=session_id)

        payload = {"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y, "duration": duration, "udid": self._default_udid(udid)}
        try:
            self._run_async(run())
            return BackendResult(ok=True, data=payload, meta={"backend": self.name})
        except Exception as exc:
            if self._ensure_wda(udid):
                try:
                    self._run_async(run())
                    return BackendResult(ok=True, data=payload, meta={"backend": self.name, "self_healed_wda": True})
                except Exception as retry_exc:
                    return self._error("swipe", retry_exc)
            return self._error("swipe", exc)

    def type_text(self, text: str, udid: str | None = None) -> BackendResult:
        async def run() -> None:
            client, session_id = await self._wda_session(udid)
            await client.send_keys(text, session_id=session_id)

        try:
            self._run_async(run())
            return BackendResult(ok=True, data={"text_length": len(text), "udid": udid}, meta={"backend": self.name})
        except Exception as exc:
            if self._ensure_wda(udid):
                try:
                    self._run_async(run())
                    return BackendResult(ok=True, data={"text_length": len(text), "udid": udid}, meta={"backend": self.name, "self_healed_wda": True})
                except Exception as retry_exc:
                    return self._error("type_text", retry_exc)
            return self._error("type_text", exc)

    def press_button(self, button: str, udid: str | None = None) -> BackendResult:
        async def run() -> None:
            client, session_id = await self._wda_session(udid)
            await client.press_button(button, session_id=session_id)

        try:
            self._run_async(run())
            return BackendResult(ok=True, data={"button": button, "udid": udid}, meta={"backend": self.name})
        except Exception as exc:
            if self._ensure_wda(udid):
                try:
                    self._run_async(run())
                    return BackendResult(ok=True, data={"button": button, "udid": udid}, meta={"backend": self.name, "self_healed_wda": True})
                except Exception as retry_exc:
                    return self._error("press_button", retry_exc)
            return self._error("press_button", exc)


def make_backend() -> IphoneBackend:
    if PyMobileDeviceBackend.available():
        return PyMobileDeviceBackend()
    return NullBackend("optional Python package pymobiledevice3 is not installed; install hermes-iphone-plugin[iphone] and ensure the iPhone is trusted/pairable")
