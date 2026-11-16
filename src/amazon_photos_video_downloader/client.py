"""Minimal client for the unofficial Amazon Photos (Cloud Drive) web API."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def load_cookies(source: str) -> dict[str, str]:
    """`source` is a path to a JSON file ({name: value} or browser-export list),
    or a raw 'a=b; c=d' cookie header string."""
    p = Path(source)
    text = p.read_text(encoding="utf-8") if p.is_file() else source
    text = text.strip()
    if text.startswith(("{", "[")):
        data = json.loads(text)
        if isinstance(data, list):
            return {c["name"]: c["value"] for c in data}
        return data
    return dict(part.strip().split("=", 1) for part in text.split(";") if "=" in part)


class AmazonPhotosClient:
    def __init__(self, cookies: dict[str, str], tld: str = "com"):
        self.base = f"https://www.amazon.{tld}/drive/v1"
        self.session = requests.Session()
        self.session.headers["User-Agent"] = UA
        self.session.cookies.update(cookies)
        if "session-id" in cookies:  # required by the API in addition to the cookies
            self.session.headers["x-amzn-sessionid"] = cookies["session-id"]

    def videos(self, page_size: int = 200) -> Iterator[dict]:
        params = {
            "asset": "ALL",
            "filters": "type:(VIDEOS) AND status:(AVAILABLE)",
            "limit": page_size,
            "searchContext": "customer",
            "sort": "['contentProperties.contentDate DESC']",
            "tempLink": "true",
            "resourceVersion": "V2",
            "ContentType": "JSON",
        }
        while True:
            r = self.session.get(f"{self.base}/search", params=params, timeout=60)
            if r.status_code in (401, 403):
                raise PermissionError("Amazon rejected the session; refresh your cookies.")
            r.raise_for_status()
            body = r.json()
            yield from body.get("data", [])
            token = body.get("nextToken")
            if not token:
                return
            params["startToken"] = token

    def download(self, node: dict, dest: Path, on_progress=None, should_stop=None) -> None:
        url = node.get("tempLink") or (
            f"{self.base}/nodes/{node['id']}/contentRedirection?querySuffix=%3Fdownload%3Dtrue"
        )
        tmp = dest.with_suffix(dest.suffix + ".part")
        with self.session.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                total = 0
                for chunk in r.iter_content(1 << 20):
                    if should_stop and should_stop():
                        raise InterruptedError("stopped")
                    f.write(chunk)
                    total += len(chunk)
                    if on_progress:
                        on_progress(total)
        tmp.replace(dest)

    def trash(self, node_ids: list[str]) -> None:
        """Move nodes to the Amazon Photos trash (recoverable there for ~30 days)."""
        r = self.session.patch(f"{self.base}/trash", json={
            "recurse": "true", "op": "add", "conflictResolution": "RENAME",
            "value": node_ids, "resourceVersion": "V2", "ContentType": "JSON",
        }, timeout=60)
        if r.status_code in (401, 403):
            raise PermissionError("Amazon rejected the session; refresh your cookies.")
        r.raise_for_status()
