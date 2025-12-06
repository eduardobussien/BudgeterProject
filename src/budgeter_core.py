# src/budgeter_core.py

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional


@dataclass
class Transaction:
    amount: float
    t_type: str         # "income" or "expense"
    category: str
    note: str = ""
    date: date = field(default_factory=date.today)

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("amount must be > 0")
        if self.t_type not in ("income", "expense"):
            raise ValueError("t_type must be 'income' or 'expense'")

    @property
    def signed_amount(self) -> float:
        return self.amount if self.t_type == "income" else -self.amount


@dataclass
class Goal:
    name: str
    current_amount: float
    target_amount: float

    def remaining(self, balance: float) -> float:
        return max(0.0, self.target_amount - balance)


@dataclass
class Account:
    name: str
    goal: Optional[Goal] = None
    transactions: List[Transaction] = field(default_factory=list)

    def add_transaction(self, txn: Transaction) -> None:
        self.transactions.append(txn)

    def new_transaction(self, amount: float, t_type: str,
                        category: str, note: str = "") -> Transaction:
        txn = Transaction(amount, t_type, category, note)
        self.add_transaction(txn)
        return txn

    def balance(self) -> float:
        return sum(t.signed_amount for t in self.transactions)

    def recent_transactions(self, n: int = 10) -> List[Transaction]:
        return self.transactions[-n:]

    def estimate_eta_weeks(self, lookback_days: int = 56) -> str:
        """
        Rough ETA based on average net gain over the last `lookback_days`.
        Returns a human-readable string like '~18 weeks (~4.5 months)'.
        """
        if not self.goal:
            return "No goal set"

        bal = self.balance()
        remaining = self.goal.remaining(bal)
        if remaining <= 0:
            return "Goal reached 🎉"

        if not self.transactions:
            return "Add more data"

        cutoff = date.today() - timedelta(days=lookback_days)
        recent = [t for t in self.transactions if t.date >= cutoff]
        if not recent:
            return "Add more recent data"

        net = sum(t.signed_amount for t in recent)
        avg_per_week = net / max(1, lookback_days / 7)

        if avg_per_week <= 0:
            return "No positive trend"

        weeks = remaining / avg_per_week
        months = weeks / 4
        return f"~{weeks:.0f} weeks (~{months:.1f} months)"