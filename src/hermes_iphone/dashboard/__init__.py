from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

DASHBOARD_PLUGIN_NAME = "hermes-iphone-plugin"


def get_hermes_home() -> Path:
    try:
        from importlib import import_module

        module = import_module("hermes_constants")
        return Path(module.get_hermes_home())
    except Exception:
        import os

        return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def source_dashboard_dir() -> Path:
    return Path(__file__).resolve().parent


def user_dashboard_dir() -> Path:
    return get_hermes_home() / "plugins" / DASHBOARD_PLUGIN_NAME / "dashboard"


def ensure_dashboard_installed() -> dict[str, Any]:
    """Mirror packaged dashboard assets into Hermes' dashboard plugin tree."""
    src = source_dashboard_dir()
    dst = user_dashboard_dir()
    if not src.exists():
        return {
            "ok": False,
            "installed": False,
            "reason": "packaged dashboard assets are missing",
            "path": str(dst),
        }
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        if child.name == "__pycache__":
            continue
        target = dst / child.name
        if child.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(
                child,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            shutil.copy2(child, target)
    return {"ok": True, "installed": True, "path": str(dst)}
