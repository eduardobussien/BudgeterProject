"""Persistence layer.

Public API (load_goals / save_goals / load_bills / save_bills /
load_balance / save_balance / load_transactions / save_transactions /
prune_old_transactions / export_transactions_csv) is stable; the
implementation moved from four JSON files to one SQLite database.

On first run, if a legacy `goals.json` / `bills.json` / `balance.json` /
`transactions.json` is found next to the new database, its contents are
imported into the DB and the JSON file is renamed `*.json.migrated` so it
won't be re-imported on subsequent launches.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from src.budgeter_core import Goal

logger = logging.getLogger("budgeter")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

RETENTION_DAYS = 7


def get_resource_base() -> Path:
    """Location of bundled resources. Frozen → sys._MEIPASS, dev → project root."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_user_data_dir() -> Path:
    """Where user data is stored. EXE → %APPDATA%/BudgeterProject, dev → ./data."""
    if getattr(sys, "frozen", False):
        appdata = os.getenv("APPDATA", str(Path.home()))
        return Path(appdata) / "BudgeterProject"
    return get_resource_base() / "data"


RESOURCE_BASE = get_resource_base()
STATIC_DATA_DIR = RESOURCE_BASE / "data"

USER_DATA_DIR = get_user_data_dir()
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_FILE = USER_DATA_DIR / "budgeter.db"

GITHUB_LOGO_FILE = STATIC_DATA_DIR / "img" / "githublogo.png"
DOLLAR_LOGO_FILE = STATIC_DATA_DIR / "img" / "dollar_logo.png"


# ---------- DB plumbing ----------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    current_amount  REAL NOT NULL DEFAULT 0,
    target_amount   REAL NOT NULL DEFAULT 0,
    position        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bills (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT NOT NULL,
    amount    REAL NOT NULL DEFAULT 0,
    position  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT NOT NULL CHECK(kind IN ('income','expense')),
    amount     REAL NOT NULL,
    category   TEXT NOT NULL DEFAULT '',
    note       TEXT NOT NULL DEFAULT '',
    timestamp  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def _db():
    """Open a SQLite connection, init schema, run one-shot migration, commit/close."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    is_new = not DB_FILE.exists() or DB_FILE.stat().st_size == 0
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA)
        if is_new:
            _migrate_from_json(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_from_json(conn: sqlite3.Connection) -> None:
    """One-shot import of legacy JSON files sitting next to the DB."""
    base = DB_FILE.parent
    sources = {
        "goals":        base / "goals.json",
        "bills":        base / "bills.json",
        "balance":      base / "balance.json",
        "transactions": base / "transactions.json",
    }
    found = {k: p for k, p in sources.items() if p.exists()}
    if not found:
        return

    logger.info("Migrating legacy JSON data into SQLite: %s", list(found))

    try:
        if (p := found.get("goals")):
            data = _read_json(p) or []
            conn.executemany(
                "INSERT INTO goals(name,current_amount,target_amount,position)"
                " VALUES (?,?,?,?)",
                [
                    (
                        item.get("name", "Untitled"),
                        float(item.get("current_amount", 0.0)),
                        float(item.get("target_amount", 0.0)),
                        i,
                    )
                    for i, item in enumerate(data)
                ],
            )

        if (p := found.get("bills")):
            data = _read_json(p) or []
            conn.executemany(
                "INSERT INTO bills(title,amount,position) VALUES (?,?,?)",
                [
                    (
                        item.get("title", "Untitled bill"),
                        float(item.get("amount", 0.0)),
                        i,
                    )
                    for i, item in enumerate(data)
                ],
            )

        if (p := found.get("transactions")):
            data = _read_json(p) or []
            conn.executemany(
                "INSERT INTO transactions(kind,amount,category,note,timestamp)"
                " VALUES (?,?,?,?,?)",
                [
                    (
                        item.get("kind", "expense"),
                        float(item.get("amount", 0.0)),
                        item.get("category", ""),
                        item.get("note", ""),
                        item.get("timestamp") or datetime.now().isoformat(),
                    )
                    for item in data
                    if item.get("kind") in ("income", "expense")
                ],
            )

        if (p := found.get("balance")):
            data = _read_json(p)
            value = (
                float(data.get("balance", 0.0))
                if isinstance(data, dict)
                else float(data or 0.0)
            )
            conn.execute(
                "INSERT OR REPLACE INTO app_state(key,value) VALUES('balance', ?)",
                (str(value),),
            )
    except (sqlite3.Error, OSError, ValueError, TypeError) as e:
        logger.warning("JSON → SQLite migration failed: %s", e)
        return

    for p in found.values():
        try:
            shutil.move(str(p), str(p.with_suffix(p.suffix + ".migrated")))
        except OSError as e:
            logger.warning("Could not archive %s: %s", p, e)


def _read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        logger.warning("Failed to read %s: %s", path, e)
        return None


# ---------- Goals ----------

def load_goals() -> list[Goal]:
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT name, current_amount, target_amount FROM goals"
                " ORDER BY position, id"
            ).fetchall()
        return [
            Goal(
                name=r["name"],
                current_amount=float(r["current_amount"]),
                target_amount=float(r["target_amount"]),
            )
            for r in rows
        ]
    except sqlite3.Error as e:
        logger.warning("Failed to load goals: %s", e)
        return []


def save_goals(goals: list[Goal]) -> None:
    try:
        with _db() as conn:
            conn.execute("DELETE FROM goals")
            conn.executemany(
                "INSERT INTO goals(name,current_amount,target_amount,position)"
                " VALUES (?,?,?,?)",
                [(g.name, g.current_amount, g.target_amount, i) for i, g in enumerate(goals)],
            )
    except sqlite3.Error as e:
        logger.warning("Failed to save goals: %s", e)


# ---------- Bills ----------

def load_bills() -> list[dict]:
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT title, amount FROM bills ORDER BY position, id"
            ).fetchall()
        return [{"title": r["title"], "amount": float(r["amount"])} for r in rows]
    except sqlite3.Error as e:
        logger.warning("Failed to load bills: %s", e)
        return []


def save_bills(bills: list[dict]) -> None:
    try:
        with _db() as conn:
            conn.execute("DELETE FROM bills")
            conn.executemany(
                "INSERT INTO bills(title,amount,position) VALUES (?,?,?)",
                [
                    (b["title"], float(b["amount"]), i)
                    for i, b in enumerate(bills)
                ],
            )
    except sqlite3.Error as e:
        logger.warning("Failed to save bills: %s", e)


# ---------- Transactions ----------

def prune_old_transactions(transactions: list[dict]) -> list[dict]:
    """Keep only transactions from the last RETENTION_DAYS days."""
    now = datetime.now()
    cutoff = now - timedelta(days=RETENTION_DAYS)
    pruned: list[dict] = []

    for tx in transactions:
        ts = tx.get("timestamp")
        if not ts:
            tx["timestamp"] = now.isoformat()
            pruned.append(tx)
            continue
        try:
            dt = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            pruned.append(tx)
            continue
        if dt >= cutoff:
            pruned.append(tx)

    return pruned


def load_transactions() -> list[dict]:
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT kind, amount, category, note, timestamp FROM transactions"
                " ORDER BY id"
            ).fetchall()
        all_tx = [
            {
                "kind": r["kind"],
                "amount": float(r["amount"]),
                "category": r["category"],
                "note": r["note"],
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]
        kept = prune_old_transactions(all_tx)
        if len(kept) != len(all_tx):
            save_transactions(kept)
        return kept
    except sqlite3.Error as e:
        logger.warning("Failed to load transactions: %s", e)
        return []


def save_transactions(transactions: list[dict]) -> None:
    try:
        with _db() as conn:
            conn.execute("DELETE FROM transactions")
            conn.executemany(
                "INSERT INTO transactions(kind,amount,category,note,timestamp)"
                " VALUES (?,?,?,?,?)",
                [
                    (
                        t.get("kind", "expense"),
                        float(t.get("amount", 0.0)),
                        t.get("category", ""),
                        t.get("note", ""),
                        t.get("timestamp") or datetime.now().isoformat(),
                    )
                    for t in transactions
                    if t.get("kind") in ("income", "expense")
                ],
            )
    except sqlite3.Error as e:
        logger.warning("Failed to save transactions: %s", e)


# ---------- Balance ----------

def load_balance() -> float:
    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT value FROM app_state WHERE key='balance'"
            ).fetchone()
        return float(row["value"]) if row else 0.0
    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.warning("Failed to load balance: %s", e)
        return 0.0


def save_balance(balance: float) -> None:
    try:
        with _db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_state(key,value) VALUES('balance', ?)",
                (str(float(balance)),),
            )
    except sqlite3.Error as e:
        logger.warning("Failed to save balance: %s", e)


# ---------- CSV export ----------

def export_transactions_csv(path: Path | str, transactions: list[dict]) -> int:
    """Write transactions to a CSV file. Returns the number of rows written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Type", "Category", "Amount", "Note"])
        rows_written = 0
        for tx in transactions:
            ts = tx.get("timestamp", "")
            try:
                date_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_str = ts
            writer.writerow([
                date_str,
                tx.get("kind", ""),
                tx.get("category", ""),
                f"{float(tx.get('amount', 0.0)):.2f}",
                tx.get("note", ""),
            ])
            rows_written += 1
    return rows_written
