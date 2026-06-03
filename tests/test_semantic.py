from hermes_iphone.backends import BackendResult
from hermes_iphone.service import IphoneService
from hermes_iphone.semantic import compact_tree_from_xml, find_elements


SOURCE = """<?xml version="1.0" encoding="UTF-8"?>
<XCUIElementTypeApplication type="XCUIElementTypeApplication" name="Messages" label="Messages" visible="true" x="0" y="0" width="390" height="844" bundleId="com.apple.MobileSMS">
  <XCUIElementTypeWindow type="XCUIElementTypeWindow" visible="true" x="0" y="0" width="390" height="844">
    <XCUIElementTypeButton type="XCUIElementTypeButton" name="Compose" label="Compose" enabled="true" visible="true" x="340" y="40" width="44" height="44"/>
    <XCUIElementTypeTextField type="XCUIElementTypeTextField" name="To:" label="To:" value="" enabled="true" visible="true" x="20" y="100" width="350" height="44"/>
    <XCUIElementTypeButton type="XCUIElementTypeButton" name="Send" label="Send" enabled="false" visible="true" x="320" y="760" width="50" height="40"/>
    <XCUIElementTypeStaticText type="XCUIElementTypeStaticText" name="Hidden" label="Hidden" visible="false" x="0" y="0" width="1" height="1"/>
  </XCUIElementTypeWindow>
</XCUIElementTypeApplication>
"""


class FakeBackend:
    name = "fake"

    def __init__(self):
        self.calls = []
        self.sources = [SOURCE]

    def source(self, udid=None):
        return BackendResult(
            ok=True,
            data={
                "source": self.sources[-1],
                "udid": udid,
                "length": len(self.sources[-1]),
            },
        )

    def tap(self, x, y, udid=None):
        self.calls.append(("tap", x, y, udid))
        return BackendResult(ok=True, data={"x": x, "y": y, "udid": udid})

    def type_text(self, text, udid=None):
        self.calls.append(("type_text", text, udid))
        return BackendResult(ok=True, data={"text_length": len(text), "udid": udid})

    def launch_app(self, bundle_id, udid=None):
        self.calls.append(("launch_app", bundle_id, udid))
        return BackendResult(
            ok=True, data={"bundle_id": bundle_id, "pid": 123, "udid": udid}
        )


def test_compact_tree_filters_visible_accessible_nodes_and_bounds():
    tree = compact_tree_from_xml(SOURCE)
    assert tree["bundle_id"] == "com.apple.MobileSMS"
    assert [n["label"] for n in tree["elements"]] == [
        "Messages",
        "Compose",
        "To:",
        "Send",
    ]
    compose = tree["elements"][1]
    assert compose["center"] == {"x": 362, "y": 62}
    assert compose["enabled"] is True


def test_find_elements_matches_label_type_and_enabled_state():
    tree = compact_tree_from_xml(SOURCE)
    matches = find_elements(tree, text="send", element_type="button", enabled=False)
    assert len(matches) == 1
    assert matches[0]["label"] == "Send"


def test_service_find_element_and_tap_text_use_semantic_center():
    backend = FakeBackend()
    svc = IphoneService(backend=backend)
    found = svc.find_element(text="Compose", element_type="button", udid="UDID123")
    assert found["ok"] is True
    assert found["data"]["element"]["center"] == {"x": 362, "y": 62}

    tapped = svc.tap_text("Compose", element_type="button", udid="UDID123")
    assert tapped["ok"] is True
    assert backend.calls[-1] == ("tap", 362, 62, "UDID123")
    assert tapped["data"]["element"]["label"] == "Compose"


def test_service_type_into_field_taps_field_then_types():
    backend = FakeBackend()
    svc = IphoneService(backend=backend)
    result = svc.type_into_field("To:", "Sean", udid="UDID123")
    assert result["ok"] is True
    assert backend.calls == [
        ("tap", 195, 122, "UDID123"),
        ("type_text", "Sean", "UDID123"),
    ]


def test_current_app_and_launch_or_focus():
    backend = FakeBackend()
    svc = IphoneService(backend=backend)
    current = svc.current_app(udid="UDID123")
    assert current["data"] == {
        "bundle_id": "com.apple.MobileSMS",
        "name": "Messages",
        "udid": "UDID123",
    }

    already = svc.launch_or_focus("com.apple.MobileSMS", udid="UDID123")
    assert already["data"]["already_foreground"] is True

    launched = svc.launch_or_focus("com.apple.Preferences", udid="UDID123")
    assert launched["ok"] is True
    assert backend.calls[-1] == ("launch_app", "com.apple.Preferences", "UDID123")


def test_action_log_redacts_text_and_records_artifacts(tmp_path):
    backend = FakeBackend()
    svc = IphoneService(backend=backend, action_log_root=tmp_path)
    result = svc.type_into_field("To:", "secret body", udid="UDID123")
    assert result["ok"] is True
    log_path = result["meta"]["action_log"]
    content = tmp_path.joinpath(log_path.split("/")[-1]).read_text()
    assert "secret body" not in content
    assert "text_length" in content
