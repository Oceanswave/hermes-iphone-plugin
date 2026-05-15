# hermes-iphone-plugin

Native Hermes plugin for attached iPhone automation. The plugin exposes a static Hermes-owned iPhone tool catalog backed by direct Python libraries/protocols. It does not use Midscene and normal device operations are not an upstream CLI wrapper.

## Tools

- `iphone_status` — plugin readiness, safety policy, and backend diagnostics
- `iphone_list_devices` — USB/usbmux device discovery
- `iphone_ensure_wda` — ensure `tunneld`/WebDriverAgent are ready for WDA-backed controls
- `iphone_screenshot` — screenshot to a user-visible PNG path
- `iphone_screen_info` — WDA window size, orientation, and status
- `iphone_source` — WDA XML UI hierarchy/source tree
- `iphone_tree` — compact semantic tree parsed from WDA source
- `iphone_find_element` — find visible elements by text/type/enabled state
- `iphone_tap_text` — tap a visible enabled element by label/name/value
- `iphone_wait_for_text` — poll the UI tree until text appears
- `iphone_type_into_field` — tap a field by label/name and type into it
- `iphone_current_app` — report foreground app name and bundle id
- `iphone_launch_or_focus` — launch an app unless it is already foreground
- `iphone_open_url` — open a URL through WebInspector automation
- `iphone_launch_app` — launch an app by bundle identifier through DVT ProcessControl
- `iphone_tap` — coordinate tap through WDA
- `iphone_swipe` — coordinate swipe through WDA
- `iphone_type_text` — type into the focused field through WDA
- `iphone_press_button` — press `home`, `lock`, `volume_up`, or `volume_down` through WDA
- `iphone_prepare_text` — prepare a guarded text-message action
- `iphone_confirm_prepared_action` — consume a one-time confirmation token

## Backend behavior

The `pymobiledevice3` backend wires:

- device discovery through `pymobiledevice3.usbmux.list_devices`
- screenshot through WebDriverAgent first, with DVT screenshot fallback
- screen/source/tap/swipe/type/button through `WdaServiceClient`
- URL launch through pymobiledevice3 WebInspector automation
- app launch through DVT `ProcessControl`
- iOS 17+ developer-service routing through already-running RemoteXPC/tunneld where available

Some operations require extra device setup beyond USB trust:

- `iphone_list_devices` requires a running/writable `usbmuxd` socket.
- WDA-backed operations require Developer Mode, mounted developer services/DDI, installed/signed WebDriverAgentRunner, and reachable WDA device port 8100.
- open URL requires Safari Web Inspector and Remote Automation to be enabled.
- app launch may require iOS developer services to be available.

The plugin returns structured JSON errors when host/device prerequisites are missing.

## WDA lifecycle and self-healing

WDA-backed controls call `iphone_ensure_wda` automatically when WDA is unreachable, then retry once. This covers common cases where WDA exits between commands.

`iphone_ensure_wda` now prefers plugin-owned native lifecycle orchestration: it checks tunneld, starts tunneld if needed, launches the configured WDA runner, waits for readiness, and only falls back to a host helper script if the native path fails. The helper is compatibility fallback, not the primary user-facing workflow.

Default helper path on Sean's host:

```bash
/home/oceanswave/ensure-iphone-wda.sh
```

Useful manual commands:

```bash
/home/oceanswave/ensure-iphone-wda.sh 00008110-001855492644801E
/home/oceanswave/.hermes/hermes-agent/venv/bin/python -m pymobiledevice3 developer wda status --tunnel 00008110-001855492644801E
```

The helper remains idempotent: it checks tunneld, starts it if needed, launches WebDriverAgentRunner if needed, waits for WDA readiness, then prints `wda-ready`.

## Semantic automation layer

The semantic layer is built on `iphone_source` and avoids raw coordinate cruft for common UI tasks:

```text
iphone_tree             -> compact visible/accessibility-oriented element list
iphone_find_element     -> locate elements by text, type, enabled/visible state
iphone_tap_text         -> locate and tap an element center
iphone_wait_for_text    -> poll until UI text appears
iphone_type_into_field  -> tap a field/label and type text
iphone_current_app      -> inspect foreground app from WDA source
iphone_launch_or_focus  -> avoid relaunching an already-foreground app
```

Every semantic action records a small JSON action log under `~/iphone-action-logs`. Sensitive typed text is redacted to length metadata rather than persisted verbatim.

## Configuration

Environment variables:

- `HERMES_IPHONE_UDID` — default device UDID when callers omit `udid`
- `HERMES_IPHONE_WDA_BUNDLE_ID` — WDA runner bundle id; default `com.baristalabs.WebDriverAgentRunner.xctrunner`
- `HERMES_IPHONE_WDA_HELPER` — helper script path; default `~/ensure-iphone-wda.sh`
- `HERMES_IPHONE_AUTO_WDA` — set to `0`, `false`, `no`, or `off` to disable self-healing WDA bootstrap
- `HERMES_IPHONE_TUNNEL_HOST` / `HERMES_IPHONE_TUNNEL_PORT` — consumed by host helper scripts when present

`iphone_status` includes diagnostics for helper path/executable state, auto-WDA setting, tunneld discovery, WDA readiness, and artifact root.

## Safety

Potential external or destructive actions are prepared first and require explicit confirmation before execution. Text sending uses:

1. `iphone_prepare_text`
2. user approval of exact recipient/body
3. `iphone_confirm_prepared_action`

Prepared confirmation tokens are one-time and expire. Message bodies should not be retained in logs or memory after execution. Real SMS/iMessage sending is intentionally not implemented until the transport and final confirmation UX are explicitly chosen.

## Development

Use the Hermes agent venv on this host:

```bash
cd /home/oceanswave/hermes-iphone-plugin
/home/oceanswave/.hermes/hermes-agent/venv/bin/python -m pytest -q
rm -rf dist
/home/oceanswave/.hermes/hermes-agent/venv/bin/python -m build
uvx twine check dist/*
```

Install into Hermes' venv from this checkout:

```bash
/home/oceanswave/.hermes/hermes-agent/venv/bin/python -m pip install -e '/home/oceanswave/hermes-iphone-plugin[iphone]'
```

This checkout is also exposed to Hermes through a small shim at `~/.hermes/plugins/hermes-iphone-plugin`; package metadata provides the `hermes_agent.plugins` entry point.
