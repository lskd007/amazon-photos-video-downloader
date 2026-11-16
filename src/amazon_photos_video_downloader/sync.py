from __future__ import annotations

import json
import queue
import re
import threading
import time
from pathlib import Path

from .client import AmazonPhotosClient


def _safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)


class Tracker:
    """Thread-safe record of the current sync, read by the GUI."""

    def __init__(self):
        self.lock = threading.Lock()
        self.items: dict[str, dict] = {}
        self.running = False
        self.error: str | None = None
        self.already = 0
        self.last_run: float | None = None

    def update(self, node_id: str, **kw):
        with self.lock:
            self.items[node_id].update(kw)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "error": self.error,
                "already": self.already,
                "last_run": self.last_run,
                "items": [dict(v) for v in self.items.values()],
            }


def _local_copy(out: Path, node: dict) -> bool:
    """True if a local file for this node exists with the size Amazon reports."""
    expected = (node.get("contentProperties") or {}).get("size") or 0
    if not expected:
        return False  # can't verify, so never trash
    base = out / _safe(node.get("name") or f"{node['id']}.mp4")
    alt = out / f"{base.stem}_{node['id'][:8]}{base.suffix}"
    return any(f.is_file() and f.stat().st_size == expected for f in (base, alt))


class _Trasher:
    """Background worker: batches trash requests so downloads never wait on them."""

    BATCH, WAIT = 50, 1.0

    def __init__(self, client, log):
        self.client, self.log = client, log
        self.q: queue.Queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def put(self, node: dict) -> None:
        self.q.put(node)

    def close(self) -> None:
        self.q.put(None)
        self.thread.join()

    def _run(self) -> None:
        finished = False
        while not finished:
            batch = []
            item = self.q.get()
            while True:
                if item is None:
                    finished = True
                    break
                batch.append(item)
                if len(batch) >= self.BATCH:
                    break
                try:
                    item = self.q.get(timeout=self.WAIT)
                except queue.Empty:
                    break
            if batch:
                self._send(batch)

    def _send(self, batch: list[dict]) -> None:
        try:
            self.client.trash([n["id"] for n in batch])
            self.log(f"Moved {len(batch)} video(s) to Amazon Photos trash")
        except Exception as e:
            self.log(f"  could not move {len(batch)} video(s) to trash: {e}")


def sync_once(client: AmazonPhotosClient, out: Path, log=print,
              tracker: Tracker | None = None, stop: threading.Event | None = None,
              trash: bool = False) -> int:
    out.mkdir(parents=True, exist_ok=True)
    state_file = out / ".downloaded.json"
    done: set[str] = set(json.loads(state_file.read_text())) if state_file.exists() else set()
    if tracker:
        with tracker.lock:
            tracker.running, tracker.error, tracker.items = True, None, {}
            tracker.already = len(done)
    count = 0
    trasher = None
    try:
        listed = list(client.videos())
        pending = [n for n in listed if n["id"] not in done]
        trasher = _Trasher(client, log) if trash else None
        if trasher:  # videos downloaded earlier that are still online
            for n in listed:
                if n["id"] in done:
                    if _local_copy(out, n):
                        trasher.put(n)
                    else:
                        log(f"Not trashing {n.get('name') or n['id']}: no verified local copy")
        if tracker:
            with tracker.lock:
                for n in pending:
                    tracker.items[n["id"]] = {
                        "id": n["id"], "name": n.get("name") or n["id"],
                        "size": (n.get("contentProperties") or {}).get("size") or 0,
                        "done": 0, "status": "queued", "error": None,
                    }

        def should_stop() -> bool:
            return bool(stop and stop.is_set())

        for node in pending:
            if should_stop():
                break
            name = _safe(node.get("name") or f"{node['id']}.mp4")
            dest = out / name
            if dest.exists():
                dest = out / f"{dest.stem}_{node['id'][:8]}{dest.suffix}"
            log(f"Downloading {dest.name}")
            if tracker:
                tracker.update(node["id"], status="downloading")
            progress = None
            if tracker:
                progress = lambda b, i=node["id"]: tracker.update(i, done=b)  # noqa: E731
            try:
                client.download(node, dest, on_progress=progress, should_stop=should_stop)
            except InterruptedError:
                if tracker:
                    tracker.update(node["id"], status="queued", done=0)
                break
            except Exception as e:  # keep going; retry next run
                log(f"  failed: {e}")
                if tracker:
                    tracker.update(node["id"], status="failed", error=str(e))
                continue
            expected = (node.get("contentProperties") or {}).get("size") or 0
            verified = not expected or dest.stat().st_size == expected
            if not verified:
                log(f"  size mismatch ({dest.stat().st_size} != {expected}); keeping in Amazon Photos")
            done.add(node["id"])
            state_file.write_text(json.dumps(sorted(done)))
            count += 1
            if trasher and verified:  # only after the file is safely on disk
                trasher.put(node)
            if tracker:
                tracker.update(node["id"], status="done")
        log(f"Done: {count} new video(s).")
    except Exception as e:
        if tracker:
            with tracker.lock:
                tracker.error = str(e)
        raise
    finally:
        if trasher:
            trasher.close()  # flush remaining trash requests
        if tracker:
            with tracker.lock:
                tracker.running, tracker.last_run = False, time.time()
    return count


def watch(client: AmazonPhotosClient, out: Path, interval_min: float, log=print,
          trash: bool = False) -> None:
    while True:
        try:
            sync_once(client, out, log, trash=trash)
        except Exception as e:
            log(f"Sync error: {e}")
        time.sleep(interval_min * 60)
