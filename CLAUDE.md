# amazon-photos-video-downloader

Cross-platform (Windows + macOS) Python app that downloads videos from Amazon Photos using the unofficial web API, authenticated with browser session cookies. Has a desktop GUI (`apvd-gui`) and a CLI (`apvd`), and can run unattended via Task Scheduler / launchd.

## Layout
- `src/amazon_photos_video_downloader/client.py` - `AmazonPhotosClient` (search videos, download) and `load_cookies`.
- `src/amazon_photos_video_downloader/sync.py` - `sync_once` / `watch`, `Tracker` for GUI progress; finished IDs in `<output>/.downloaded.json`.
- `src/amazon_photos_video_downloader/config.py` - shared paths/settings in `~/.apvd` (GUI, CLI, scheduler).
- `src/amazon_photos_video_downloader/cli.py` - argparse entry point (`--cookies`, `-o`, `--tld`, `--watch`, `--log-file`, `--install-schedule`).
- `src/amazon_photos_video_downloader/scheduler.py` - Task Scheduler (Windows) / launchd (macOS) installer.
- `src/amazon_photos_video_downloader/gui.py` + `ui/index.html` - pywebview app; the page polls `Api.get_state()` every second.
- `tests/` - pytest.

## Commands
- Setup: create a venv, then `pip install -e .[dev]` (Windows: `.venv\Scripts\`, macOS: `.venv/bin/`).
- Test: `python -m pytest -q`
- Run: `apvd-gui`, or `apvd` (uses the `~/.apvd` sign-in).

## Notes
- Amazon endpoints are undocumented. The API needs the `x-amzn-sessionid` header (= `session-id` cookie) in addition to cookies. Verified against a real Japan account: listing and downloads work.
- Never commit or log cookie values (`cookies*.json`, `logs/`, `downloads/` are git-ignored).
- Scheduled runs use `pythonw` on Windows (no console), so output must go through the `log` callable / `--log-file`, not bare `print`.
- Downloads write to a `.part` file and rename on completion; keep that so interrupted runs don't leave corrupt videos marked done.
- Keep `sync_once` usable without a tracker (CLI path).

## Cross-platform rules
- Use `pathlib` / `Path.home()`; no hard-coded `\` paths. Keep platform branches inside `scheduler.py`.
- Tests must never touch the real `~/.apvd` sign-in: `cli.main([])` would start a real sync. Monkeypatch `cli.COOKIES`.
- macOS is untested (written without access to a Mac): GUI sign-in cookie capture via WebKit and launchd are the parts to verify first.
