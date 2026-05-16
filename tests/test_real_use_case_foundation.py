from hermes_iphone.backends import BackendResult
from hermes_iphone.service import IphoneService


SOURCE = '''<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="390" height="844">
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="Compose" label="Compose" visible="true" enabled="true" x="340" y="20" width="40" height="40" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="To:" label="To:" value="" visible="true" enabled="true" x="55" y="90" width="300" height="35" />
  <XCUIElementTypeTextView type="XCUIElementTypeTextView" name="iMessage" label="iMessage" value="" visible="true" enabled="true" x="20" y="760" width="300" height="44" />
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="Send" label="Send" visible="true" enabled="true" x="330" y="760" width="44" height="44" />
</AppiumAUT>'''

MESSAGE_LABEL_SOURCE = '''<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="926" height="428">
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="To:" label="To:" value="Sean" visible="true" enabled="true" x="397" y="24" width="457" height="44" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="messageBodyField" label="Message" value="" visible="true" enabled="true" x="446" y="207" width="373" height="41" />
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="sendButton" label="Send" visible="true" enabled="true" x="818" y="214" width="39" height="28" />
</AppiumAUT>'''


class FakeBackend:
    name = "fake"

    def __init__(self):
        self.taps = []
        self.typed = []
        self.launched = []
        self.screenshots = 0

    def source(self, udid=None):
        return BackendResult(ok=True, data={"source": SOURCE, "udid": udid})

    def screenshot(self, udid=None):
        self.screenshots += 1
        return BackendResult(ok=True, data={"path": f"/tmp/screenshot-{self.screenshots}.png", "udid": udid})

    def tap(self, x, y, udid=None):
        self.taps.append((x, y))
        return BackendResult(ok=True, data={"x": x, "y": y, "udid": udid})

    def type_text(self, text, udid=None):
        self.typed.append(text)
        return BackendResult(ok=True, data={"text_length": len(text), "udid": udid})

    def launch_app(self, bundle_id, udid=None):
        self.launched.append(bundle_id)
        return BackendResult(ok=True, data={"bundle_id": bundle_id, "udid": udid})


class MessageLabelBackend(FakeBackend):
    def source(self, udid=None):
        return BackendResult(ok=True, data={"source": MESSAGE_LABEL_SOURCE, "udid": udid})


def test_tap_element_by_id_uses_current_tree_and_logs_trace(tmp_path):
    backend = FakeBackend()
    service = IphoneService(backend=backend, action_log_root=tmp_path / "logs", trace_root=tmp_path / "traces")

    result = service.tap_element_id("e2", udid="UDID")

    assert result["ok"] is True
    assert backend.taps == [(205, 107)]
    assert result["data"]["element"]["id"] == "e2"
    assert result["meta"]["trace_dir"].startswith(str(tmp_path / "traces"))


def test_describe_screen_returns_compact_human_summary(tmp_path):
    service = IphoneService(backend=FakeBackend(), action_log_root=tmp_path / "logs", trace_root=tmp_path / "traces")

    result = service.describe_screen(udid="UDID")

    assert result["ok"] is True
    assert result["data"]["bundle_id"] == "com.apple.MobileSMS"
    assert "Compose" in result["data"]["summary"]
    assert "Send" in result["data"]["summary"]


def test_prepare_text_composes_message_but_does_not_tap_send_and_redacts_body(tmp_path):
    backend = FakeBackend()
    service = IphoneService(backend=backend, action_log_root=tmp_path / "logs", trace_root=tmp_path / "traces")

    result = service.prepare_text(to="+155****4567", body="super secret", udid="UDID")

    assert result["ok"] is True
    assert result["requires_confirmation"] is True
    assert result["token"]
    assert result["data"]["body_length"] == 12
    assert result["data"]["screenshot_before_send"] == "/tmp/screenshot-4.png"
    assert "super secret" not in str(result)
    send_center = (352, 782)
    assert send_center not in backend.taps
    assert backend.typed == ["+155****4567", "super secret"]

    for path in (tmp_path / "logs").glob("*.json"):
        assert "super secret" not in path.read_text()


def test_confirm_prepared_text_taps_send_once_and_consumes_token(tmp_path):
    backend = FakeBackend()
    service = IphoneService(backend=backend, action_log_root=tmp_path / "logs", trace_root=tmp_path / "traces")
    prepared = service.prepare_text(to="Sean", body="hello", udid="UDID")

    confirmed = service.confirm_prepared_action(prepared["token"], udid="UDID")

    assert confirmed["ok"] is True
    assert confirmed["action"] == "send_text"
    assert backend.taps[-1] == (352, 782)
    assert confirmed["data"]["sent"] is True
    again = service.confirm_prepared_action(prepared["token"], udid="UDID")
    assert again["ok"] is False
    assert again["error"] == "unknown_or_expired_token"


def test_type_into_field_prefers_exact_input_over_root_app_match(tmp_path):
    backend = MessageLabelBackend()
    service = IphoneService(backend=backend, action_log_root=tmp_path / "logs", trace_root=tmp_path / "traces")

    result = service.type_into_field("Message", "hello", udid="UDID")

    assert result["ok"] is True
    assert result["data"]["field"]["type"] == "textfield"
    assert result["data"]["field"]["label"] == "Message"
    assert backend.taps == [(632, 227)]


def test_prepare_text_accepts_message_body_field_label(tmp_path):
    backend = MessageLabelBackend()
    service = IphoneService(backend=backend, action_log_root=tmp_path / "logs", trace_root=tmp_path / "traces")

    result = service.prepare_text(to="Sean", body="hello", udid="UDID")

    assert result["ok"] is True
    assert result["requires_confirmation"] is True
    assert backend.typed[-1] == "hello"


def test_send_text_uses_hermes_approval_before_tapping_send(tmp_path):
    backend = FakeBackend()
    approvals = []
    service = IphoneService(backend=backend, action_log_root=tmp_path / "logs", trace_root=tmp_path / "traces")

    def approve(command, description, *, allow_permanent=True):
        approvals.append((command, description, allow_permanent))
        return "always"

    result = service.send_text(to="Sean", body="hello", udid="UDID", approval_fn=approve)

    assert result["ok"] is True
    assert result["data"]["sent"] is True
    assert result["approval"] == "always"
    assert approvals == [("Send iMessage/SMS to Sean (5 characters)", "send_text", True)]
    assert backend.taps[-1] == (352, 782)


def test_send_text_denied_by_hermes_approval_leaves_staged_draft(tmp_path):
    backend = FakeBackend()
    service = IphoneService(backend=backend, action_log_root=tmp_path / "logs", trace_root=tmp_path / "traces")

    result = service.send_text(to="Sean", body="hello", udid="UDID", approval_fn=lambda *a, **k: "deny")

    assert result["ok"] is False
    assert result["error"] == "approval_denied"
    assert result["staged"] is True
    assert result["token"]
    assert backend.typed == ["Sean", "hello"]
    assert (352, 782) not in backend.taps
