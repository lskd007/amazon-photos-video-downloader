# amazon-photos-video-downloader

Download videos from Amazon Photos. Runs on Windows and macOS.

## Setup
Windows (PowerShell):

    python -m venv .venv; .venv\Scripts\activate; pip install -e .[dev]

macOS (Terminal):

    python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'

## Desktop app
    apvd-gui

- **Sign in to Amazon** opens an Amazon login window. When you reach Photos, the session cookies are saved to `~/.apvd/cookies.json` (no DevTools needed). Amazon Japan is the default; change it under Settings.
- The window shows the current download as a strip of film frames, counts, and a list for this session.
- Settings (output folder, Amazon site, auto-check interval) are saved in `~/.apvd/config.json`.

## Command line
The CLI reuses the GUI's sign-in and settings:

    apvd                         # one sync
    apvd --watch 30              # keep running, check every 30 minutes
    apvd --trash                 # after each verified download, move the video to the Amazon Photos trash
    apvd -o ~/Videos --tld com   # override folder / Amazon site

## Run in the background
    apvd --install-schedule 30    # every 30 minutes while you are logged in
    apvd --uninstall-schedule

Uses Task Scheduler on Windows and a launchd agent on macOS. Output goes to `~/.apvd/apvd.log`.
The schedule remembers the Python environment it was installed from, so re-run the command if you move the project.
When cookies expire the log says "refresh your cookies": open `apvd-gui` and sign in again.

## Notes
- Amazon has no public API; this uses the web endpoints with your session cookies. Treat `~/.apvd/cookies.json` like a password.
- Cookies are per machine: sign in separately on each computer.
