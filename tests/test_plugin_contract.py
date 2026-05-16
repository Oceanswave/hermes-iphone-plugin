import json
from pathlib import Path


class FakeContext:
    def __init__(self):
        self.tools = {}
        self.skills = {}

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs

    def register_skill(self, name, path, description=""):
        self.skills[name] = {"path": Path(path), "description": description}


def test_register_exposes_native_iphone_tools_and_operator_skill():
    import hermes_iphone

    ctx = FakeContext()
    hermes_iphone.register(ctx)

    assert {
        "iphone_status",
        "iphone_list_devices",
        "iphone_ensure_wda",
        "iphone_screenshot",
        "iphone_screen_info",
        "iphone_source",
        "iphone_tree",
        "iphone_find_element",
        "iphone_tap_text",
        "iphone_tap_element",
        "iphone_describe_screen",
        "iphone_wait_for_text",
        "iphone_type_into_field",
        "iphone_current_app",
        "iphone_launch_or_focus",
        "iphone_open_url",
        "iphone_launch_app",
        "iphone_tap",
        "iphone_swipe",
        "iphone_type_text",
        "iphone_press_button",
        "iphone_prepare_text",
        "iphone_send_text",
        "iphone_confirm_prepared_action",
    }.issubset(ctx.tools)
    assert all(tool["toolset"] == "iphone" for tool in ctx.tools.values())
    assert "operator" in ctx.skills
    assert ctx.skills["operator"]["path"].exists()


def test_handlers_return_json_strings():
    import hermes_iphone

    ctx = FakeContext()
    hermes_iphone.register(ctx)
    payload = ctx.tools["iphone_status"]["handler"]({})

    parsed = json.loads(payload)
    assert parsed["ok"] is True
    assert parsed["plugin"] == "hermes-iphone-plugin"
    assert "backends" in parsed
