from amazon_photos_video_downloader.sync import sync_once


class FakeClient:
    def __init__(self, size_ok=True):
        self.size_ok, self.trashed = size_ok, []

    def videos(self):
        yield {"id": "abc12345", "name": "a.mp4", "contentProperties": {"size": 3}}

    def download(self, node, dest, on_progress=None, should_stop=None):
        dest.write_bytes(b"123" if self.size_ok else b"1")

    def trash(self, ids):
        self.trashed += ids


def test_trash_after_verified_download(tmp_path):
    c = FakeClient()
    sync_once(c, tmp_path, log=lambda m: None, trash=True)
    assert c.trashed == ["abc12345"]


def test_no_trash_by_default_or_on_size_mismatch(tmp_path):
    c = FakeClient()
    sync_once(c, tmp_path / "x", log=lambda m: None)
    assert c.trashed == []
    c = FakeClient(size_ok=False)
    sync_once(c, tmp_path / "y", log=lambda m: None, trash=True)
    assert c.trashed == []


def test_trashes_previously_downloaded_only_if_local_copy_verified(tmp_path):
    import json
    (tmp_path / ".downloaded.json").write_text(json.dumps(["abc12345"]))
    (tmp_path / "a.mp4").write_bytes(b"123")
    c = FakeClient()
    sync_once(c, tmp_path, log=lambda m: None, trash=True)
    assert c.trashed == ["abc12345"]

    (tmp_path / "a.mp4").write_bytes(b"1")  # wrong size -> keep online
    c = FakeClient()
    sync_once(c, tmp_path, log=lambda m: None, trash=True)
    assert c.trashed == []
