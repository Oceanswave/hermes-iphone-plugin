import sys
import types
from pathlib import Path

from hermes_iphone.backends import PyMobileDeviceBackend


def install_lockdown(monkeypatch, provider="provider", async_factory=False):
    fake_lockdown = types.ModuleType("pymobiledevice3.lockdown")

    if async_factory:
        async def create_using_usbmux(serial=None, autopair=True):
            assert serial == "UDID123"
            assert autopair is True
            return provider
    else:
        def create_using_usbmux(serial=None, autopair=True):
            assert serial == "UDID123"
            assert autopair is True
            return provider

    setattr(fake_lockdown, "create_using_usbmux", create_using_usbmux)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.lockdown", fake_lockdown)


def test_screenshot_writes_png_artifact_with_metadata(tmp_path, monkeypatch):
    install_lockdown(monkeypatch)

    class FakeScreenshotService:
        def __init__(self, service_provider):
            assert service_provider == "provider"

        async def take_screenshot(self):
            return b"PNGDATA"

    fake_screenshot = types.ModuleType("pymobiledevice3.services.screenshot")
    setattr(fake_screenshot, "ScreenshotService", FakeScreenshotService)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.screenshot", fake_screenshot)

    result = PyMobileDeviceBackend(artifact_root=tmp_path).screenshot("UDID123")

    assert result.ok is True
    assert result.data["udid"] == "UDID123"
    assert result.data["size_bytes"] == 7
    path = Path(result.data["path"])
    assert path.exists()
    assert path.read_bytes() == b"PNGDATA"
    assert path.suffix == ".png"


def test_screenshot_supports_async_lockdown_factory(tmp_path, monkeypatch):
    install_lockdown(monkeypatch, async_factory=True)

    class FakeScreenshotService:
        def __init__(self, service_provider):
            assert service_provider == "provider"

        async def take_screenshot(self):
            return b"PNGDATA"

    fake_screenshot = types.ModuleType("pymobiledevice3.services.screenshot")
    setattr(fake_screenshot, "ScreenshotService", FakeScreenshotService)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.screenshot", fake_screenshot)

    result = PyMobileDeviceBackend(artifact_root=tmp_path).screenshot("UDID123")

    assert result.ok is True
    assert Path(result.data["path"]).read_bytes() == b"PNGDATA"


def test_launch_app_uses_dvt_process_control(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    class FakeDvtProvider:
        def __init__(self, service_provider):
            calls.append(("dvt", service_provider))

        async def __aenter__(self):
            return "dvt-provider"

        async def __aexit__(self, *exc):
            calls.append(("dvt-close",))

    class FakeProcessControl:
        def __init__(self, dvt):
            calls.append(("pc", dvt))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            calls.append(("pc-close",))

        async def launch(self, bundle_id):
            calls.append(("launch", bundle_id))
            return 4242

    fake_provider = types.ModuleType("pymobiledevice3.services.dvt.instruments.dvt_provider")
    setattr(fake_provider, "DvtProvider", FakeDvtProvider)
    fake_pc = types.ModuleType("pymobiledevice3.services.dvt.instruments.process_control")
    setattr(fake_pc, "ProcessControl", FakeProcessControl)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.dvt.instruments.dvt_provider", fake_provider)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.dvt.instruments.process_control", fake_pc)

    result = PyMobileDeviceBackend().launch_app("com.apple.mobilesafari", "UDID123")

    assert result.ok is True
    assert result.data == {"bundle_id": "com.apple.mobilesafari", "pid": 4242, "udid": "UDID123"}
    assert ("launch", "com.apple.mobilesafari") in calls


def test_open_url_uses_webinspector_launch_task(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    async def launch_task(service_provider, url, timeout):
        calls.append((service_provider, url, timeout))

    fake_webinspector = types.ModuleType("pymobiledevice3.cli.webinspector")
    setattr(fake_webinspector, "launch_task", launch_task)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.cli.webinspector", fake_webinspector)

    result = PyMobileDeviceBackend().open_url("https://example.com", "UDID123")

    assert result.ok is True
    assert result.data == {"url": "https://example.com", "udid": "UDID123"}
    assert calls == [("provider", "https://example.com", 5.0)]


def test_tap_uses_wda_coordinate_endpoint(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            calls.append(("init", service_provider, timeout))

        async def start_session(self):
            calls.append(("session",))
            return "SESSION1"

        async def _request_json(self, method, path, payload=None):
            calls.append((method, path, payload))
            return {"status": 0}

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

    result = PyMobileDeviceBackend().tap(12, 34, "UDID123")

    assert result.ok is True
    assert result.data == {"x": 12, "y": 34, "udid": "UDID123"}
    assert ("POST", "/session/SESSION1/wda/tap/0", {"x": 12, "y": 34}) in calls


def test_type_text_uses_wda_send_keys(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            pass

        async def start_session(self):
            return "SESSION1"

        async def send_keys(self, text, session_id=None):
            calls.append((text, session_id))

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

    result = PyMobileDeviceBackend().type_text("hello", "UDID123")

    assert result.ok is True
    assert result.data == {"text_length": 5, "udid": "UDID123"}
    assert calls == [("hello", "SESSION1")]


def test_press_button_uses_wda_press_button(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            pass

        async def start_session(self):
            return "SESSION1"

        async def press_button(self, name, session_id=None):
            calls.append((name, session_id))

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

    result = PyMobileDeviceBackend().press_button("home", "UDID123")

    assert result.ok is True
    assert result.data == {"button": "home", "udid": "UDID123"}
    assert calls == [("home", "SESSION1")]
