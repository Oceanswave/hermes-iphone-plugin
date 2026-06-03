from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

from .state import PluginState

CONFIRMATION_REQUIRED_ACTIONS = {
    "send_text",
    "place_call",
    "delete",
    "purchase",
    "settings_change",
}


def requires_confirmation(action: str) -> bool:
    return action.strip().lower() in CONFIRMATION_REQUIRED_ACTIONS


@dataclass
class SafetyPolicy:
    state: PluginState
    ttl_seconds: int = 300

    def prepare(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = action.strip().lower()
        token = secrets.token_urlsafe(18)
        expires_at = time.time() + self.ttl_seconds
        record = {
            "action": normalized,
            "payload": payload,
            "created_at": time.time(),
            "expires_at": expires_at,
            "requires_confirmation": requires_confirmation(normalized),
        }
        self.state.put_pending_action(token, record)
        return {
            "ok": True,
            "action": normalized,
            "token": token,
            "expires_at": expires_at,
            "requires_confirmation": record["requires_confirmation"],
            "next_step": "Call iphone_confirm_prepared_action with this token only after the user explicitly approves.",
        }

    def confirm(self, token: str) -> dict[str, Any]:
        self.state.cleanup_expired()
        record = self.state.pop_pending_action(token)
        if not record:
            return {"ok": False, "error": "unknown_or_expired_token"}
        return {"ok": True, **record}
