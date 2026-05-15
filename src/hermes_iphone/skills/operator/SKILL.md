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

Device-control prerequisites:
- `iphone_screenshot` uses pymobiledevice3's ScreenshotService. If it returns `InvalidServiceError`, the phone is trusted but is not exposing the needed developer screenshot service.
- `iphone_open_url` uses Safari WebInspector automation. Enable Safari Web Inspector and Remote Automation on the iPhone before expecting it to work.
- `iphone_launch_app` uses DVT ProcessControl and may require Developer Mode / developer services.
- `iphone_tap`, `iphone_type_text`, and `iphone_press_button` use WebDriverAgent. If WDA is not running/reachable, report that device-side prerequisite instead of retrying blindly.

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
