from hermes_iphone.backends import BackendResult
from hermes_iphone.service import IphoneService


SOURCE = """<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="390" height="844">
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="Compose" label="Compose" visible="true" enabled="true" x="340" y="20" width="40" height="40" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="To:" label="To:" value="" visible="true" enabled="true" x="55" y="90" width="300" height="35" />
  <XCUIElementTypeTextView type="XCUIElementTypeTextView" name="iMessage" label="iMessage" value="" visible="true" enabled="true" x="20" y="760" width="300" height="44" />
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="Send" label="Send" visible="true" enabled="true" x="330" y="760" width="44" height="44" />
</AppiumAUT>"""

MESSAGE_LABEL_SOURCE = """<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="926" height="428">
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="To:" label="To:" value="Sean" visible="true" enabled="true" x="397" y="24" width="457" height="44" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="messageBodyField" label="Message" value="" visible="true" enabled="true" x="446" y="207" width="373" height="41" />
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="sendButton" label="Send" visible="true" enabled="true" x="818" y="214" width="39" height="28" />
</AppiumAUT>"""

UNRESOLVED_RECIPIENT_SOURCE = """<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="926" height="428">
  <XCUIElementTypeCell type="XCUIElementTypeCell" name="sean, Hey, this is Rocky., 12:56 AM" label="sean, Hey, this is Rocky., 12:56 AM" visible="true" enabled="true" x="63" y="138" width="288" height="87" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="messageBodyField" label="Message" value="" visible="true" enabled="true" x="446" y="207" width="373" height="41" />
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="sendButton" label="Send" visible="true" enabled="true" x="818" y="214" width="39" height="28" />
</AppiumAUT>"""

SUGGESTION_SOURCE = """<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="926" height="428">
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="To:" label="To:" value="Sean" visible="true" enabled="true" x="397" y="24" width="457" height="44" />
  <XCUIElementTypeCell type="XCUIElementTypeCell" name="Maybe: Sean McLellan" label="Maybe: Sean McLellan" visible="true" enabled="true" x="397" y="72" width="457" height="54" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="messageBodyField" label="Message" value="" visible="true" enabled="true" x="446" y="207" width="373" height="41" />
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="sendButton" label="Send" visible="true" enabled="true" x="818" y="214" width="39" height="28" />
</AppiumAUT>"""

SELECTED_SUGGESTION_SOURCE = """<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="926" height="428">
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="To:" label="To:" value="Sean McLellan" visible="true" enabled="true" x="397" y="24" width="457" height="44" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="messageBodyField" label="Message" value="" visible="true" enabled="true" x="446" y="207" width="373" height="41" />
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="sendButton" label="Send" visible="true" enabled="true" x="818" y="214" width="39" height="28" />
</AppiumAUT>"""

THREAD_LIST_SOURCE = """<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="390" height="844">
  <XCUIElementTypeTextField type="XCUIElementTypeSearchField" name="Search" label="Search" value="" visible="true" enabled="true" x="16" y="80" width="358" height="36" />
  <XCUIElementTypeCell type="XCUIElementTypeCell" name="Sean McLellan, Hey, this is Rocky., 12:56 AM" label="Sean McLellan, Hey, this is Rocky., 12:56 AM" visible="true" enabled="true" x="16" y="138" width="358" height="87" />
</AppiumAUT>"""

OPEN_THREAD_SOURCE = """<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="390" height="844">
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="Messages" label="Messages" visible="true" enabled="true" x="8" y="20" width="90" height="44" />
  <XCUIElementTypeStaticText type="XCUIElementTypeStaticText" name="Sean McLellan" label="Sean McLellan" visible="true" enabled="true" x="120" y="42" width="150" height="24" />
  <XCUIElementTypeStaticText type="XCUIElementTypeStaticText" name="Incoming hello" label="Incoming hello" visible="true" enabled="true" x="28" y="590" width="160" height="44" />
  <XCUIElementTypeStaticText type="XCUIElementTypeStaticText" name="Outgoing yep" label="Outgoing yep" visible="true" enabled="true" x="210" y="650" width="150" height="44" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="messageBodyField" label="Message" value="" visible="true" enabled="true" x="20" y="760" width="300" height="44" />
  <XCUIElementTypeButton type="XCUIElementTypeButton" name="sendButton" label="Send" visible="true" enabled="true" x="330" y="760" width="44" height="44" />
</AppiumAUT>"""

SPLIT_THREAD_SOURCE = """<AppiumAUT type="XCUIElementTypeApplication" name="Messages" label="Messages" bundleId="com.apple.MobileSMS" visible="true" enabled="true" x="0" y="0" width="926" height="428">
  <XCUIElementTypeCell type="XCUIElementTypeCell" name="Sean McLellan, sidebar preview" label="Sean McLellan, sidebar preview" visible="true" enabled="true" x="63" y="138" width="288" height="87" />
  <XCUIElementTypeStaticText type="XCUIElementTypeStaticText" name="sidebar preview" label="sidebar preview" value="sidebar preview" visible="true" enabled="true" x="89" y="169" width="246" height="44" />
  <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="messageBodyField" label="Message" value="iMessage" visible="true" enabled="true" x="446" y="207" width="373" height="41" />
  <XCUIElementTypeTextView type="XCUIElementTypeTextView" name="CKBalloonTextView" label="CKBalloonTextView" value="Actual right-pane message" visible="true" enabled="true" x="498" y="130" width="356" height="60" />
  <XCUIElementTypeStaticText type="XCUIElementTypeStaticText" name="‎Read 1:36 PM" label="‎Read 1:36 PM" value="‎Read 1:36 PM" visible="true" enabled="true" x="769" y="177" width="74" height="14" />
</AppiumAUT>"""


class FakeBackend:
    name = "fake"

    def __init__(self):
        self.taps = []
        self.typed = []
        self.launched = []
        self.pressed = []
        self.screenshots = 0

    def source(self, udid=None):
        return BackendResult(ok=True, data={"source": SOURCE, "udid": udid})

    def screenshot(self, udid=None):
        self.screenshots += 1
        return BackendResult(
            ok=True,
            data={"path": f"/tmp/screenshot-{self.screenshots}.png", "udid": udid},
        )

    def tap(self, x, y, udid=None):
        self.taps.append((x, y))
        return BackendResult(ok=True, data={"x": x, "y": y, "udid": udid})

    def type_text(self, text, udid=None):
        self.typed.append(text)
        return BackendResult(ok=True, data={"text_length": len(text), "udid": udid})

    def launch_app(self, bundle_id, udid=None):
        self.launched.append(bundle_id)
        return BackendResult(ok=True, data={"bundle_id": bundle_id, "udid": udid})

    def press_button(self, button, udid=None):
        self.pressed.append(button)
        return BackendResult(ok=True, data={"button": button, "udid": udid})


class MessageLabelBackend(FakeBackend):
    def source(self, udid=None):
        return BackendResult(
            ok=True, data={"source": MESSAGE_LABEL_SOURCE, "udid": udid}
        )


class UnresolvedRecipientBackend(FakeBackend):
    def source(self, udid=None):
        if self.typed:
            return BackendResult(
                ok=True, data={"source": UNRESOLVED_RECIPIENT_SOURCE, "udid": udid}
            )
        return super().source(udid=udid)


class SuggestionBackend(FakeBackend):
    def source(self, udid=None):
        if (625, 99) in self.taps:
            return BackendResult(
                ok=True, data={"source": SELECTED_SUGGESTION_SOURCE, "udid": udid}
            )
        if self.typed:
            return BackendResult(
                ok=True, data={"source": SUGGESTION_SOURCE, "udid": udid}
            )
        return super().source(udid=udid)


class ThreadListBackend(FakeBackend):
    def source(self, udid=None):
        if self.taps:
            return BackendResult(
                ok=True, data={"source": OPEN_THREAD_SOURCE, "udid": udid}
            )
        return BackendResult(ok=True, data={"source": THREAD_LIST_SOURCE, "udid": udid})


class OpenThreadBackend(FakeBackend):
    def source(self, udid=None):
        return BackendResult(ok=True, data={"source": OPEN_THREAD_SOURCE, "udid": udid})


class SplitThreadBackend(FakeBackend):
    def source(self, udid=None):
        return BackendResult(
            ok=True, data={"source": SPLIT_THREAD_SOURCE, "udid": udid}
        )


def test_tap_element_by_id_uses_current_tree_and_logs_trace(tmp_path):
    backend = FakeBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.tap_element_id("e2", udid="UDID")

    assert result["ok"] is True
    assert backend.taps == [(205, 107)]
    assert result["data"]["element"]["id"] == "e2"
    assert result["meta"]["trace_dir"].startswith(str(tmp_path / "traces"))


def test_describe_screen_returns_compact_human_summary(tmp_path):
    service = IphoneService(
        backend=FakeBackend(),
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.describe_screen(udid="UDID")

    assert result["ok"] is True
    assert result["data"]["bundle_id"] == "com.apple.MobileSMS"
    assert "Compose" in result["data"]["summary"]
    assert "Send" in result["data"]["summary"]


def test_prepare_text_composes_message_but_does_not_tap_send_and_redacts_body(tmp_path):
    backend = FakeBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

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
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )
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
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.type_into_field("Message", "hello", udid="UDID")

    assert result["ok"] is True
    assert result["data"]["field"]["type"] == "textfield"
    assert result["data"]["field"]["label"] == "Message"
    assert backend.taps == [(632, 227)]


def test_prepare_text_accepts_message_body_field_label(tmp_path):
    backend = MessageLabelBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.prepare_text(to="Sean", body="hello", udid="UDID")

    assert result["ok"] is True
    assert result["requires_confirmation"] is True
    assert backend.typed[-1] == "hello"


def test_send_text_uses_hermes_approval_before_tapping_send(tmp_path):
    backend = FakeBackend()
    approvals = []
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    def approve(command, description, *, allow_permanent=True):
        approvals.append((command, description, allow_permanent))
        return "always"

    result = service.send_text(
        to="Sean", body="hello", udid="UDID", approval_fn=approve
    )

    assert result["ok"] is True
    assert result["data"]["sent"] is True
    assert result["approval"] == "always"
    assert approvals == [
        ("Send iMessage/SMS to Sean (5 characters)", "send_text", True)
    ]
    assert backend.taps[-1] == (352, 782)


def test_send_text_denied_by_hermes_approval_leaves_staged_draft(tmp_path):
    backend = FakeBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.send_text(
        to="Sean", body="hello", udid="UDID", approval_fn=lambda *a, **k: "deny"
    )

    assert result["ok"] is False
    assert result["error"] == "approval_denied"
    assert result["staged"] is True
    assert result["token"]
    assert backend.typed == ["Sean", "hello"]
    assert (352, 782) not in backend.taps


def test_send_text_cli_unavailable_approval_has_actionable_non_gateway_message(
    tmp_path,
):
    backend = FakeBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.send_text(
        to="Sean", body="hello", udid="UDID", approval_fn=lambda *a, **k: "unavailable"
    )

    assert result["ok"] is False
    assert result["error"] == "approval_required"
    assert result["approval"] == "unavailable"
    assert "fallback token" in result["message"]
    assert "/approve" not in result["message"]


def test_prepare_text_rejects_unresolved_literal_recipient_before_send(tmp_path):
    backend = UnresolvedRecipientBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.prepare_text(to="Sean", body="Hey, this is Rocky.", udid="UDID")

    assert result["ok"] is False
    assert result["error"] == "recipient_not_verified"
    assert "Sean" in result["message"]
    assert not result.get("token")
    assert (837, 228) not in backend.taps


def test_prepare_text_selects_matching_messages_contact_suggestion_before_send(
    tmp_path,
):
    backend = SuggestionBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.prepare_text(to="Sean", body="Hey, this is Rocky.", udid="UDID")

    assert result["ok"] is True
    assert result["requires_confirmation"] is True
    assert (625, 99) in backend.taps
    assert result["data"]["recipient"]["verified_by"] == "contact_suggestion"
    assert result["data"]["recipient"]["display"] == "Sean McLellan"
    assert (837, 228) not in backend.taps


def test_snapshot_state_can_include_screenshot_without_body_leaks(tmp_path):
    backend = FakeBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.snapshot_state(include_screenshot=True, limit=2, udid="UDID")

    assert result["ok"] is True
    assert result["data"]["bundle_id"] == "com.apple.MobileSMS"
    assert result["data"]["screenshot"] == "/tmp/screenshot-1.png"
    assert len(result["data"]["elements"]) == 2


def test_select_suggestion_taps_best_visible_cell(tmp_path):
    backend = SuggestionBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )
    backend.typed.append("Sean")

    result = service.select_suggestion("Sean", udid="UDID")

    assert result["ok"] is True
    assert backend.taps == [(625, 99)]
    assert result["data"]["suggestion"]["label"] == "Maybe: Sean McLellan"


def test_recover_to_home_or_app_presses_home_then_launches_target(tmp_path):
    backend = FakeBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.recover_to_home_or_app(
        bundle_id="com.apple.MobileSMS", udid="UDID"
    )

    assert result["ok"] is True
    assert backend.pressed == ["home"]
    assert backend.launched == ["com.apple.MobileSMS"]
    assert result["data"]["recovered_from_home"] is True


def test_open_messages_thread_taps_visible_thread_cell(tmp_path):
    backend = ThreadListBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.open_messages_thread("Sean", udid="UDID")

    assert result["ok"] is True
    assert result["data"]["opened_thread"] == "Sean"
    assert result["data"]["method"] == "visible_thread_cell"
    assert backend.taps == [(195, 181)]


def test_read_recent_messages_filters_controls_and_keeps_visible_bubbles(tmp_path):
    service = IphoneService(
        backend=OpenThreadBackend(),
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.read_recent_messages(limit=2, udid="UDID")

    assert result["ok"] is True
    assert [m["text"] for m in result["data"]["messages"]] == [
        "Incoming hello",
        "Outgoing yep",
    ]
    assert result["data"]["messages"][0]["direction"] == "inbound"
    assert result["data"]["messages"][1]["direction"] == "outbound"


def test_prepare_current_message_reply_stages_without_tapping_send(tmp_path):
    backend = OpenThreadBackend()
    service = IphoneService(
        backend=backend,
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.prepare_current_message_reply("reply body", udid="UDID")

    assert result["ok"] is True
    assert result["requires_confirmation"] is True
    assert result["data"]["to"] == "current Messages thread"
    assert result["data"]["body_length"] == 10
    assert backend.typed == ["reply body"]
    assert (352, 782) not in backend.taps
    assert result["data"]["thread_context"]["count"] == 2


def test_read_recent_messages_scopes_to_detail_pane_in_split_view(tmp_path):
    service = IphoneService(
        backend=SplitThreadBackend(),
        action_log_root=tmp_path / "logs",
        trace_root=tmp_path / "traces",
    )

    result = service.read_recent_messages(limit=5, udid="UDID")

    assert result["ok"] is True
    texts = [m["text"] for m in result["data"]["messages"]]
    assert texts == ["Actual right-pane message"]
    assert "sidebar preview" not in texts
    assert result["data"]["messages"][0]["direction"] == "outbound"
