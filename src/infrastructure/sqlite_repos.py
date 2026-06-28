import sqlite3

from src.domain.wallet import WalletProfile


class SQLiteMarketRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS watched_markets (
                id       TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                yes_price REAL NOT NULL DEFAULT 0
            )
        """)
        self._conn.commit()

    def get_watched(self) -> list[dict]:
        cur = self._conn.execute("SELECT id, question, yes_price FROM watched_markets")
        return [{"id": r[0], "question": r[1], "yes_price": r[2]} for r in cur.fetchall()]

    def add(self, market: dict) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO watched_markets (id, question, yes_price) VALUES (?,?,?)",
            (market["id"], market.get("question", ""), market.get("yes_price", 0.0)),
        )
        self._conn.commit()

    def remove(self, market_id: str) -> None:
        self._conn.execute("DELETE FROM watched_markets WHERE id=?", (market_id,))
        self._conn.commit()


class SQLiteWalletRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                address      TEXT PRIMARY KEY,
                win_rate     REAL,
                n_markets    INTEGER,
                total_pnl    REAL,
                age_days     INTEGER,
                bias_up      REAL,
                total_trades INTEGER
            )
        """)
        self._conn.commit()

    def get(self, address: str) -> WalletProfile | None:
        cur = self._conn.execute(
            "SELECT win_rate,n_markets,total_pnl,age_days,bias_up,total_trades"
            " FROM wallets WHERE address=?",
            (address,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return WalletProfile(
            win_rate=row[0], n_markets=row[1], total_pnl=row[2],
            age_days=row[3], bias_up=row[4], total_trades=row[5],
        )

    def save(self, wallet: WalletProfile, address: str) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO wallets
               (address,win_rate,n_markets,total_pnl,age_days,bias_up,total_trades)
               VALUES (?,?,?,?,?,?,?)""",
            (address, wallet.win_rate, wallet.n_markets, wallet.total_pnl,
             wallet.age_days, wallet.bias_up, wallet.total_trades),
        )
        self._conn.commit()
