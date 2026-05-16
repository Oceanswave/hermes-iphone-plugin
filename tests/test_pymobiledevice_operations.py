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

    async def service_provider_async(self, udid=None):
        assert udid == "UDID123"
        return provider

    setattr(fake_lockdown, "create_using_usbmux", create_using_usbmux)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.lockdown", fake_lockdown)
    monkeypatch.setattr(PyMobileDeviceBackend, "_service_provider_async", service_provider_async)


def install_fake_wda_screenshot(monkeypatch, image=b"PNGDATA"):
    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            assert service_provider == "provider"

        async def start_session(self):
            return "SESSION1"

        async def get_screenshot(self, session_id=None):
            assert session_id == "SESSION1"
            return image

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)


def test_screenshot_writes_png_artifact_with_metadata(tmp_path, monkeypatch):
    install_lockdown(monkeypatch)
    install_fake_wda_screenshot(monkeypatch)

    result = PyMobileDeviceBackend(artifact_root=tmp_path).screenshot("UDID123")

    assert result.ok is True
    assert result.data["udid"] == "UDID123"
    assert result.data["size_bytes"] == 7
    assert result.data["transport"] == "wda"
    path = Path(result.data["path"])
    assert path.exists()
    assert path.read_bytes() == b"PNGDATA"
    assert path.suffix == ".png"


def test_screenshot_supports_async_lockdown_factory(tmp_path, monkeypatch):
    install_lockdown(monkeypatch, async_factory=True)
    install_fake_wda_screenshot(monkeypatch)

    result = PyMobileDeviceBackend(artifact_root=tmp_path).screenshot("UDID123")

    assert result.ok is True
    assert Path(result.data["path"]).read_bytes() == b"PNGDATA"


def test_launch_app_uses_wda_session_first(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            calls.append(("wda", service_provider, timeout))

        async def start_session(self, bundle_id=None):
            calls.append(("wda-launch", bundle_id))
            return "SESSION1"

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

    result = PyMobileDeviceBackend().launch_app("com.apple.MobileSMS", "UDID123")

    assert result.ok is True
    assert result.data == {"bundle_id": "com.apple.MobileSMS", "session_id": "SESSION1", "udid": "UDID123", "transport": "wda"}
    assert ("wda-launch", "com.apple.MobileSMS") in calls


def test_launch_app_reports_locked_device_without_slow_fallback(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            pass

        async def start_session(self, bundle_id=None):
            calls.append(("wda-launch", bundle_id))
            raise RuntimeError('Unable to launch com.apple.MobileSMS because the device was not, or could not be, unlocked.')

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

    result = PyMobileDeviceBackend().launch_app("com.apple.MobileSMS", "UDID123")

    assert result.ok is False
    assert result.error == "device_locked"
    assert "unlock" in result.message.lower()
    assert calls == [("wda-launch", "com.apple.MobileSMS")]


def test_launch_app_falls_back_to_dvt_for_non_locked_wda_failure(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            calls.append(("wda", service_provider, timeout))

        async def start_session(self, bundle_id=None):
            calls.append(("wda-launch", bundle_id))
            raise RuntimeError("wda temporary failure")

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

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
    assert result.data == {"bundle_id": "com.apple.mobilesafari", "pid": 4242, "udid": "UDID123", "transport": "dvt", "wda_error": "wda temporary failure"}
    assert ("launch", "com.apple.mobilesafari") in calls


def test_run_async_is_safe_inside_existing_event_loop():
    backend = PyMobileDeviceBackend()

    async def inner():
        async def work():
            return "ok"
        return backend._run_async(work())

    import asyncio
    assert asyncio.run(inner()) == "ok"


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
    assert ("POST", "/session/SESSION1/wda/tap", {"x": 12, "y": 34}) in calls


def test_tap_retries_after_wda_self_heal(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []
    attempts = {"count": 0}

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            pass

        async def start_session(self):
            return "SESSION1"

        async def _request_json(self, method, path, payload=None):
            attempts["count"] += 1
            calls.append((method, path, payload))
            if attempts["count"] == 1:
                raise RuntimeError("wda down")
            return {"status": 0}

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)
    monkeypatch.setattr(PyMobileDeviceBackend, "_ensure_wda", lambda self, udid=None: True)

    result = PyMobileDeviceBackend().tap(12, 34, "UDID123")

    assert result.ok is True
    assert result.meta["self_healed_wda"] is True
    assert attempts["count"] == 2
    assert calls == [
        ("POST", "/session/SESSION1/wda/tap", {"x": 12, "y": 34}),
        ("POST", "/session/SESSION1/wda/tap", {"x": 12, "y": 34}),
    ]


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


def test_screen_info_uses_wda_status_size_and_orientation(monkeypatch):
    install_lockdown(monkeypatch)

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            pass

        async def start_session(self):
            return "SESSION1"

        async def get_status(self):
            return {"value": {"ready": True}}

        async def get_window_size(self, session_id=None):
            assert session_id == "SESSION1"
            return {"width": 1284, "height": 2778}

        async def _request_json(self, method, path, payload=None):
            assert (method, path, payload) == ("GET", "/session/SESSION1/orientation", None)
            return {"value": "PORTRAIT"}

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

    result = PyMobileDeviceBackend().screen_info("UDID123")

    assert result.ok is True
    assert result.data["window_size"] == {"width": 1284, "height": 2778}
    assert result.data["orientation"] == "PORTRAIT"


def test_source_uses_wda_source(monkeypatch):
    install_lockdown(monkeypatch)

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            pass

        async def start_session(self):
            return "SESSION1"

        async def get_source(self, session_id=None):
            assert session_id == "SESSION1"
            return "<App><Button name='OK'/></App>"

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

    result = PyMobileDeviceBackend().source("UDID123")

    assert result.ok is True
    assert result.data["length"] == len("<App><Button name='OK'/></App>")
    assert "Button" in result.data["source"]


def test_swipe_uses_wda_swipe(monkeypatch):
    install_lockdown(monkeypatch)
    calls = []

    class FakeWdaClient:
        def __init__(self, service_provider, timeout=10.0):
            pass

        async def start_session(self):
            return "SESSION1"

        async def swipe(self, start_x, start_y, end_x, end_y, duration=0.2, session_id=None):
            calls.append((start_x, start_y, end_x, end_y, duration, session_id))

    fake_wda = types.ModuleType("pymobiledevice3.services.wda")
    setattr(fake_wda, "WdaServiceClient", FakeWdaClient)
    monkeypatch.setitem(sys.modules, "pymobiledevice3.services.wda", fake_wda)

    result = PyMobileDeviceBackend().swipe(1, 2, 3, 4, duration=0.7, udid="UDID123")

    assert result.ok is True
    assert calls == [(1, 2, 3, 4, 0.7, "SESSION1")]
