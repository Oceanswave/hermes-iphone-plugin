import sys
import types

from hermes_iphone.backends import PyMobileDeviceBackend


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
