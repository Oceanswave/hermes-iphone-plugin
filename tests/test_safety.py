import json

from hermes_iphone.safety import SafetyPolicy, requires_confirmation
from hermes_iphone.state import PluginState


def test_potentially_external_actions_require_confirmation():
    assert requires_confirmation("send_text") is True
    assert requires_confirmation("place_call") is True
    assert requires_confirmation("tap") is False
    assert requires_confirmation("open_url") is False


def test_prepare_and_confirm_action_uses_one_time_tokens(tmp_path):
    state = PluginState(root=tmp_path)
    policy = SafetyPolicy(state=state)

    prepared = policy.prepare(action="send_text", payload={"to": "+15555550123", "body": "hello"})
    assert prepared["requires_confirmation"] is True
    assert prepared["token"]

    confirmed = policy.confirm(token=prepared["token"])
    assert confirmed["ok"] is True
    assert confirmed["action"] == "send_text"

    second = policy.confirm(token=prepared["token"])
    assert second["ok"] is False
    assert second["error"] == "unknown_or_expired_token"
