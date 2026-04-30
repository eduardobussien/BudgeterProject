from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.budgeter_core import Goal
from src.dialogs import BillEditDialog, GoalEditDialog, TransactionDialog
from src.storage import (
    DOLLAR_LOGO_FILE,
    GITHUB_LOGO_FILE,
    export_transactions_csv,
    load_balance,
    load_bills,
    load_goals,
    load_transactions,
    prune_old_transactions,
    save_balance,
    save_bills,
    save_goals,
    save_transactions,
)
from src.theme import ACCENT, BG_MAIN, FG_TEXT
from src.widgets import (
    BillRowWidget,
    CardWidget,
    CircularProgressBar,
    GoalRowWidget,
    SpendingTrendsWidget,
)

logger = logging.getLogger("budgeter")


class BudgeterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("BUDGETER")
        self.resize(1200, 700)

        if DOLLAR_LOGO_FILE.exists():
            self.setWindowIcon(QIcon(str(DOLLAR_LOGO_FILE)))

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {BG_MAIN};
            }}
            QLabel {{
                color: {FG_TEXT};
            }}
        """)

        central = QWidget()
        self.setCentralWidget(central)

        grid = QGridLayout()
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        central.setLayout(grid)

        self.goals: list[Goal] = load_goals()
        self.goal_rows: list[GoalRowWidget] = []

        self.balance: float = load_balance()
        self.transactions: list[dict] = load_transactions()

        grid.setRowStretch(0, 6)
        grid.setRowStretch(1, 10)
        grid.setRowStretch(2, 8)

        grid.setColumnStretch(0, 8)
        grid.setColumnStretch(1, 12)
        grid.setColumnStretch(2, 5)

        self._build_logo_title(grid)
        self._build_menu(grid)
        self._build_main_goal_card(grid)
        self._build_goals_summary(grid)
        self._build_spending_trend(grid)
        self._build_insights(grid)
        self._build_bills_card(grid)
        self._build_transactions_card(grid)

        self._refresh_transactions_table()
        self._update_spending_trends()
        self._update_insights()

    # ---------- Layout sections ----------

    def _build_logo_title(self, grid: QGridLayout):
        top_left = QWidget()
        grid.addWidget(top_left, 0, 0)
        tl_layout = QHBoxLayout(top_left)
        tl_layout.setContentsMargins(16, 12, 16, 12)
        tl_layout.setSpacing(10)

        logo_label = QLabel()
        pix = QPixmap(str(DOLLAR_LOGO_FILE))
        if not pix.isNull():
            pix = pix.scaled(
                120, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(pix)
            logo_label.setScaledContents(False)
            tl_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        else:
            logo_circle = QFrame()
            logo_circle.setFixedSize(32, 32)
            logo_circle.setStyleSheet(f"""
                QFrame {{
                    background-color: {ACCENT};
                    border-radius: 16px;
                }}
            """)
            tl_layout.addWidget(logo_circle, alignment=Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 30, 20, 0)
        title = QLabel("Budgeter")
        title.setStyleSheet("font-size: 40px; font-weight: 1000; color: #b4ffd8;")
        subtitle = QLabel("Track • Plan • Grow")
        subtitle.setStyleSheet("font-size: 11px; color: #b4ffd8;")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        tl_layout.addLayout(text_col)
        tl_layout.addStretch()

    def _build_menu(self, grid: QGridLayout):
        top_right = QWidget()
        grid.addWidget(top_right, 0, 2)

        tr_layout = QVBoxLayout(top_right)
        tr_layout.setContentsMargins(4, 4, 4, 4)
        tr_layout.setSpacing(4)

        menu_button = QToolButton()
        menu_button.setText("MENU")
        menu_button.setStyleSheet(f"""
            QToolButton {{
                color: #e9fff3;
                padding: 8px 26px;
                border-radius: 18px;
                background-color: #063525;
                border: 1px solid {ACCENT};
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 1px;
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
            QToolButton:hover {{
                background-color: #0a4530;
            }}
        """)

        menu = QMenu(menu_button)
        menu.addAction("Profile (WIP)", self._dummy_action)
        menu.addAction("Appearance (WIP)", self._dummy_action)
        menu.addSeparator()
        menu.addAction("Export transactions (CSV)…", self._export_transactions_csv)
        menu.addSeparator()
        menu.addAction("About", self._show_about)
        menu.addSeparator()
        menu.addAction("Settings", self._open_settings_dialog)

        menu_button.setMenu(menu)
        menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        tr_layout.addStretch()
        tr_layout.addWidget(menu_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        tr_layout.addStretch()

    def _build_main_goal_card(self, grid: QGridLayout):
        main_goal = CardWidget()
        grid.addWidget(main_goal, 0, 1, 2, 1)

        mg_layout = QVBoxLayout(main_goal)
        mg_layout.setContentsMargins(18, 16, 18, 16)
        mg_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        mg_title = QLabel("Main Goal:")
        mg_title.setStyleSheet("font-size: 16px; font-weight: 700;")

        self.main_goal_name = QLabel("(no main goal)")
        self.main_goal_name.setStyleSheet(f"""
            font-size: 30px;
            font-weight: 700;
            color: {ACCENT};
        """)

        header_layout.addWidget(mg_title)
        header_layout.addWidget(self.main_goal_name)
        header_layout.addStretch()
        mg_layout.addLayout(header_layout)

        mg_sub = QLabel("Overview of your primary savings goal.")
        mg_sub.setStyleSheet("font-size: 11px; color: #a3ffcf;")
        mg_layout.addWidget(mg_sub)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(32)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        left_col.addStretch()

        self.main_goal_progress = CircularProgressBar(
            size=230, thickness=18, max_value=100,
        )
        self.main_goal_progress.setValue(0)
        left_col.addWidget(
            self.main_goal_progress,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        left_col.addStretch()
        content_layout.addLayout(left_col, stretch=3)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        self.main_goal_amount_label = QLabel("Saved: $0.00 of $0.00")
        self.main_goal_amount_label.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.main_goal_progress_label = QLabel("You're 0% of the way there.")
        self.main_goal_progress_label.setStyleSheet(
            "font-size: 12px; color: #c8ffe6;"
        )

        right_col.addWidget(self.main_goal_amount_label)
        right_col.addWidget(self.main_goal_progress_label)
        right_col.addSpacing(18)

        balance_header_row = QHBoxLayout()
        balance_title = QLabel("Overall Balance")
        balance_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        balance_header_row.addWidget(balance_title)
        balance_header_row.addStretch()

        balance_edit_btn = QToolButton()
        balance_edit_btn.setText("Edit")
        balance_edit_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #c8ffe6;
                font-size: 11px;
            }
            QToolButton:hover {
                color: #e9fff3;
                text-decoration: underline;
            }
        """)
        balance_edit_btn.clicked.connect(self._edit_balance)
        balance_header_row.addWidget(balance_edit_btn)
        right_col.addLayout(balance_header_row)

        self.balance_label = QLabel(f"$ {self.balance:,.2f}")
        self.balance_label.setStyleSheet("""
            font-size: 36px;
            font-weight: 800;
        """)
        self.balance_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        right_col.addWidget(self.balance_label)
        right_col.addStretch()

        content_layout.addLayout(right_col, stretch=4)
        mg_layout.addLayout(content_layout)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(50)

        self.add_income_btn = QPushButton("ADD INCOME")
        self.add_income_btn.setFixedHeight(50)
        self.add_income_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT};
                border: 2px solid {ACCENT};
                border-radius: 6px;
                font-weight: 700;
                letter-spacing: 1px;
                padding-left: 24px;
                padding-right: 24px;
            }}
            QPushButton:hover {{
                background-color: #064023;
            }}
        """)
        self.add_income_btn.clicked.connect(self._add_income)

        self.add_expense_btn = QPushButton("ADD EXPENSE")
        self.add_expense_btn.setFixedHeight(50)
        self.add_expense_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT};
                border: 2px solid {ACCENT};
                border-radius: 6px;
                font-weight: 700;
                letter-spacing: 1px;
                padding-left: 24px;
                padding-right: 24px;
            }}
            QPushButton:hover {{
                background-color: #640808;
                border-color: #ff5c5c;
                color: #ffbcbc;
            }}
        """)
        self.add_expense_btn.clicked.connect(self._add_expense)

        buttons_row.addStretch()
        buttons_row.addWidget(self.add_income_btn)
        buttons_row.addSpacing(40)
        buttons_row.addWidget(self.add_expense_btn)
        buttons_row.addStretch()

        mg_layout.addSpacing(30)
        mg_layout.addLayout(buttons_row)
        mg_layout.addStretch()

    def _build_goals_summary(self, grid: QGridLayout):
        goals_card = CardWidget()
        grid.addWidget(goals_card, 1, 0)

        goals_layout = QVBoxLayout(goals_card)
        goals_layout.setContentsMargins(16, 16, 16, 16)
        goals_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_label = QLabel("Goals Summary")
        header_label.setStyleSheet(
            "font-size: 14px; font-weight: 700; margin-left: 10px;"
        )
        header_row.addWidget(header_label)
        header_row.addStretch()

        add_button = QToolButton()
        add_button.setText("+")
        add_button.setStyleSheet("""
            QToolButton {
                color: #e9fff3;
                font-size: 18px;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: #09422f;
            }
        """)
        add_button.clicked.connect(self._add_goal)
        header_row.addWidget(add_button)
        goals_layout.addLayout(header_row)

        self.goals_container = QVBoxLayout()
        self.goals_container.setSpacing(8)
        goals_layout.addLayout(self.goals_container)
        goals_layout.addStretch()

        self._rebuild_goal_rows()
        if self.goals:
            self.set_main_goal(self.goals[0])

    def _build_spending_trend(self, grid: QGridLayout):
        spending_container = QWidget()
        grid.addWidget(spending_container, 1, 2)

        spending_layout = QVBoxLayout(spending_container)
        spending_layout.setContentsMargins(4, 8, 4, 8)
        spending_layout.setSpacing(6)

        spending_title = QLabel("Spending Trend (This Week)")
        spending_title.setStyleSheet(
            "font-size: 14px; font-weight: 700; margin-left: 25px;"
        )
        spending_layout.addWidget(spending_title)

        self.spending_trends = SpendingTrendsWidget()
        spending_layout.addWidget(self.spending_trends)

    def _build_insights(self, grid: QGridLayout):
        insights_container = QWidget()
        grid.addWidget(insights_container, 2, 2)

        insights_layout = QVBoxLayout(insights_container)
        insights_layout.setContentsMargins(0, 0, 0, 0)
        insights_layout.setSpacing(0)
        insights_layout.addStretch()

        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(20)

        insights_title = QLabel("Insights & Tips")
        insights_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        inner.addWidget(insights_title, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.insight_week_spent = QLabel("")
        self.insight_week_spent.setStyleSheet("font-size: 12px; color: #c8ffe6;")
        inner.addWidget(self.insight_week_spent, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.insight_week_net = QLabel("")
        self.insight_week_net.setStyleSheet("font-size: 12px; color: #c8ffe6;")
        inner.addWidget(self.insight_week_net, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.insight_bills_total = QLabel("")
        self.insight_bills_total.setStyleSheet("font-size: 12px; color: #c8ffe6;")
        inner.addWidget(self.insight_bills_total, alignment=Qt.AlignmentFlag.AlignHCenter)

        inner.addSpacing(12)

        self.github_button = QPushButton("eduardobussien")
        self.github_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.github_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(40, 224, 122, 0.07);
                color: #b4ffd8;
                border: 1px solid {ACCENT};
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(40, 224, 122, 0.20);
            }}
        """)

        if GITHUB_LOGO_FILE.exists():
            pix = QPixmap(str(GITHUB_LOGO_FILE))
            if not pix.isNull():
                icon = QIcon(
                    pix.scaled(
                        16, 16,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.github_button.setIcon(icon)
                self.github_button.setIconSize(QSize(16, 16))

        self.github_button.clicked.connect(self._open_github)
        inner.addWidget(self.github_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        wrapper = QWidget()
        wrapper.setLayout(inner)
        insights_layout.addWidget(wrapper, alignment=Qt.AlignmentFlag.AlignHCenter)
        insights_layout.addStretch()

    def _build_bills_card(self, grid: QGridLayout):
        self.bills: list[dict] = load_bills()
        self.bill_rows: list[BillRowWidget] = []

        bills_card = CardWidget()
        grid.addWidget(bills_card, 2, 0)

        bills_layout = QVBoxLayout(bills_card)
        bills_layout.setContentsMargins(16, 10, 16, 10)
        bills_layout.setSpacing(10)

        header_row = QHBoxLayout()
        bills_header = QLabel("Upcoming Bills")
        bills_header.setStyleSheet(
            "font-size: 14px; font-weight: 700; margin-left: 5px; margin-top: 2px;"
        )
        header_row.addWidget(bills_header)
        header_row.addStretch()

        bills_add_btn = QToolButton()
        bills_add_btn.setText("Add / edit")
        bills_add_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #c8ffe6;
                font-size: 11px;
            }
            QToolButton:hover {
                color: #e9fff3;
                text-decoration: underline;
            }
        """)
        bills_add_btn.clicked.connect(self._add_bill)
        header_row.addWidget(bills_add_btn)
        bills_layout.addLayout(header_row)

        self.bills_container = QVBoxLayout()
        self.bills_container.setSpacing(6)
        bills_layout.addLayout(self.bills_container)

        self._rebuild_bill_rows()

    def _build_transactions_card(self, grid: QGridLayout):
        tx_card = CardWidget()
        grid.addWidget(tx_card, 2, 1)

        tx_layout = QVBoxLayout(tx_card)
        tx_layout.setContentsMargins(16, 10, 16, 10)
        tx_layout.setSpacing(8)

        tx_header_row = QHBoxLayout()
        tx_title = QLabel("Transactions Summary")
        tx_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        tx_header_row.addWidget(tx_title)
        tx_header_row.addStretch()
        tx_layout.addLayout(tx_header_row)

        self.tx_table = QTableWidget(0, 5)
        self.tx_table.setHorizontalHeaderLabels(
            ["Date", "Type", "Category", "Amount", "Note"]
        )
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tx_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tx_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tx_table.setShowGrid(False)
        self.tx_table.setAlternatingRowColors(True)

        header = self.tx_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.tx_table.setMinimumHeight(120)
        self.tx_table.setStyleSheet("""
            QTableWidget {
                background-color: #021f16;
                color: #e9fff3;
                border: none;
            }
            QHeaderView::section {
                background-color: #063525;
                color: #e9fff3;
                border: none;
                padding: 4px 6px;
                font-size: 11px;
            }
        """)
        tx_layout.addWidget(self.tx_table)

    # ---------- Menu / settings ----------

    def _dummy_action(self):
        QMessageBox.information(
            self,
            "Coming soon",
            "This feature isn't implemented yet — stay tuned!",
        )

    def _export_transactions_csv(self):
        if not self.transactions:
            QMessageBox.information(
                self,
                "No transactions",
                "There are no transactions to export yet.",
            )
            return

        default_name = f"budgeter_transactions_{datetime.now():%Y%m%d_%H%M}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export transactions",
            default_name,
            "CSV files (*.csv);;All files (*.*)",
        )
        if not path:
            return

        try:
            count = export_transactions_csv(path, self.transactions)
        except OSError as e:
            QMessageBox.critical(self, "Export failed", f"Could not write file:\n{e}")
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Wrote {count} transaction(s) to:\n{path}",
        )

    def _show_about(self):
        QMessageBox.information(
            self,
            "About Budgeter",
            (
                "Budgeter\n\n"
                "A simple personal finance dashboard built with Python and PyQt6.\n"
                "Track goals, upcoming bills, income and expenses, and weekly spending trends.\n\n"
                "Created by Eduardo Bussien\n"
                "GitHub: https://github.com/eduardobussien"
            ),
        )

    def _open_settings_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        info = QLabel(
            "Settings\n\n"
            "You can reset all data for this Budgeter profile.\n"
            "This will clear:\n"
            " • Goals\n"
            " • Upcoming bills\n"
            " • Balance\n"
            " • All income/expense transactions\n"
            " • Spending trends & insights\n"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        reset_btn = QPushButton("Reset all data")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a0b0b;
                color: #ffecec;
                border-radius: 6px;
                font-weight: 700;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #8c1010;
            }
        """)
        reset_btn.clicked.connect(self._confirm_and_reset)
        layout.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.exec()

    def _confirm_and_reset(self):
        reply = QMessageBox.warning(
            self,
            "Reset all data",
            "Are you sure you want to reset ALL data?\n\n"
            "This will clear goals, bills, balance, transactions and trends.\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._reset_all_data()

    def _reset_all_data(self):
        self.goals = []
        self.bills = []
        self.transactions = []
        self.balance = 0.0
        self.current_main_goal = None

        save_goals(self.goals)
        save_bills(self.bills)
        save_transactions(self.transactions)
        save_balance(self.balance)

        self.main_goal_name.setText("(no main goal)")
        self.main_goal_progress.setValue(0)
        self.main_goal_amount_label.setText("Saved: $0.00 of $0.00")
        self.main_goal_progress_label.setText("You're 0% of the way there.")

        self._rebuild_goal_rows()
        self._rebuild_bill_rows()
        self._refresh_transactions_table()
        self._update_balance_label()
        self._update_spending_trends()
        self._update_insights()

        QMessageBox.information(
            self,
            "Reset complete",
            "All Budgeter data has been reset.",
        )

    # ---------- Core UI helpers ----------

    def set_main_goal(self, goal):
        self.current_main_goal = goal

        self.main_goal_name.setText(goal.name)

        if goal.target_amount > 0:
            percent = int((goal.current_amount / goal.target_amount) * 100)
        else:
            percent = 0
        percent = max(0, min(percent, 100))

        self.main_goal_progress.setValue(percent)
        self.main_goal_amount_label.setText(
            f"Saved: ${goal.current_amount:,.2f} of ${goal.target_amount:,.2f}"
        )
        self.main_goal_progress_label.setText(
            f"You're {percent}% of the way there."
        )

    def _rebuild_bill_rows(self):
        if hasattr(self, "bills_container"):
            while self.bills_container.count():
                item = self.bills_container.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
        self.bill_rows.clear()
        self._update_insights()

        if not self.bills:
            placeholder_btn = QToolButton()
            placeholder_btn.setText("Add / edit upcoming bills")
            placeholder_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    color: #c8ffe6;
                    font-size: 12px;
                }
                QToolButton:hover {
                    color: #e9fff3;
                    text-decoration: underline;
                }
            """)
            placeholder_btn.clicked.connect(self._add_bill)

            self.bills_container.addStretch()
            self.bills_container.addWidget(
                placeholder_btn, alignment=Qt.AlignmentFlag.AlignHCenter
            )
            self.bills_container.addStretch()
            return

        colors = ["#d7263d", "#ffd447", "#2d9cff", "#ff9ff3"]

        for i, bill in enumerate(self.bills):
            color = colors[i % len(colors)]
            row = BillRowWidget(bill, color)
            row.clicked.connect(self._open_edit_bill)
            self.bills_container.addWidget(row)
            self.bill_rows.append(row)

    def _add_bill(self):
        dlg = BillEditDialog(bill=None, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and not dlg.deleted:
            new_bill = dlg.get_bill()
            self.bills.append(new_bill)
            self._rebuild_bill_rows()

    def _open_edit_bill(self, bill: dict):
        dlg = BillEditDialog(bill=bill, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.deleted:
                if bill in self.bills:
                    self.bills.remove(bill)
                self._rebuild_bill_rows()
            else:
                dlg.get_bill()
                for row in self.bill_rows:
                    if row.bill is bill:
                        row.update_from_bill()

    def _rebuild_goal_rows(self):
        if hasattr(self, "goals_container"):
            while self.goals_container.count():
                item = self.goals_container.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
        self.goal_rows.clear()

        row_colors = ["#ffd447", "#ff6b81", "#4da6ff", "#ff9ff3"]

        if not self.goals:
            label = QLabel("No goals yet. Click + to add one.")
            label.setStyleSheet("font-size: 12px; color: #c8ffe6;")
            self.goals_container.addWidget(label)
            return

        for i, goal in enumerate(self.goals):
            color = row_colors[i % len(row_colors)]
            row = GoalRowWidget(goal, color)
            row.clicked.connect(self.set_main_goal)
            row.edit_requested.connect(self._open_edit_goal)
            self.goals_container.addWidget(row)
            self.goal_rows.append(row)

    def _add_goal(self):
        dlg = GoalEditDialog(goal=None, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and not dlg.deleted:
            new_goal = dlg.get_goal_data()
            self.goals.append(new_goal)
            self._rebuild_goal_rows()
            if len(self.goals) == 1:
                self.set_main_goal(new_goal)

    def _open_edit_goal(self, goal: Goal):
        dlg = GoalEditDialog(goal=goal, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.deleted:
                if goal in self.goals:
                    self.goals.remove(goal)
                self._rebuild_goal_rows()

                if getattr(self, "current_main_goal", None) is goal:
                    self.current_main_goal = None
                    if self.goals:
                        self.set_main_goal(self.goals[0])
                    else:
                        self.main_goal_name.setText("(no main goal)")
                        self.main_goal_progress.setValue(0)
                        self.main_goal_amount_label.setText("Saved: $0.00 of $0.00")
                        self.main_goal_progress_label.setText(
                            "You're 0% of the way there."
                        )
            else:
                dlg.get_goal_data()
                for row in self.goal_rows:
                    if row.goal is goal:
                        row.update_from_goal()
                if getattr(self, "current_main_goal", None) is goal:
                    self.set_main_goal(goal)

    def _refresh_transactions_table(self):
        if not hasattr(self, "tx_table"):
            return

        self.transactions = prune_old_transactions(self.transactions)
        save_transactions(self.transactions)

        self.tx_table.setRowCount(len(self.transactions))

        for row_idx, tx in enumerate(self.transactions):
            ts = tx.get("timestamp")
            try:
                dt = datetime.fromisoformat(ts) if ts else None
            except (ValueError, TypeError):
                dt = None

            date_str = dt.strftime("%Y-%m-%d") if dt else ""
            kind_str = "Income" if tx.get("kind") == "income" else "Expense"
            cat_str = tx.get("category", "")
            amount_str = f"${tx.get('amount', 0.0):,.2f}"
            note_str = tx.get("note", "")

            self.tx_table.setItem(row_idx, 0, QTableWidgetItem(date_str))
            self.tx_table.setItem(row_idx, 1, QTableWidgetItem(kind_str))
            self.tx_table.setItem(row_idx, 2, QTableWidgetItem(cat_str))
            self.tx_table.setItem(row_idx, 3, QTableWidgetItem(amount_str))
            self.tx_table.setItem(row_idx, 4, QTableWidgetItem(note_str))

    def _update_balance_label(self):
        self.balance_label.setText(f"$ {self.balance:,.2f}")
        save_balance(self.balance)

    def _edit_balance(self):
        value, ok = QInputDialog.getDouble(
            self,
            "Edit Overall Balance",
            "Set new overall balance:",
            self.balance,
            -1_000_000_000,
            1_000_000_000,
            2,
        )
        if ok:
            self.balance = value
            self._update_balance_label()

    def _add_income(self):
        self._record_transaction(kind="income", sign=1)

    def _add_expense(self):
        self._record_transaction(kind="expense", sign=-1)

    def _record_transaction(self, kind: str, sign: int):
        dlg = TransactionDialog(kind=kind, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        tx = dlg.get_transaction()
        if tx["amount"] <= 0:
            return
        tx["timestamp"] = datetime.now().isoformat()
        self.transactions.append(tx)
        self.balance += sign * tx["amount"]
        self._update_balance_label()
        self._update_spending_trends()
        self._update_insights()
        save_transactions(self.transactions)
        self._refresh_transactions_table()

    def closeEvent(self, event):
        save_goals(self.goals)
        save_bills(self.bills)
        save_balance(self.balance)
        save_transactions(self.transactions)
        super().closeEvent(event)

    def _update_spending_trends(self):
        if hasattr(self, "spending_trends"):
            self.spending_trends.set_transactions(self.transactions)

    def _open_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/eduardobussien"))

    def _update_insights(self):
        one_week_ago = datetime.now() - timedelta(days=7)

        total_expense = 0.0
        total_income = 0.0
        by_category: dict[str, float] = {}

        for tx in self.transactions:
            ts_str = tx.get("timestamp")
            try:
                ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            if ts < one_week_ago:
                continue

            kind = tx.get("kind")
            amount = float(tx.get("amount", 0.0))
            category = tx.get("category", "Other")

            if kind == "expense":
                total_expense += amount
                by_category[category] = by_category.get(category, 0.0) + amount
            elif kind == "income":
                total_income += amount

        if by_category:
            top_cat = max(by_category.items(), key=lambda kv: kv[1])[0]
            self.insight_week_spent.setText(
                f"This week you spent ${total_expense:,.2f} (top: {top_cat})."
            )
        else:
            self.insight_week_spent.setText("No expense data for this week yet.")

        net = total_income - total_expense
        sign = "+" if net >= 0 else "-"
        self.insight_week_net.setText(
            f"Net change this week: {sign}${abs(net):,.2f}."
        )

        bills_total = sum(float(b.get("amount", 0.0)) for b in self.bills)
        self.insight_bills_total.setText(
            f"Total of your bills: ${bills_total:,.2f}."
        )


def main():
    app = QApplication(sys.argv)
    win = BudgeterWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
