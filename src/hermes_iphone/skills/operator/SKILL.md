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

Linux usbmuxd troubleshooting:
- If `iphone_list_devices` returns `PermissionError: [Errno 13] Permission denied`, check `stat -c '%A %U %G %n' /run/usbmuxd /var/run/usbmuxd`.
- A socket like `srwxr-xr-x root root /run/usbmuxd` is not writable by the Hermes user, so `pymobiledevice3` cannot connect even when the daemon is active and `lsusb` sees the iPhone.
- Fix requires elevated host changes, such as restarting/overriding usbmuxd so the socket is group/world writable or adding the Hermes user to the group used by the socket. Do not keep retrying `iphone_list_devices` unchanged after this error.

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
