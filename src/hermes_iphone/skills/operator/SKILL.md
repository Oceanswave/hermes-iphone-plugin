---
name: operator
description: Operate attached iPhones safely through hermes-iphone-plugin tools.
---

# iPhone Operator

Use this skill when controlling an attached iPhone through the native Hermes iPhone plugin.

Rules:
- Start with `iphone_status` and `iphone_list_devices`.
- Prefer deterministic tools over vision-only automation.
- Never send texts, place calls, delete data, buy anything, or change account/security settings without explicit user approval.
- For SMS/iMessage, use `iphone_prepare_text` first. Only call `iphone_confirm_prepared_action` after the user approves the exact recipient/body.
- Report which backend is active and whether any capability is not yet implemented on this host.

Current MVP tools:
- `iphone_status`
- `iphone_list_devices`
- `iphone_screenshot`
- `iphone_open_url`
- `iphone_launch_app`
- `iphone_tap`
- `iphone_type_text`
- `iphone_press_button`
- `iphone_prepare_text`
- `iphone_confirm_prepared_action`
