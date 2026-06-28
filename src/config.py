"""환경 변수에서 설정 로드."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    telegram_token: str
    telegram_chat_id: str
    db_path: str
    scan_interval_sec: int
    monitor_interval_sec: int
    whale_min_usd: float

    @classmethod
    def from_env(cls) -> "Config":
        def require(key: str) -> str:
            v = os.environ.get(key, "").strip()
            if not v:
                raise RuntimeError(f"Missing required env var: {key}")
            return v

        return cls(
            telegram_token=require("TG_TOKEN"),
            telegram_chat_id=require("TG_CHAT"),
            db_path=os.environ.get("DB_PATH", "polywatch.db"),
            scan_interval_sec=int(os.environ.get("SCAN_INTERVAL_SEC", "3600")),
            monitor_interval_sec=int(os.environ.get("MONITOR_INTERVAL_SEC", "300")),
            whale_min_usd=float(os.environ.get("WHALE_MIN_USD", "50000")),
        )
