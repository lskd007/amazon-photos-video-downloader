"""Run a sync in the background on a timer: Task Scheduler (Windows) or launchd (macOS)."""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

from .config import COOKIES, LOG, load_config

NAME = "AmazonPhotosVideoDownloader"
LABEL = "com.apvd.videodownloader"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _command() -> list[str]:
    py = Path(sys.executable)
    if sys.platform == "win32":  # pythonw runs without a console window
        pyw = py.with_name("pythonw.exe")
        py = pyw if pyw.exists() else py
    cfg = load_config()
    return [str(py), "-m", "amazon_photos_video_downloader.cli", "--cookies", str(COOKIES),
            "-o", cfg["output"], "--tld", cfg["tld"], "--log-file", str(LOG)]


def install(interval_min: int) -> str:
    if sys.platform == "win32":
        tr = subprocess.list2cmdline(_command())
        subprocess.run(["schtasks", "/Create", "/TN", NAME, "/SC", "MINUTE", "/MO", str(interval_min),
                        "/TR", tr, "/F"], check=True)
        return f"Scheduled task '{NAME}' runs every {interval_min} min while you are logged in."
    if sys.platform == "darwin":
        PLIST.parent.mkdir(parents=True, exist_ok=True)
        PLIST.write_bytes(plistlib.dumps({
            "Label": LABEL, "ProgramArguments": _command(), "RunAtLoad": True,
            "StartInterval": interval_min * 60,
        }))
        uid = str(os.getuid())
        subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST)], capture_output=True)
        subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(PLIST)], check=True)
        return f"launchd agent '{LABEL}' runs every {interval_min} min while you are logged in."
    raise SystemExit(f"Background scheduling is not supported on {sys.platform}.")


def uninstall() -> str:
    if sys.platform == "win32":
        subprocess.run(["schtasks", "/Delete", "/TN", NAME, "/F"], check=True)
    elif sys.platform == "darwin":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(PLIST)], capture_output=True)
        PLIST.unlink(missing_ok=True)
    else:
        raise SystemExit(f"Background scheduling is not supported on {sys.platform}.")
    return "Background schedule removed."
