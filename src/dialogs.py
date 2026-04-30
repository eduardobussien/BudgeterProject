from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from src.budgeter_core import Goal


class GoalEditDialog(QDialog):
    def __init__(self, goal: Goal | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Goal" if goal else "Add Goal")
        self.setModal(True)

        self.deleted = False
        self._goal = goal

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Goal name")

        self.target_spin = QDoubleSpinBox()
        self.target_spin.setPrefix("$ ")
        self.target_spin.setMaximum(1_000_000_000)
        self.target_spin.setDecimals(2)

        self.current_spin = QDoubleSpinBox()
        self.current_spin.setPrefix("$ ")
        self.current_spin.setMaximum(1_000_000_000)
        self.current_spin.setDecimals(2)

        layout.addWidget(QLabel("Name"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Target amount"))
        layout.addWidget(self.target_spin)
        layout.addWidget(QLabel("Current amount"))
        layout.addWidget(self.current_spin)

        buttons = QDialogButtonBox()
        self.save_button = buttons.addButton(
            "Save", QDialogButtonBox.ButtonRole.AcceptRole
        )

        if goal is not None:
            self.delete_button = buttons.addButton(
                "Delete", QDialogButtonBox.ButtonRole.DestructiveRole
            )
            self.delete_button.setStyleSheet("color: #ff6b81;")
            self.delete_button.clicked.connect(self._on_delete)

        self.save_button.clicked.connect(self._on_save)
        layout.addWidget(buttons)

        if goal:
            self.name_edit.setText(goal.name)
            self.target_spin.setValue(goal.target_amount)
            self.current_spin.setValue(goal.current_amount)

    def _on_save(self):
        self.deleted = False
        self.accept()

    def _on_delete(self):
        self.deleted = True
        self.accept()

    def get_goal_data(self) -> Goal:
        name = self.name_edit.text() or "Untitled Goal"
        target = float(self.target_spin.value())
        current = float(self.current_spin.value())

        if self._goal is None:
            return Goal(name=name, current_amount=current, target_amount=target)
        self._goal.name = name
        self._goal.current_amount = current
        self._goal.target_amount = target
        return self._goal


class BillEditDialog(QDialog):
    def __init__(self, bill: dict | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Bill" if bill else "Add Bill")
        self.setModal(True)

        self.deleted = False
        self._bill = bill

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Bill name (e.g., Rent)")

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setPrefix("$ ")
        self.amount_spin.setMaximum(1_000_000_000)
        self.amount_spin.setDecimals(2)

        layout.addWidget(QLabel("Title"))
        layout.addWidget(self.title_edit)
        layout.addWidget(QLabel("Amount"))
        layout.addWidget(self.amount_spin)

        buttons = QDialogButtonBox()
        self.save_button = buttons.addButton(
            "Save", QDialogButtonBox.ButtonRole.AcceptRole
        )

        if bill is not None:
            self.delete_button = buttons.addButton(
                "Delete", QDialogButtonBox.ButtonRole.DestructiveRole
            )
            self.delete_button.setStyleSheet("color: #ff6b81;")
            self.delete_button.clicked.connect(self._on_delete)

        self.save_button.clicked.connect(self._on_save)
        layout.addWidget(buttons)

        if bill is not None:
            self.title_edit.setText(bill.get("title", ""))
            self.amount_spin.setValue(float(bill.get("amount", 0.0)))

    def _on_save(self):
        self.deleted = False
        self.accept()

    def _on_delete(self):
        self.deleted = True
        self.accept()

    def get_bill(self) -> dict:
        title = self.title_edit.text().strip() or "Untitled bill"
        amount = float(self.amount_spin.value())

        if self._bill is None:
            return {"title": title, "amount": amount}
        self._bill["title"] = title
        self._bill["amount"] = amount
        return self._bill


class TransactionDialog(QDialog):
    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Add {kind.capitalize()}")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.kind = kind  # "income" or "expense"

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setPrefix("$ ")
        self.amount_spin.setMaximum(1_000_000_000)
        self.amount_spin.setDecimals(2)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Personal", "School", "Food", "Bills", "Other"])

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Optional note / description")

        layout.addWidget(QLabel("Amount"))
        layout.addWidget(self.amount_spin)
        layout.addWidget(QLabel("Category"))
        layout.addWidget(self.category_combo)
        layout.addWidget(QLabel("Note"))
        layout.addWidget(self.note_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_transaction(self) -> dict:
        return {
            "kind": self.kind,
            "amount": float(self.amount_spin.value()),
            "category": self.category_combo.currentText(),
            "note": self.note_edit.text().strip(),
            "timestamp": datetime.now().isoformat(),
        }
