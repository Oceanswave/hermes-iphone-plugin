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
- Never send texts, place calls, delete data, buy anything, or change account/security settings without explicit user approval or Hermes built-in approval.
- For SMS/iMessage real sends, prefer `iphone_send_text`; it stages the draft and then uses Hermes' approval system (`/approve`, `/approve session`, `/approve always`, `/deny`, `/yolo`) before tapping Send. Use `iphone_prepare_text` for draft-only/manual fallback flows.
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
- `iphone_send_text`
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
- Use `iphone_describe_screen` for a compact current-screen summary and `iphone_tap_element` when selecting by id from the semantic tree.
- Use `iphone_type_into_field` for text entry; it logs text length but not text contents under `~/iphone-action-logs`.
- Use `iphone_last_trace` and `iphone_action_logs` to debug recent semantic actions.
- Use `iphone_source` only when raw XML is necessary; `iphone_tree` is the compact default.

Safe Messages flow:
- `iphone_prepare_text` now opens/focuses Messages, taps Compose, types recipient/body, captures a screenshot before send, locates Send, and returns a token.
- `iphone_send_text` is the high-level flow: it calls `iphone_prepare_text`, asks Hermes' built-in dangerous-action approval, then consumes the token and taps Send only if approval returns `once`, `session`, or `always`.
- The iPhone must be unlocked and awake before this flow; iOS denies launching Messages while locked.
- App launches are WDA-first. A locked phone returns `device_locked` quickly/actionably and should not fall back through slower DVT launch attempts.
- `iphone_prepare_text` must never tap Send.
- Do not call `iphone_confirm_prepared_action` manually until the user explicitly approves the exact recipient/body in chat. Prefer Hermes-native approval through `iphone_send_text` for normal sends.
- `iphone_confirm_prepared_action` consumes the one-time token and taps Send for `send_text` actions.
- Message body text must not be persisted to logs/traces; only body length and metadata are retained.

WDA/self-healing notes:
- The known WDA runner bundle id on Sean's phone is `com.baristalabs.WebDriverAgentRunner.xctrunner`.
- Prefer `remote tunneld --host 127.0.0.1 --port 49151 --protocol tcp`; `remote start-tunnel --script-mode` can report `Device is not connected` on this host.
- `iphone_ensure_wda` now prefers plugin-owned native lifecycle orchestration and only falls back to `/home/oceanswave/ensure-iphone-wda.sh` if native startup fails.
- The correct coordinate tap endpoint for this WDA build is `/session/<id>/wda/tap`, not `/session/<id>/wda/tap/0`.
- If WDA-backed actions fail, run `iphone_ensure_wda`, then retry once. If it still fails, report the structured error instead of looping.
