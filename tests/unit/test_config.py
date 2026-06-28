"""Config 단위 테스트"""
import pytest

from src.config import Config


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("TG_TOKEN", "tok")
    monkeypatch.setenv("TG_CHAT", "chat")
    cfg = Config.from_env()
    assert cfg.telegram_token == "tok"
    assert cfg.telegram_chat_id == "chat"
    assert cfg.db_path == "polywatch.db"
    assert cfg.scan_interval_sec == 3600
    assert cfg.monitor_interval_sec == 300
    assert cfg.whale_min_usd == 50_000.0


def test_config_custom_intervals(monkeypatch):
    monkeypatch.setenv("TG_TOKEN", "t")
    monkeypatch.setenv("TG_CHAT", "c")
    monkeypatch.setenv("SCAN_INTERVAL_SEC", "7200")
    monkeypatch.setenv("MONITOR_INTERVAL_SEC", "60")
    cfg = Config.from_env()
    assert cfg.scan_interval_sec == 7200
    assert cfg.monitor_interval_sec == 60


def test_config_missing_token_raises(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(RuntimeError, match="TG_TOKEN"):
        Config.from_env()
