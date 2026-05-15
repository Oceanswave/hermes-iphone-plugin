---
name: operator
description: Operate attached iPhones safely through hermes-iphone-plugin tools.
---

# iPhone Operator

Use this skill when controlling an attached iPhone through the native Hermes iPhone plugin.

Rules:
- Start with `iphone_status` and `iphone_list_devices`.
- For WDA-backed controls, call `iphone_ensure_wda` first when reliability matters; tap/type/button/swipe also self-heal by calling the helper and retrying once.
- Prefer deterministic semantic tools (`iphone_tree`, `iphone_find_element`, `iphone_tap_text`, `iphone_wait_for_text`, `iphone_type_into_field`, `iphone_current_app`) over vision-only automation or raw coordinate tapping.
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
- `iphone_tree`
- `iphone_find_element`
- `iphone_tap_text`
- `iphone_wait_for_text`
- `iphone_type_into_field`
- `iphone_current_app`
- `iphone_launch_or_focus`
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

Semantic automation notes:
- Use `iphone_current_app` before app-specific flows.
- Use `iphone_launch_or_focus` instead of blindly launching apps.
- Use `iphone_find_element`/`iphone_tap_text` for buttons and labels before falling back to `iphone_tap` coordinates.
- Use `iphone_type_into_field` for text entry; it logs text length but not text contents under `~/iphone-action-logs`.
- Use `iphone_source` only when raw XML is necessary; `iphone_tree` is the compact default.

WDA/self-healing notes:
- The known WDA runner bundle id on Sean's phone is `com.baristalabs.WebDriverAgentRunner.xctrunner`.
- Prefer `remote tunneld --host 127.0.0.1 --port 49151 --protocol tcp`; `remote start-tunnel --script-mode` can report `Device is not connected` on this host.
- `iphone_ensure_wda` now prefers plugin-owned native lifecycle orchestration and only falls back to `/home/oceanswave/ensure-iphone-wda.sh` if native startup fails.
- The correct coordinate tap endpoint for this WDA build is `/session/<id>/wda/tap`, not `/session/<id>/wda/tap/0`.
- If WDA-backed actions fail, run `iphone_ensure_wda`, then retry once. If it still fails, report the structured error instead of looping.
