from hermes_iphone.backends import BackendResult, NullBackend
from hermes_iphone.service import IphoneService


def test_null_backend_reports_missing_runtime_without_crashing():
    backend = NullBackend(reason="pymobiledevice3 not installed")
    result = backend.list_devices()
    assert result.ok is False
    assert result.error == "backend_unavailable"
    assert "pymobiledevice3" in result.message


def test_service_delegates_ui_actions_to_backend():
    calls = []

    class FakeBackend:
        name = "fake"
        def list_devices(self):
            return BackendResult(ok=True, data=[{"udid": "abc"}])
        def screenshot(self, udid=None):
            calls.append(("screenshot", udid))
            return BackendResult(ok=True, data={"path": "/tmp/shot.png"})
        def open_url(self, url, udid=None):
            calls.append(("open_url", url, udid))
            return BackendResult(ok=True, data={"url": url})
        def launch_app(self, bundle_id, udid=None):
            calls.append(("launch_app", bundle_id, udid))
            return BackendResult(ok=True, data={"bundle_id": bundle_id})
        def tap(self, x, y, udid=None):
            calls.append(("tap", x, y, udid))
            return BackendResult(ok=True, data={"x": x, "y": y})
        def type_text(self, text, udid=None):
            calls.append(("type_text", text, udid))
            return BackendResult(ok=True, data={"length": len(text)})
        def press_button(self, button, udid=None):
            calls.append(("press_button", button, udid))
            return BackendResult(ok=True, data={"button": button})

    service = IphoneService(backend=FakeBackend())
    assert service.open_url("https://example.com")["ok"] is True
    assert service.tap(10, 20, udid="abc")["ok"] is True
    assert calls == [("open_url", "https://example.com", None), ("tap", 10, 20, "abc")]
