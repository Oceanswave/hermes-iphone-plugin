import json
from pathlib import Path

from pydantic import ValidationError

from hermes_iphone.dashboard import ensure_dashboard_installed
from hermes_iphone.dashboard import plugin_api
from hermes_iphone.dashboard.plugin_api import QuickActionBody, quick_action, tools


def test_dashboard_assets_install_to_hermes_plugin_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    result = ensure_dashboard_installed()

    dashboard_dir = Path(result["path"])
    assert dashboard_dir == tmp_path / "plugins" / "hermes-iphone-plugin" / "dashboard"
    assert (dashboard_dir / "manifest.json").exists()
    assert (dashboard_dir / "plugin_api.py").exists()
    assert (dashboard_dir / "assets" / "index.js").exists()
    assert (dashboard_dir / "assets" / "style.css").exists()
    manifest = json.loads((dashboard_dir / "manifest.json").read_text())
    assert manifest["label"] == "iPhone"
    assert manifest["tab"]["path"] == "/iphone"


def test_dashboard_catalog_excludes_sensitive_message_send_tools():
    catalog = tools()

    assert catalog["ok"] is True
    assert "status" in catalog["reads"]
    assert "ensure-wda" in catalog["quick_actions"]
    exposed_values = set(catalog["quick_actions"].values()) | set(
        catalog["reads"].values()
    )
    assert "send_text" not in exposed_values
    assert "prepare_text" not in exposed_values
    assert "confirm_prepared_action" not in exposed_values


def test_dashboard_quick_action_requires_confirm_before_service_call(monkeypatch):
    calls = []

    def fake_call(method_name, args=None):
        calls.append((method_name, args or {}))
        return {"ok": True}

    monkeypatch.setattr(plugin_api, "_call", fake_call)

    result = quick_action(QuickActionBody(action="home", confirm=False))

    assert result["ok"] is False
    assert result["error"] == "confirmation_required"
    assert calls == []


def test_dashboard_quick_action_maps_defaults_and_inputs(monkeypatch):
    calls = []

    def fake_call(method_name, args=None):
        calls.append((method_name, args or {}))
        return {"ok": True, "method": method_name, "args": args or {}}

    monkeypatch.setattr(plugin_api, "_call", fake_call)

    launch = quick_action(
        QuickActionBody(action="launch-messages", confirm=True, udid="dev1")
    )
    open_url = quick_action(
        QuickActionBody(action="open-url", confirm=True, url="https://example.com")
    )

    assert launch["method"] == "launch_app"
    assert launch["args"] == {"udid": "dev1", "bundle_id": "com.apple.MobileSMS"}
    assert open_url["method"] == "open_url"
    assert open_url["args"] == {"url": "https://example.com"}
    assert calls[0][0] == "launch_app"
    assert calls[1][0] == "open_url"


def test_dashboard_quick_action_rejects_unmodeled_fields():
    try:
        QuickActionBody.model_validate(
            {"action": "home", "confirm": True, "body": "do not allow message body"}
        )
    except ValidationError as exc:
        assert "Extra inputs are not permitted" in str(exc)
    else:
        raise AssertionError("extra dashboard quick-action fields should be forbidden")


def test_dashboard_overview_uses_read_only_snapshot_without_screenshot(monkeypatch):
    calls = []

    def fake_safe_call(method_name, args=None):
        calls.append((method_name, args or {}))
        return {"ok": True, "method": method_name, "data": {}}

    monkeypatch.setattr(plugin_api, "_safe_call", fake_safe_call)

    result = plugin_api.overview(udid="dev1")

    assert result["ok"] is True
    assert ("ensure_wda", {}) not in calls
    assert ("screenshot", {}) not in calls
    assert (
        "snapshot_state",
        {"udid": "dev1", "include_screenshot": False, "limit": 20},
    ) in calls


def test_dashboard_assets_use_guarded_actions_and_redacted_payload_panel():
    asset = Path("src/hermes_iphone/dashboard/assets/index.js").read_text()
    style = Path("src/hermes_iphone/dashboard/assets/style.css").read_text()

    assert "I confirm this iPhone quick action" in asset
    assert "Message-send prepare/confirm tools are intentionally not exposed" in asset
    assert "display_payload" in asset
    assert "iphone-overview-grid" in style
