from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def default_state_root() -> Path:
    try:
        from hermes_constants import get_hermes_home  # type: ignore

        return Path(get_hermes_home()) / "plugins" / "iphone"
    except Exception:
        return (
            Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
            / "plugins"
            / "iphone"
        )


class PluginState:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else default_state_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.pending_path = self.root / "pending_actions.json"

    def _read_pending(self) -> dict[str, Any]:
        if not self.pending_path.exists():
            return {}
        try:
            data = json.loads(self.pending_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _write_pending(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            prefix="pending-actions-", suffix=".json", dir=str(self.root)
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp, self.pending_path)

    def put_pending_action(self, token: str, action: dict[str, Any]) -> None:
        data = self._read_pending()
        data[token] = action
        self._write_pending(data)

    def pop_pending_action(self, token: str) -> dict[str, Any] | None:
        data = self._read_pending()
        action = data.pop(token, None)
        self._write_pending(data)
        return action if isinstance(action, dict) else None

    def cleanup_expired(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        data = self._read_pending()
        kept = {
            k: v
            for k, v in data.items()
            if isinstance(v, dict) and float(v.get("expires_at", 0)) > now
        }
        removed = len(data) - len(kept)
        if removed:
            self._write_pending(kept)
        return removed
