# tests/test_budgeter_core.py

import unittest
from datetime import date, timedelta

from src.budgeter_core import Account, Goal, Transaction


class TestTransaction(unittest.TestCase):
    def test_signed_income_and_expense(self):
        t1 = Transaction(100, "income", "Salary")
        t2 = Transaction(50, "expense", "Food")
        self.assertEqual(t1.signed_amount, 100)
        self.assertEqual(t2.signed_amount, -50)

    def test_invalid_amount_raises(self):
        with self.assertRaises(ValueError):
            Transaction(0, "income", "X")

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            Transaction(10, "other", "X")


class TestGoal(unittest.TestCase):
    def test_remaining_clamps_at_zero(self):
        g = Goal("Trip", current_amount=0, target_amount=1000)
        self.assertEqual(g.remaining(1500), 0.0)
        self.assertEqual(g.remaining(400), 600.0)


class TestAccount(unittest.TestCase):
    def setUp(self):
        self.goal = Goal("Trip to Bali", current_amount=0, target_amount=3000)
        self.acc = Account("Travel", self.goal)

    def test_balance_and_recent(self):
        self.acc.new_transaction(1000, "income", "Salary")
        self.acc.new_transaction(200, "expense", "Food")
        self.assertAlmostEqual(self.acc.balance(), 800)
        self.assertEqual(len(self.acc.recent_transactions(1)), 1)

    def test_eta_reached(self):
        self.acc.new_transaction(3500, "income", "Salary")
        eta = self.acc.estimate_eta_weeks()
        self.assertIn("Goal reached", eta)

    def test_eta_no_goal(self):
        acc2 = Account("No goal")
        self.assertEqual(acc2.estimate_eta_weeks(), "No goal set")

    def test_eta_no_positive_trend(self):
        old = date.today() - timedelta(days=10)
        self.acc.add_transaction(Transaction(100, "expense", "Food", date=old))
        self.assertEqual(self.acc.estimate_eta_weeks(), "No positive trend")


if __name__ == "__main__":
    unittest.main()
