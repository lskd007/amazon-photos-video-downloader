import argparse
import os
import time
from pathlib import Path

from . import __version__
from .client import AmazonPhotosClient, load_cookies
from .config import COOKIES, load_config
from .sync import sync_once, watch


def main(argv=None) -> int:
    cfg = load_config()
    p = argparse.ArgumentParser(prog="apvd", description="Amazon Photos video downloader")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("-o", "--output", default=cfg["output"], help="output directory")
    p.add_argument("--cookies", default=os.environ.get("APVD_COOKIES") or (str(COOKIES) if COOKIES.exists() else None),
                   help="cookies JSON file or 'name=value; ...' string (default: the GUI's saved sign-in)")
    p.add_argument("--tld", default=cfg["tld"], help="Amazon domain suffix: co.jp, com, de, ...")
    p.add_argument("--watch", type=float, metavar="MINUTES",
                   help="keep running and check for new videos every N minutes")
    p.add_argument("--trash", action="store_true", default=cfg["trash"],
                   help="after a verified download, move the video to the Amazon Photos trash")
    p.add_argument("--log-file", help="append log output to this file (needed with pythonw)")
    p.add_argument("--install-schedule", type=int, metavar="MINUTES",
                   help="run in the background every N minutes (Task Scheduler / launchd)")
    p.add_argument("--uninstall-schedule", action="store_true", help="remove the background schedule")
    args = p.parse_args(argv)

    if args.install_schedule or args.uninstall_schedule:
        from . import scheduler
        print(scheduler.uninstall() if args.uninstall_schedule else scheduler.install(args.install_schedule))
        return 0
    if not args.cookies:
        p.error("no sign-in found: run apvd-gui and sign in, or pass --cookies / set APVD_COOKIES")

    client = AmazonPhotosClient(load_cookies(args.cookies), args.tld)
    out = Path(args.output)
    log = print
    if args.log_file:
        lf = Path(args.log_file)
        lf.parent.mkdir(parents=True, exist_ok=True)

        def log(msg):
            with open(lf, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

    try:
        if args.watch:
            watch(client, out, args.watch, log, trash=args.trash)
        else:
            sync_once(client, out, log, trash=args.trash)
    except Exception as e:
        log(f"Error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
