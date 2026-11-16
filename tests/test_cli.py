import pytest

from amazon_photos_video_downloader import cli, scheduler
from amazon_photos_video_downloader.client import load_cookies


def test_requires_cookies(monkeypatch, tmp_path):
    monkeypatch.delenv("APVD_COOKIES", raising=False)
    monkeypatch.setattr(cli, "COOKIES", tmp_path / "missing.json")  # never use the real sign-in
    with pytest.raises(SystemExit):
        cli.main([])


def test_load_cookies_string():
    assert load_cookies("a=b; c=d=e") == {"a": "b", "c": "d=e"}


def test_scheduler_command_is_cross_platform():
    cmd = scheduler._command()
    assert cmd[1:3] == ["-m", "amazon_photos_video_downloader.cli"]
    assert "--log-file" in cmd
