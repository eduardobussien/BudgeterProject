# tests/test_budgeter_core.py

import unittest
from datetime import date, timedelta

from src.budgeter_core import Transaction, Goal, Account


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


class TestAccount(unittest.TestCase):
    def setUp(self):
        self.goal = Goal("Trip to Bali", 3000)
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


if __name__ == "__main__":
    unittest.main()