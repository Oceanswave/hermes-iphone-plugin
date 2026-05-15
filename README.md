# hermes-iphone-plugin

Native Hermes plugin for attached iPhone automation. This package exposes a static Hermes-owned iPhone tool catalog backed by direct Python libraries/protocols, not Midscene and not an upstream automation CLI wrapper.

## Tools

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

## Implemented backend behavior

The `pymobiledevice3` backend now wires:

- device discovery through `pymobiledevice3.usbmux.list_devices`
- screenshots through `ScreenshotService`
- URL launch through pymobiledevice3 WebInspector automation
- app launch through DVT `ProcessControl`
- tap/type/button through WebDriverAgent (`WdaServiceClient`)

Some operations require additional device-side setup beyond USB trust:

- `iphone_list_devices` requires a running/writable `usbmuxd` socket.
- screenshot / app launch may require iOS developer services to be available.
- open URL requires Safari Web Inspector and Remote Automation to be enabled.
- tap/type/button require a reachable WebDriverAgent service.

The plugin returns structured JSON errors when those host/device prerequisites are missing.

## Safety

Potential external or destructive actions are prepared first and require explicit confirmation before execution. Text sending uses:

1. `iphone_prepare_text`
2. user approval of exact recipient/body
3. `iphone_confirm_prepared_action`

## Development

Use the Hermes agent venv on this host:

```bash
/home/oceanswave/.hermes/hermes-agent/venv/bin/python -m pytest tests -q
/home/oceanswave/.hermes/hermes-agent/venv/bin/python -m build --wheel
```
