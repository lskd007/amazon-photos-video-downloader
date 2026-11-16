"""Desktop GUI: sign in to Amazon Photos (captures cookies) and track downloads."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import webview

from .client import AmazonPhotosClient
from .config import APP_DIR, COOKIES, DEFAULTS, load_config, save_config
from .sync import Tracker, sync_once

UI = Path(__file__).parent / "ui" / "index.html"


class Api:
    """Methods here are callable from the page as pywebview.api.<name>()."""

    def __init__(self):
        APP_DIR.mkdir(exist_ok=True)
        self.cfg = load_config()
        self.tracker = Tracker()
        self.stop = threading.Event()
        self.main_window = None
        self.login_window = None
        self.expired = False
        self.signing_in = False
        self._next_auto = time.time() + 5
        threading.Thread(target=self._scheduler, daemon=True).start()

    # ---- state for the UI -------------------------------------------------
    def get_state(self):
        return {"cfg": self.cfg, "connected": COOKIES.exists() and not self.expired,
                "expired": self.expired, "signing_in": self.signing_in,
                "sync": self.tracker.snapshot()}

    def set_config(self, **kw):
        self.cfg.update({k: v for k, v in kw.items() if k in DEFAULTS})
        save_config(self.cfg)
        return self.cfg

    def choose_folder(self):
        r = self.main_window.create_file_dialog(webview.FOLDER_DIALOG, directory=self.cfg["output"])
        if r:
            self.set_config(output=r[0])
        return self.cfg

    # ---- sign in ----------------------------------------------------------
    def sign_in(self):
        if self.login_window or self.signing_in:
            return
        self.signing_in = True
        url = f"https://www.amazon.{self.cfg['tld']}/photos"
        self.login_window = webview.create_window("Sign in to Amazon Photos", url, width=520, height=760)
        threading.Thread(target=self._watch_login, args=(self.login_window,), daemon=True).start()

    def _watch_login(self, win):
        closed = threading.Event()
        win.events.closed += closed.set
        try:
            while not closed.is_set():
                time.sleep(2)
                try:
                    url = win.get_current_url() or ""
                    cookies = {}
                    for jar in win.get_cookies():
                        for key, morsel in jar.items():
                            cookies[key] = morsel.value
                except Exception:
                    continue
                signed = any(k.startswith(("at-", "sess-at-")) for k in cookies)
                if signed and "/photos" in url and "signin" not in url and "/ap/" not in url:
                    COOKIES.write_text(json.dumps(cookies, indent=2))
                    self.expired = False
                    win.destroy()
                    break
        finally:
            self.login_window = None
            self.signing_in = False

    def sign_out(self):
        COOKIES.unlink(missing_ok=True)
        self.expired = False
        return True

    # ---- syncing ----------------------------------------------------------
    def sync_now(self):
        if self.tracker.running or not COOKIES.exists():
            return False
        self.stop.clear()
        threading.Thread(target=self._run_sync, daemon=True).start()
        return True

    def stop_sync(self):
        self.stop.set()

    def _run_sync(self):
        try:
            client = AmazonPhotosClient(json.loads(COOKIES.read_text()), self.cfg["tld"])
            sync_once(client, Path(self.cfg["output"]), log=lambda m: None,
                      tracker=self.tracker, stop=self.stop, trash=bool(self.cfg.get("trash")))
        except PermissionError:
            self.expired = True
        except Exception:
            pass  # tracker.error already holds the message

    def _scheduler(self):
        while True:
            time.sleep(5)
            if (self.cfg["auto"] and COOKIES.exists() and not self.expired
                    and not self.tracker.running and time.time() >= self._next_auto):
                self._next_auto = time.time() + float(self.cfg["interval"]) * 60
                self.sync_now()


def main():
    api = Api()
    api.main_window = webview.create_window("Amazon Photos videos", UI.as_uri(), js_api=api,
                                            width=880, height=720, min_size=(640, 520))
    webview.start(private_mode=False, storage_path=str(APP_DIR / "webview"))


if __name__ == "__main__":
    main()
