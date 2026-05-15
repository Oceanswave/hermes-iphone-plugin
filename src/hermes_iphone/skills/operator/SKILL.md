---
name: operator
description: Operate attached iPhones safely through hermes-iphone-plugin tools.
---

# iPhone Operator

Use this skill when controlling an attached iPhone through the native Hermes iPhone plugin.

Rules:
- Start with `iphone_status` and `iphone_list_devices`.
- For WDA-backed controls, call `iphone_ensure_wda` first when reliability matters; tap/type/button/swipe also self-heal by calling the helper and retrying once.
- Prefer deterministic tools (`iphone_source`, `iphone_screen_info`, coordinate tools) over vision-only automation.
- Never send texts, place calls, delete data, buy anything, or change account/security settings without explicit user approval.
- For SMS/iMessage, use `iphone_prepare_text` first. Only call `iphone_confirm_prepared_action` after the user approves the exact recipient/body.
- Report which backend is active and whether any capability is not yet implemented on this host.

Current tools:
- `iphone_status`
- `iphone_list_devices`
- `iphone_ensure_wda`
- `iphone_screenshot`
- `iphone_screen_info`
- `iphone_source`
- `iphone_open_url`
- `iphone_launch_app`
- `iphone_tap`
- `iphone_swipe`
- `iphone_type_text`
- `iphone_press_button`
- `iphone_prepare_text`
- `iphone_confirm_prepared_action`

Linux usbmuxd troubleshooting:
- If `iphone_list_devices` returns `PermissionError: [Errno 13] Permission denied`, check `stat -c '%A %U %G %n' /run/usbmuxd /var/run/usbmuxd`.
- A socket like `srwxr-xr-x root root /run/usbmuxd` is not writable by the Hermes user, so `pymobiledevice3` cannot connect even when the daemon is active and `lsusb` sees the iPhone.
- Fix requires elevated host changes, such as restarting/overriding usbmuxd so the socket is group/world writable or adding the Hermes user to the group used by the socket. Do not keep retrying `iphone_list_devices` unchanged after this error.

Device-control prerequisites:
- `iphone_screenshot` uses WDA first with DVT screenshot fallback.
- `iphone_screen_info`, `iphone_source`, `iphone_tap`, `iphone_swipe`, `iphone_type_text`, and `iphone_press_button` use WebDriverAgent.
- `iphone_open_url` uses Safari WebInspector automation. Enable Safari Web Inspector and Remote Automation on the iPhone before expecting it to work.
- `iphone_launch_app` uses DVT ProcessControl and may require Developer Mode / developer services.
- On iOS 17+, developer services usually require `pymobiledevice3 remote tunneld` running as root; on Sean's host use `/home/oceanswave/ensure-iphone-wda.sh [UDID]`.

WDA/self-healing notes:
- The known WDA runner bundle id on Sean's phone is `com.baristalabs.WebDriverAgentRunner.xctrunner`.
- Prefer `remote tunneld --host 127.0.0.1 --port 49151 --protocol tcp`; `remote start-tunnel --script-mode` can report `Device is not connected` on this host.
- The correct coordinate tap endpoint for this WDA build is `/session/<id>/wda/tap`, not `/session/<id>/wda/tap/0`.
- If WDA-backed actions fail, run `iphone_ensure_wda`, then retry once. If it still fails, report the structured error instead of looping.
