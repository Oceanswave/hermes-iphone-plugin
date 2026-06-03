def test_register_registers_tools_and_skill():
    import hermes_iphone

    calls = {"tools": [], "skills": []}

    class Ctx:
        def register_tool(self, **kw):
            calls["tools"].append(kw)

        def register_skill(self, name, path, **kw):
            calls["skills"].append((name, path))

    hermes_iphone.register(Ctx())
    names = [t["name"] for t in calls["tools"]]
    assert "iphone_status" in names
    assert "iphone_ensure_wda" in names
    assert "iphone_screen_info" in names
    assert "iphone_source" in names
    assert "iphone_tree" in names
    assert "iphone_find_element" in names
    assert "iphone_tap_text" in names
    assert "iphone_tap_element" in names
    assert "iphone_describe_screen" in names
    assert "iphone_type_into_field" in names
    assert "iphone_current_app" in names
    assert "iphone_swipe" in names
    assert "iphone_screenshot" in names
    assert "iphone_send_text" in names
    assert "iphone_confirm_prepared_action" in names
    assert "iphone_snapshot_state" in names
    assert "iphone_select_suggestion" in names
    assert "iphone_dismiss_keyboard" in names
    assert "iphone_go_back" in names
    assert "iphone_recover_to_home_or_app" in names
    assert "iphone_open_messages_thread" in names
    assert "iphone_read_recent_messages" in names
    assert "iphone_prepare_current_message_reply" in names
    assert "iphone_reply_current_message_thread" in names
    assert len(names) == 35
    assert calls["skills"]


def test_prepare_confirm_token_is_one_time(tmp_path, monkeypatch):
    from hermes_iphone.safety import SafetyPolicy
    from hermes_iphone.state import PluginState

    policy = SafetyPolicy(state=PluginState(root=tmp_path))
    prepared = policy.prepare("send_text", {"to": "+15551234567", "body": "hello"})
    assert prepared["ok"] is True
    token = prepared["token"]
    first = policy.confirm(token=token)
    assert first["ok"] is True
    assert first["action"] == "send_text"
    second = policy.confirm(token=token)
    assert second["error"] == "unknown_or_expired_token"


def test_list_devices_missing_dependency_monkeypatch(monkeypatch):
    from hermes_iphone.backends import NullBackend

    result = NullBackend("missing").list_devices().to_dict()
    assert result["ok"] is False
    assert result["error"] == "backend_unavailable"
