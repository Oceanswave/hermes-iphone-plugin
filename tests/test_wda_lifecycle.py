from hermes_iphone.backends import BackendResult, PyMobileDeviceBackend


def test_ensure_wda_prefers_native_lifecycle_before_shell_helper(monkeypatch, tmp_path):
    calls = []
    backend = PyMobileDeviceBackend()
    monkeypatch.setattr(backend, "_wda_ready", lambda udid=None: (False, None, "down") if len(calls) == 0 else (True, {"value": {"ready": True}}, None))
    monkeypatch.setattr(backend, "_ensure_wda_native", lambda udid=None: calls.append(("native", udid)) or BackendResult(ok=True, data={"started_wda": True, "method": "native"}))
    monkeypatch.setattr(backend, "_ensure_wda_helper", lambda udid=None: calls.append(("helper", udid)) or BackendResult(ok=True))

    result = backend.ensure_wda("UDID123")

    assert result.ok is True
    assert result.data["method"] == "native"
    assert calls == [("native", "UDID123")]


def test_ensure_wda_falls_back_to_helper_when_native_lifecycle_fails(monkeypatch):
    calls = []
    backend = PyMobileDeviceBackend()
    readiness = {"ready": False}
    monkeypatch.setattr(backend, "_wda_ready", lambda udid=None: (readiness["ready"], {"value": {"ready": True}} if readiness["ready"] else None, None if readiness["ready"] else "down"))
    monkeypatch.setattr(backend, "_ensure_wda_native", lambda udid=None: calls.append(("native", udid)) or BackendResult(ok=False, error="native_failed"))
    def helper(udid=None):
        calls.append(("helper", udid))
        readiness["ready"] = True
        return BackendResult(ok=True, data={"method": "helper"})
    monkeypatch.setattr(backend, "_ensure_wda_helper", helper)

    result = backend.ensure_wda("UDID123")

    assert result.ok is True
    assert result.data["method"] == "helper"
    assert calls == [("native", "UDID123"), ("helper", "UDID123")]
