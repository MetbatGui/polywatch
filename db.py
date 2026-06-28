"""SQLite 스키마 + 수집 함수"""
import sqlite3, time
from pathlib import Path

DB = Path(__file__).parent / "polymarket.db"


def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS market_snapshots (
        id          INTEGER PRIMARY KEY,
        condition_id TEXT NOT NULL,
        title       TEXT,
        yes_price   REAL,
        captured_at INTEGER NOT NULL  -- unix timestamp
    );

    CREATE TABLE IF NOT EXISTS positions (
        id           INTEGER PRIMARY KEY,
        wallet       TEXT NOT NULL,
        condition_id TEXT NOT NULL,
        outcome      TEXT,
        avg_price    REAL,
        size         REAL,
        current_value REAL,
        realized_pnl  REAL,
        cur_price    REAL,
        total_bought REAL,
        captured_at  INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS trades (
        id           INTEGER PRIMARY KEY,
        wallet       TEXT NOT NULL,
        condition_id TEXT NOT NULL,
        tx_hash      TEXT UNIQUE,
        side         TEXT,
        outcome      TEXT,
        price        REAL,
        size         REAL,
        ts           INTEGER,
        title        TEXT
    );

    CREATE TABLE IF NOT EXISTS wallets (
        wallet       TEXT PRIMARY KEY,
        name         TEXT,
        classification TEXT,
        win_rate     REAL,
        n_markets    INTEGER,
        total_pnl    REAL,
        updated_at   INTEGER
    );

    CREATE TABLE IF NOT EXISTS watched_markets (
        condition_id TEXT PRIMARY KEY,
        title        TEXT,
        volume       REAL,
        yes_price    REAL,
        first_seen   INTEGER NOT NULL,
        last_seen    INTEGER NOT NULL,
        expires_at   INTEGER NOT NULL   -- last_seen + 43200 (12h)
    );

    CREATE INDEX IF NOT EXISTS idx_snap_cid    ON market_snapshots(condition_id, captured_at);
    CREATE INDEX IF NOT EXISTS idx_pos_wallet  ON positions(wallet, captured_at);
    CREATE INDEX IF NOT EXISTS idx_pos_cid     ON positions(condition_id, captured_at);
    CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet, ts);
    CREATE INDEX IF NOT EXISTS idx_trades_cid   ON trades(condition_id, ts);
    CREATE INDEX IF NOT EXISTS idx_watch_exp   ON watched_markets(expires_at);
    """)
    conn.commit()
    conn.close()


def insert_snapshot(condition_id: str, title: str, yes_price: float):
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO market_snapshots(condition_id, title, yes_price, captured_at) VALUES (?,?,?,?)",
            (condition_id, title, yes_price, now)
        )


def insert_positions(condition_id: str, positions: list):
    now = int(time.time())
    rows = [(
        p.get("proxyWallet") or p.get("user", ""),
        condition_id,
        p.get("outcome"),
        p.get("avgPrice"),
        p.get("size"),
        p.get("currentValue"),
        p.get("realizedPnl"),
        p.get("currPrice") or p.get("curPrice"),
        p.get("totalBought"),
        now,
    ) for p in positions]
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO positions
               (wallet,condition_id,outcome,avg_price,size,current_value,realized_pnl,cur_price,total_bought,captured_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            rows
        )


def insert_trades(wallet: str, trades: list):
    rows = [(
        wallet,
        t.get("conditionId"),
        t.get("transactionHash"),
        t.get("side"),
        t.get("outcome"),
        t.get("price"),
        t.get("size"),
        t.get("timestamp"),
        t.get("title"),
    ) for t in trades]
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO trades
               (wallet,condition_id,tx_hash,side,outcome,price,size,ts,title)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            rows
        )


WATCH_TTL = 12 * 3600  # 12시간


def upsert_watched(condition_id: str, title: str, volume: float, yes_price: float):
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO watched_markets(condition_id,title,volume,yes_price,first_seen,last_seen,expires_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(condition_id) DO UPDATE SET
                 title=excluded.title, volume=excluded.volume, yes_price=excluded.yes_price,
                 last_seen=excluded.last_seen, expires_at=excluded.expires_at""",
            (condition_id, title, volume, yes_price, now, now, now + WATCH_TTL)
        )


def get_active_watched():
    now = int(time.time())
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM watched_markets WHERE expires_at > ?", (now,)
        ).fetchall()


def expire_watched():
    now = int(time.time())
    with get_conn() as conn:
        n = conn.execute("DELETE FROM watched_markets WHERE expires_at <= ?", (now,)).rowcount
    return n


def upsert_wallet(wallet: str, data: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO wallets(wallet,name,classification,win_rate,n_markets,total_pnl,updated_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(wallet) DO UPDATE SET
                 name=excluded.name, classification=excluded.classification,
                 win_rate=excluded.win_rate, n_markets=excluded.n_markets,
                 total_pnl=excluded.total_pnl, updated_at=excluded.updated_at""",
            (wallet, data.get("name"), data.get("classification"),
             data.get("win_rate"), data.get("n_markets"),
             data.get("total_pnl"), int(time.time()))
        )


if __name__ == "__main__":
    init_db()
    print(f"DB 초기화 완료: {DB}")
    conn = get_conn()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for t in tables:
        print(f"  {t['name']}")
    conn.close()
