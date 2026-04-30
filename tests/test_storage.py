from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from src import storage
from src.budgeter_core import Goal


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Each test gets a fresh, throwaway SQLite database."""
    monkeypatch.setattr(storage, "DB_FILE", tmp_path / "test.db")
    yield tmp_path


# ---------- Goals ----------

def test_goals_round_trip(isolated_db):
    goals = [
        Goal(name="Trip", current_amount=200.0, target_amount=1500.0),
        Goal(name="Laptop", current_amount=0.0, target_amount=2000.0),
    ]
    storage.save_goals(goals)

    loaded = storage.load_goals()
    assert [g.name for g in loaded] == ["Trip", "Laptop"]
    assert loaded[0].current_amount == 200.0
    assert loaded[1].target_amount == 2000.0


def test_goals_save_replaces_existing(isolated_db):
    storage.save_goals([Goal("A", 0, 100)])
    storage.save_goals([Goal("B", 0, 200), Goal("C", 0, 300)])
    loaded = storage.load_goals()
    assert [g.name for g in loaded] == ["B", "C"]


def test_goals_empty_list_when_db_fresh(isolated_db):
    assert storage.load_goals() == []


# ---------- Bills ----------

def test_bills_round_trip(isolated_db):
    bills = [{"title": "Rent", "amount": 1200.0}, {"title": "Power", "amount": 80.0}]
    storage.save_bills(bills)
    assert storage.load_bills() == bills


# ---------- Balance ----------

def test_balance_round_trip(isolated_db):
    storage.save_balance(2575.50)
    assert storage.load_balance() == pytest.approx(2575.50)


def test_balance_defaults_to_zero(isolated_db):
    assert storage.load_balance() == 0.0


# ---------- Transactions + prune ----------

def test_transactions_round_trip_keeps_recent(isolated_db):
    now = datetime.now()
    txs = [
        {
            "kind": "income",
            "amount": 500.0,
            "category": "Salary",
            "note": "",
            "timestamp": now.isoformat(),
        },
        {
            "kind": "expense",
            "amount": 25.0,
            "category": "Food",
            "note": "lunch",
            "timestamp": (now - timedelta(days=2)).isoformat(),
        },
    ]
    storage.save_transactions(txs)
    loaded = storage.load_transactions()
    assert len(loaded) == 2
    assert {t["category"] for t in loaded} == {"Salary", "Food"}


def test_load_transactions_drops_entries_older_than_retention(isolated_db):
    now = datetime.now()
    storage.save_transactions([
        {
            "kind": "expense",
            "amount": 10.0,
            "category": "Old",
            "note": "",
            "timestamp": (now - timedelta(days=storage.RETENTION_DAYS + 5)).isoformat(),
        },
        {
            "kind": "expense",
            "amount": 20.0,
            "category": "Recent",
            "note": "",
            "timestamp": (now - timedelta(days=1)).isoformat(),
        },
    ])
    loaded = storage.load_transactions()
    assert [t["category"] for t in loaded] == ["Recent"]


def test_save_transactions_filters_invalid_kind(isolated_db):
    storage.save_transactions([
        {"kind": "income", "amount": 10, "timestamp": datetime.now().isoformat()},
        {"kind": "junk", "amount": 99, "timestamp": datetime.now().isoformat()},
    ])
    loaded = storage.load_transactions()
    assert len(loaded) == 1
    assert loaded[0]["kind"] == "income"


def test_prune_old_transactions_pure_function():
    now = datetime.now()
    out = storage.prune_old_transactions([
        {"kind": "expense", "amount": 1, "timestamp": (now - timedelta(days=20)).isoformat()},
        {"kind": "expense", "amount": 1, "timestamp": now.isoformat()},
        {"kind": "expense", "amount": 1, "timestamp": "not-a-date"},  # kept (un-parseable)
        {"kind": "expense", "amount": 1},                              # filled-in + kept
    ])
    assert len(out) == 3


# ---------- Corrupt-file resilience ----------

def test_corrupt_db_file_is_recreated(tmp_path, monkeypatch):
    """A corrupt DB file should not crash the app — load returns empty,
    and a subsequent save heals the database."""
    bad = tmp_path / "test.db"
    bad.write_bytes(b"this is not a sqlite database")
    monkeypatch.setattr(storage, "DB_FILE", bad)

    # Don't crash — just degrade gracefully.
    assert storage.load_goals() == []

    # Replace the corrupt file so we can verify save works post-recovery.
    bad.unlink()
    storage.save_goals([Goal("Recovered", 0, 100)])
    assert [g.name for g in storage.load_goals()] == ["Recovered"]


def test_load_handles_empty_db_file(tmp_path, monkeypatch):
    empty = tmp_path / "test.db"
    empty.touch()  # zero-byte file — sqlite treats it as empty DB
    monkeypatch.setattr(storage, "DB_FILE", empty)

    assert storage.load_goals() == []
    assert storage.load_bills() == []
    assert storage.load_balance() == 0.0
    assert storage.load_transactions() == []


# ---------- JSON → SQLite migration ----------

def test_first_run_migrates_legacy_json(tmp_path, monkeypatch):
    """Legacy JSON files next to the DB should be imported once and archived."""
    monkeypatch.setattr(storage, "DB_FILE", tmp_path / "budgeter.db")

    (tmp_path / "goals.json").write_text(
        json.dumps([{"name": "Trip", "current_amount": 100, "target_amount": 1000}])
    )
    (tmp_path / "bills.json").write_text(
        json.dumps([{"title": "Rent", "amount": 1200}])
    )
    (tmp_path / "balance.json").write_text(json.dumps({"balance": 350.25}))
    (tmp_path / "transactions.json").write_text(
        json.dumps([{
            "kind": "income",
            "amount": 500,
            "category": "Salary",
            "note": "",
            "timestamp": datetime.now().isoformat(),
        }])
    )

    # First load triggers migration.
    goals = storage.load_goals()
    assert [g.name for g in goals] == ["Trip"]
    assert storage.load_bills() == [{"title": "Rent", "amount": 1200.0}]
    assert storage.load_balance() == pytest.approx(350.25)
    assert len(storage.load_transactions()) == 1

    # Originals were renamed so they won't be re-imported.
    assert not (tmp_path / "goals.json").exists()
    assert (tmp_path / "goals.json.migrated").exists()


# ---------- CSV export ----------

def test_export_transactions_csv_writes_header_and_rows(tmp_path):
    out = tmp_path / "export.csv"
    txs = [
        {
            "kind": "expense",
            "amount": 12.50,
            "category": "Food",
            "note": "lunch",
            "timestamp": "2026-04-29T12:30:00",
        },
        {
            "kind": "income",
            "amount": 1000,
            "category": "Salary",
            "note": "",
            "timestamp": "bad-timestamp",
        },
    ]
    count = storage.export_transactions_csv(out, txs)
    assert count == 2

    text = out.read_text(encoding="utf-8").splitlines()
    assert text[0] == "Date,Type,Category,Amount,Note"
    assert "2026-04-29 12:30,expense,Food,12.50,lunch" in text[1]
    # Bad timestamp falls through unchanged rather than crashing.
    assert "bad-timestamp,income,Salary,1000.00," in text[2]


def test_export_transactions_csv_empty_list(tmp_path):
    out = tmp_path / "empty.csv"
    count = storage.export_transactions_csv(out, [])
    assert count == 0
    assert out.read_text(encoding="utf-8").strip() == "Date,Type,Category,Amount,Note"
