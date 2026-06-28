"""메인 러너: MarketScanService(1h) + PositionMonitor(5min) 스케줄링."""
import logging
import sqlite3
import time

from dotenv import load_dotenv

from src.application.market_scan import MarketScanService
from src.application.position_monitor import PositionMonitor
from src.config import Config
from src.infrastructure.polymarket_adapter import PolymarketAdapter
from src.infrastructure.sqlite_repos import SQLiteMarketRepo, SQLiteWalletRepo
from src.infrastructure.telegram_adapter import TelegramAdapter

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run(cfg: Config) -> None:
    conn = sqlite3.connect(cfg.db_path)

    market_repo = SQLiteMarketRepo(conn)
    wallet_repo = SQLiteWalletRepo(conn)
    market_repo.init_schema()
    wallet_repo.init_schema()

    poly = PolymarketAdapter()
    alert = TelegramAdapter(token=cfg.telegram_token, chat_id=cfg.telegram_chat_id)

    scanner = MarketScanService(poly, market_repo)
    monitor = PositionMonitor(poly, alert, market_repo, wallet_repo,
                              whale_min_usd=cfg.whale_min_usd)

    last_scan = 0.0

    log.info("polywatch started — scan=%ds monitor=%ds",
             cfg.scan_interval_sec, cfg.monitor_interval_sec)

    while True:
        now = time.monotonic()

        if now - last_scan >= cfg.scan_interval_sec:
            try:
                scanner.run_once()
                log.info("market scan complete, watching %d markets",
                         len(market_repo.get_watched()))
            except Exception as exc:
                log.error("scan error: %s", exc)
            last_scan = now

        try:
            monitor.run_once()
        except Exception as exc:
            log.error("monitor error: %s", exc)

        time.sleep(cfg.monitor_interval_sec)


def main() -> None:
    cfg = Config.from_env()
    run(cfg)


if __name__ == "__main__":
    main()
