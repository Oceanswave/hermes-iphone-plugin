import sys
import types

from hermes_iphone.backends import BackendResult, PyMobileDeviceBackend


def test_pymobiledevice_backend_awaits_async_list_devices(monkeypatch):
    class FakeDevice:
        serial = "UDID123"
        connection_type = "USB"

    async def list_devices():
        return [FakeDevice()]

    fake_pkg = types.ModuleType("pymobiledevice3")
    fake_usbmux = types.ModuleType("pymobiledevice3.usbmux")
    fake_usbmux.list_devices = list_devices
    monkeypatch.setitem(sys.modules, "pymobiledevice3", fake_pkg)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.usbmux", fake_usbmux)

    result = PyMobileDeviceBackend().list_devices()

    assert result.ok is True
    assert result.data[0]["udid"] == "UDID123"
    assert result.data[0]["connection_type"] == "USB"
    assert "FakeDevice" in result.data[0]["raw"]


def test_pymobiledevice_backend_explains_usbmuxd_permission_denied(monkeypatch):
    def list_devices():
        raise PermissionError(13, "Permission denied")

    fake_pkg = types.ModuleType("pymobiledevice3")
    fake_usbmux = types.ModuleType("pymobiledevice3.usbmux")
    fake_usbmux.list_devices = list_devices
    monkeypatch.setitem(sys.modules, "pymobiledevice3", fake_pkg)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.usbmux", fake_usbmux)

    result = PyMobileDeviceBackend().list_devices()

    assert result.ok is False
    assert result.error == "list_devices_failed"
    assert "permission" in result.message.lower()
    assert "usbmuxd" in result.message.lower()
    assert result.meta["exception"] == "PermissionError"


def test_diagnostics_reports_wda_helper_and_readiness(monkeypatch, tmp_path):
    helper = tmp_path / "ensure-iphone-wda.sh"
    helper.write_text("#!/bin/sh\nexit 0\n")
    helper.chmod(0o755)
    monkeypatch.setenv("HERMES_IPHONE_WDA_HELPER", str(helper))
    monkeypatch.setenv("HERMES_IPHONE_UDID", "UDID123")
    monkeypatch.setattr(
        PyMobileDeviceBackend,
        "_tunneld_ready",
        lambda self, udid=None: (True, ["UDID123"], None),
    )
    monkeypatch.setattr(
        PyMobileDeviceBackend,
        "_wda_ready",
        lambda self, udid=None: (True, {"ready": True}, None),
    )

    result = PyMobileDeviceBackend().diagnostics()

    assert result.ok is True
    assert result.data["udid"] == "UDID123"
    assert result.data["wda_helper"]["exists"] is True
    assert result.data["tunneld"]["ready"] is True
    assert result.data["wda"]["ready"] is True


def test_ensure_wda_uses_native_lifecycle_when_wda_is_down(monkeypatch, tmp_path):
    calls = {"count": 0, "native": 0}

    def fake_ready(self, udid=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return False, None, "down"
        return True, {"ready": True}, None

    def fake_native(self, udid=None):
        calls["native"] += 1
        return BackendResult(ok=True, data={"started_wda": True})

    monkeypatch.setattr(PyMobileDeviceBackend, "_wda_ready", fake_ready)
    monkeypatch.setattr(PyMobileDeviceBackend, "_ensure_wda_native", fake_native)

    result = PyMobileDeviceBackend().ensure_wda("UDID123")

    assert result.ok is True
    assert result.data["already_ready"] is False
    assert result.data["method"] == "native"
    assert calls["native"] == 1
