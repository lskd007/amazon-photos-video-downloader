"""Paths and settings shared by the GUI, CLI and scheduler (Windows and macOS)."""
from __future__ import annotations

import json
from pathlib import Path

APP_DIR = Path.home() / ".apvd"
CONFIG = APP_DIR / "config.json"
COOKIES = APP_DIR / "cookies.json"
LOG = APP_DIR / "apvd.log"
DEFAULTS = {"output": str(Path.home() / "Videos" / "AmazonPhotos"), "tld": "co.jp",
            "interval": 30, "auto": True, "trash": True}


def load_config() -> dict:
    saved = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    return {**DEFAULTS, **saved}


def save_config(cfg: dict) -> None:
    APP_DIR.mkdir(exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2))
