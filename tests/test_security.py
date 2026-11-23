from app.config import load_settings
from app.logger import sanitize


def test_sanitizer_redacts_token_hash_and_windows_profile_path():
    text = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmno api_hash=0123456789abcdef0123456789abcdef C:\\Users\\Alice\\private\\log.txt"
    clean = sanitize(text)
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in clean
    assert "0123456789abcdef0123456789abcdef" not in clean
    assert "C:\\Users\\Alice" not in clean
    assert clean.count("***REDACTED***") == 3


def test_settings_reject_exposed_web_host(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_HOST", "0.0.0.0")
    try:
        load_settings(tmp_path / "missing.env")
    except ValueError as exc:
        assert "loopback" in str(exc)
    else:
        raise AssertionError("non-loopback web host must be rejected")
