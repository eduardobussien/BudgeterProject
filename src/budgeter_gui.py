import sys
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QToolButton, QMenu, QSizePolicy, QSpacerItem,
    QProgressBar, QDialog, QDialogButtonBox, QLineEdit,
    QDoubleSpinBox, QComboBox, QPushButton, QInputDialog,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView  
)

from datetime import datetime, timedelta 

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QFont

from budgeter_core import Goal

# ---- COLOR PALETTE  ----
BG_MAIN = "#021710"   
BG_CARD = "#05291b"   
FG_TEXT = "#e9fff3"   
ACCENT = "#28e07a"    


class CardWidget(QFrame):
    """Simple reusable 'card' with dark background and rounded corners."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {BG_CARD};
                border-radius: 14px;
            }}
        """)

class CircularProgressBar(QWidget):
    def __init__(self, size=220, thickness=18, max_value=100, parent=None):
        super().__init__(parent)
        self._value = 0
        self._max = max_value
        self._size = size
        self._thickness = thickness

        self.setMinimumSize(size, size)
        self.setMaximumSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def setValue(self, value: int):
        self._value = max(0, min(value, self._max))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self._size
        height = self._size

        # Centered square
        rect = self.rect()
        size = min(rect.width(), rect.height())
        margin = self._thickness // 2 + 4
        circle_rect = rect.adjusted(margin, margin, -margin, -margin)

        # ---------- Background circle (track) ----------
        bg_pen = QPen()
        bg_pen.setWidth(self._thickness)
        bg_pen.setColor(Qt.GlobalColor.darkGreen)
        painter.setPen(bg_pen)
        painter.drawArc(circle_rect, 0, 360 * 16)

        # ---------- Progress arc ----------
        if self._max > 0:
            angle_span = int((self._value / self._max) * 360 * 16)
        else:
            angle_span = 0

        fg_pen = QPen()
        fg_pen.setWidth(self._thickness)
        fg_pen.setColor(Qt.GlobalColor.green)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)

        # Start at top (-90 degrees)
        painter.drawArc(circle_rect, -90 * 16, -angle_span)

        # ---------- Text (percentage) ----------
        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Segoe UI", 20, QFont.Weight.Bold)
        painter.setFont(font)

        text = f"{int(self._value)}%"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

BASE_DIR = Path(__file__).resolve().parent.parent
GOALS_FILE = BASE_DIR / "data" / "goals.json"
BILLS_FILE = BASE_DIR / "data" / "bills.json"
BALANCE_FILE = BASE_DIR / "data" / "balance.json"
TRANSACTIONS_FILE = BASE_DIR / "data" / "transactions.json" 


def load_goals() -> list[Goal]:
    if not GOALS_FILE.exists():
        return []
    try:
        with GOALS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        goals: list[Goal] = []
        for item in data:
            goals.append(
                Goal(
                    name=item.get("name", "Untitled"),
                    current_amount=float(item.get("current_amount", 0.0)),
                    target_amount=float(item.get("target_amount", 0.0)),
                )
            )
        return goals
    except Exception as e:
        print("Failed to load goals:", e)
        return []


def save_goals(goals: list[Goal]) -> None:
    GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "name": g.name,
            "current_amount": g.current_amount,
            "target_amount": g.target_amount,
        }
        for g in goals
    ]
    try:
        with GOALS_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Failed to save goals:", e)

def load_bills() -> list[dict]:
    if not BILLS_FILE.exists():
        return []
    try:
        with BILLS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        bills: list[dict] = []
        for item in data:
            bills.append(
                {
                    "title": item.get("title", "Untitled bill"),
                    "amount": float(item.get("amount", 0.0)),
                }
            )
        return bills
    except Exception as e:
        print("Failed to load bills:", e)
        return []


def save_bills(bills: list[dict]) -> None:
    BILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {"title": b["title"], "amount": b["amount"]}
        for b in bills
    ]
    try:
        with BILLS_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Failed to save bills:", e)

def _prune_old_transactions(transactions: list[dict]) -> list[dict]:
    """Keep only the transactions from the last 7 days."""
    now = datetime.now()
    cutoff = now - timedelta(days=7)
    pruned: list[dict] = []

    for tx in transactions:
        ts = tx.get("timestamp")
        if not ts:
            # if missing timestamp, assume 'now' and keep
            tx["timestamp"] = now.isoformat()
            pruned.append(tx)
            continue
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            # if timestamp is weird, keep it rather than losing user data
            pruned.append(tx)
            continue
        if dt >= cutoff:
            pruned.append(tx)

    return pruned


def load_transactions() -> list[dict]:
    if not TRANSACTIONS_FILE.exists():
        return []
    try:
        with TRANSACTIONS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []

        txs = _prune_old_transactions(data)
        # if we removed old ones, save the cleaned list back
        if len(txs) != len(data):
            save_transactions(txs)
        return txs
    except Exception as e:
        print("Failed to load transactions:", e)
        return []


def save_transactions(transactions: list[dict]) -> None:
    try:
        TRANSACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with TRANSACTIONS_FILE.open("w", encoding="utf-8") as f:
            json.dump(transactions, f, indent=2)
    except Exception as e:
        print("Failed to save transactions:", e)

def load_balance() -> float:
    if not BALANCE_FILE.exists():
        return 0.0
    try:
        with BALANCE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # allow either plain number or {"balance": number}
        if isinstance(data, dict):
            return float(data.get("balance", 0.0))
        else:
            return float(data)
    except Exception as e:
        print("Failed to load balance:", e)
        return 0.0


def save_balance(balance: float) -> None:
    try:
        BALANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with BALANCE_FILE.open("w", encoding="utf-8") as f:
            json.dump({"balance": balance}, f, indent=2)
    except Exception as e:
        print("Failed to save balance:", e)



class GoalRowWidget(QFrame):
    clicked = pyqtSignal(object)         # emits Goal
    edit_requested = pyqtSignal(object)  # emits Goal

    def __init__(self, goal: Goal, color: str, parent=None):
        super().__init__(parent)
        self.goal = goal
        self.color = color

        self.setObjectName("goalRow")
        self.setStyleSheet("""
            QFrame#goalRow {
                background-color: #021f16;
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # Title
        self.title_label = QLabel(goal.name)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self.title_label, stretch=2)

        # Progress (percent label + bar)
        progress_col = QVBoxLayout()
        progress_col.setSpacing(2)

        self.percent_label = QLabel("")
        self.percent_label.setStyleSheet("font-size: 11px; color: #e9fff3;")

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #013323;
                border: 1px solid #025034;
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {self.color};
                border-radius: 6px;
            }}
        """)

        progress_col.addWidget(self.percent_label)
        progress_col.addWidget(self.progress)

        layout.addLayout(progress_col, stretch=3)

        # Edit button (three dots)
        self.edit_button = QToolButton()
        self.edit_button.setText("⋯")
        self.edit_button.setStyleSheet("""
            QToolButton {
                color: #e9fff3;
                font-size: 16px;
                padding: 2px 6px;
                border-radius: 12px;
                background-color: #073123;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        self.edit_button.clicked.connect(self._edit_clicked)
        layout.addWidget(self.edit_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.update_from_goal()

    def update_from_goal(self):
        g = self.goal
        if g.target_amount > 0:
            percent = int((g.current_amount / g.target_amount) * 100)
        else:
            percent = 0
        percent = max(0, min(percent, 100))

        self.title_label.setText(g.name)
        self.progress.setValue(percent)
        self.percent_label.setText(f"{percent} %")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.goal)
        return super().mousePressEvent(event)

    def _edit_clicked(self):
        self.edit_requested.emit(self.goal)

class BillRowWidget(QWidget):
    clicked = pyqtSignal(object)  # emits the bill dict

    def __init__(self, bill: dict, color: str, parent=None):
        super().__init__(parent)
        self.bill = bill

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # Colored circle
        circle = QFrame()
        circle.setFixedSize(18, 18)
        circle.setStyleSheet(f"""
            QFrame {{
                border-radius: 9px;
                border: 3px solid {color};
                background-color: transparent;
            }}
        """)
        layout.addWidget(circle)

        # Title
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Amount (right side)
        self.amount_label = QLabel("")
        self.amount_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self.amount_label)

        self.update_from_bill()

    def update_from_bill(self):
        self.title_label.setText(self.bill["title"])
        self.amount_label.setText(f"${self.bill['amount']:,.2f}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.bill)
        super().mousePressEvent(event)


class GoalEditDialog(QDialog):
    def __init__(self, goal: Goal | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Goal" if goal else "Add Goal")
        self.setModal(True)

        self.deleted = False   

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

        # ----- buttons: Save (+ Delete only when editing) -----
        buttons = QDialogButtonBox()
        self.save_button = buttons.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)

        if goal is not None:
            self.delete_button = buttons.addButton(
                "Delete", QDialogButtonBox.ButtonRole.DestructiveRole
            )
            self.delete_button.setStyleSheet("color: #ff6b81;")
            self.delete_button.clicked.connect(self._on_delete)

        self.save_button.clicked.connect(self._on_save)

        layout.addWidget(buttons)

        self._goal = goal
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
        if self._goal is None:
            return Goal(
                name=self.name_edit.text() or "Untitled Goal",
                current_amount=float(self.current_spin.value()),
                target_amount=float(self.target_spin.value()),
            )
        else:
            self._goal.name = self.name_edit.text() or "Untitled Goal"
            self._goal.current_amount = float(self.current_spin.value())
            self._goal.target_amount = float(self.target_spin.value())
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

        # Fill fields if editing
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
        """Create or update a bill dict based on dialog contents."""
        title = self.title_edit.text().strip() or "Untitled bill"
        amount = float(self.amount_spin.value())

        if self._bill is None:
            return {"title": title, "amount": amount}
        else:
        # update in place
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
        }



class BudgeterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Budgeter")
        self.resize(1200, 700)

        # Global background + label defaults
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

        # Overall balance and transactions (for income/expense)
        self.balance: float = load_balance()
        # each transaction: {kind, amount, category, note, timestamp}
        self.transactions: list[dict] = load_transactions()


        # ----- 3x3 GRID STRETCH (non-uniform) -----
        # Rows: top smaller, middle tallest, bottom medium
        grid.setRowStretch(0, 6)   
        grid.setRowStretch(1, 10) 
        grid.setRowStretch(2, 8)  

        # Columns: center widest, right narrower for dropdown
        grid.setColumnStretch(0, 8)   
        grid.setColumnStretch(1, 12)  
        grid.setColumnStretch(2, 5)   

        # ---------- (1,1) Top-left: Logo + Title + Subtitle ----------
        top_left = QWidget()   
        grid.addWidget(top_left, 0, 0)
        tl_layout = QHBoxLayout(top_left)

        tl_layout.setContentsMargins(16, 12, 16, 12)
        tl_layout.setSpacing(10)

        # --- small logo using your dollar image ---
        logo_label = QLabel()

        # Build an absolute path relative to this file:
        BASE_DIR = Path(__file__).resolve().parent.parent   # -> BDGTR/
        LOGO_PATH = BASE_DIR / "data" / "img" / "dollar_logo.png"

        print("Logo path:", LOGO_PATH)  # debug: you can see this in terminal

        try:
            pix = QPixmap(str(LOGO_PATH))
            if not pix.isNull():
                pix = pix.scaled(
                    120, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                logo_label.setPixmap(pix)
                logo_label.setScaledContents(False)
                # add the label to layout
                tl_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignVCenter)
            else:
                raise RuntimeError("Pixmap is null")
        except Exception as e:
            print("Failed to load logo:", e)
            # fallback circle
            logo_circle = QFrame()
            logo_circle.setFixedSize(32, 32)
            logo_circle.setStyleSheet(f"""
                QFrame {{
                    background-color: {ACCENT};
                    border-radius: 16px;
                }}
            """)
            tl_layout.addWidget(logo_circle, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Title + subtitle stack
        text_col = QVBoxLayout()
        text_col.setSpacing(2)   # small gap between title & subtitle
        text_col.setContentsMargins(0, 30, 20, 0)
        title = QLabel("Budgeter")
        title.setStyleSheet("font-size: 40px; font-weight: 1000; color: #b4ffd8;")
        subtitle = QLabel("Track • Plan • Grow")
        subtitle.setStyleSheet("font-size: 11px; color: #b4ffd8;")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        tl_layout.addLayout(text_col)

        tl_layout.addStretch()  # (1,1) stays compact, not huge
        # ---------- (1,3) Top-right: Centered Menu Button + "WIP" ----------
        top_right = QWidget()
        grid.addWidget(top_right, 0, 2)

        tr_layout = QVBoxLayout(top_right)
        tr_layout.setContentsMargins(4, 4, 4, 4)
        tr_layout.setSpacing(4)

        # MENU BUTTON (centered)
        menu_button = QToolButton()
        menu_button.setText("Menu")
        menu_button.setStyleSheet("""
            QToolButton {
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 8px;
                background-color: #0b3a28;
                font-weight: 600;
                font-size: 13px;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)

        menu = QMenu(menu_button)
        menu.addAction("Profile (WIP)", self._dummy_action)
        menu.addAction("Appearance (WIP)", self._dummy_action)
        menu.addSeparator()
        menu.addAction("About (WIP)", self._dummy_action)
        menu.addSeparator()
        menu.addAction("Settings (WIP)", self._dummy_action)
        menu_button.setMenu(menu)
        menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        tr_layout.addStretch()
        tr_layout.addWidget(menu_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        tr_layout.addStretch()

        # --- work in progress label ---
        wip_label = QLabel("(Work In Progress)")
        wip_label.setStyleSheet("font-size: 11px; color: #a3ffcf;")
        tr_layout.addWidget(wip_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        tr_layout.addStretch()


        # ---------- (1,2) & (2,2): Main Goal card (wider + tall) ----------
        main_goal = CardWidget()
        grid.addWidget(main_goal, 0, 1, 2, 1)  # rows 0-1, col 1

        mg_layout = QVBoxLayout(main_goal)
        mg_layout.setContentsMargins(18, 16, 18, 16)
        mg_layout.setSpacing(10)

        # ===== HEADER ROW: "Main Goal: <goal name>" =====
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

        # Small subtitle line under the header
        mg_sub = QLabel("Overview of your primary savings goal.")
        mg_sub.setStyleSheet("font-size: 11px; color: #a3ffcf;")
        mg_layout.addWidget(mg_sub)

        # ===== MAIN CONTENT AREA: left (circle+button), right (info+balance+button) =====
        content_layout = QHBoxLayout()
        content_layout.setSpacing(32)

        # ----- LEFT COLUMN: circular progress slightly lower -----
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        left_col.addStretch()  # pushes the circle slightly down

        self.main_goal_progress = CircularProgressBar(size=230, thickness=18, max_value=100)
        self.main_goal_progress.setValue(0)

        left_col.addWidget(
            self.main_goal_progress,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        left_col.addStretch()

        content_layout.addLayout(left_col, stretch=3)

        # ----- RIGHT COLUMN: goal info + Overall Balance + ADD EXPENSE -----
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Goal info (saved / percent)
        self.main_goal_amount_label = QLabel("Saved: $0.00 of $0.00")
        self.main_goal_amount_label.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.main_goal_progress_label = QLabel("You're 0% of the way there.")
        self.main_goal_progress_label.setStyleSheet("font-size: 12px; color: #c8ffe6;")

        right_col.addWidget(self.main_goal_amount_label)
        right_col.addWidget(self.main_goal_progress_label)
        right_col.addSpacing(18)

        # Overall Balance header + edit link in one row
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

        # Big balance label
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
        content_layout.addLayout(right_col, stretch=4)

        mg_layout.addLayout(content_layout)

        # ===== BOTTOM BUTTON ROW =====
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
        buttons_row.addSpacing(40)  # space between the two buttons
        buttons_row.addWidget(self.add_expense_btn)
        buttons_row.addStretch()

        mg_layout.addSpacing(30)
        mg_layout.addLayout(buttons_row)
        mg_layout.addStretch()


        # ---------- Other placeholder cards ----------
        def add_placeholder(row, col, text):
            card = CardWidget()
            grid.addWidget(card, row, col)
            vbox = QVBoxLayout(card)
            vbox.setContentsMargins(16, 16, 16, 16)
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 12px; color: #c8ffe6;")
            vbox.addWidget(label)
            return card


        # (2,1) Goals Summary card
        goals_card = CardWidget()
        grid.addWidget(goals_card, 1, 0)

        goals_layout = QVBoxLayout(goals_card)
        goals_layout.setContentsMargins(16, 16, 16, 16)
        goals_layout.setSpacing(10)

        # Header row: title + "+" button
        header_row = QHBoxLayout()
        header_label = QLabel("Goals Summary")
        header_label.setStyleSheet("font-size: 14px; font-weight: 700;")
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

        # Container where GoalRowWidget instances will be added
        self.goals_container = QVBoxLayout()
        self.goals_container.setSpacing(8)
        goals_layout.addLayout(self.goals_container)
        goals_layout.addStretch()

        # Build the rows from self.goals (loaded from file)
        self._rebuild_goal_rows()

        # If we have at least one goal, set the first as main
        if self.goals:
            self.set_main_goal(self.goals[0])


        # (2,3) – also in tall middle row
        add_placeholder(1, 2, "(2,3)\nSpending Trend\n(placeholder)")


        self.bills: list[dict] = load_bills()
        self.bill_rows: list[BillRowWidget] = []
        # (3,1) – Upcoming Bills
        bills_card = CardWidget()
        grid.addWidget(bills_card, 2, 0)

        bills_layout = QVBoxLayout(bills_card)
        bills_layout.setContentsMargins(16, 10, 16, 10)
        bills_layout.setSpacing(10)

        # Header row: title + "Add / edit" button
        header_row = QHBoxLayout()
        bills_header = QLabel("Upcoming Bills")
        bills_header.setStyleSheet("font-size: 14px; font-weight: 700;")
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


        # (3,2) – bottom row center: Transactions Summary
        tx_card = CardWidget()
        grid.addWidget(tx_card, 2, 1)

        tx_layout = QVBoxLayout(tx_card)
        tx_layout.setContentsMargins(16, 10, 16, 10)
        tx_layout.setSpacing(8)

        # header
        tx_header_row = QHBoxLayout()
        tx_title = QLabel("Transactions Summary")
        tx_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        tx_header_row.addWidget(tx_title)
        tx_header_row.addStretch()
        tx_layout.addLayout(tx_header_row)

        # table
        self.tx_table = QTableWidget(0, 5)
        self.tx_table.setHorizontalHeaderLabels(
            ["Date", "Type", "Category", "Amount", "Note"]
        )
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tx_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tx_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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

        # fill with any loaded transactions
        self._refresh_transactions_table()


        # (3,3) – bottom-right
        add_placeholder(2, 2, "(3,3)\nExtra / Tips\n(placeholder)")

        # NOTE for later:
        # When we add a background image, we can either:
        #  - draw it in a custom QWidget and place cards with transparent
        #    backgrounds, or
        #  - set it via a stylesheet for central widget.
        # For now cards stay opaque to keep it simple.

    def _dummy_action(self):
        print("Menu item clicked")

    def set_main_goal(self, goal):
        """Update the Main Goal card with the given Goal object."""
        self.current_main_goal = goal

        # Name
        self.main_goal_name.setText(goal.name)

        # Percentage
        if goal.target_amount > 0:
            percent = int((goal.current_amount / goal.target_amount) * 100)
        else:
            percent = 0
        percent = max(0, min(percent, 100))

        self.main_goal_progress.setValue(percent)

        # Amount text
        self.main_goal_amount_label.setText(
            f"Saved: ${goal.current_amount:,.2f} of ${goal.target_amount:,.2f}"
        )

        # Extra line
        self.main_goal_progress_label.setText(
            f"You're {percent}% of the way there."
        )


    def _rebuild_bill_rows(self):
        # Clear existing widgets from the container
        if hasattr(self, "bills_container"):
            while self.bills_container.count():
                item = self.bills_container.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
        self.bill_rows.clear()

        if not self.bills:
            # Centered clickable 'add/edit' text when there are no bills
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
                placeholder_btn,
                alignment=Qt.AlignmentFlag.AlignHCenter
            )
            self.bills_container.addStretch()
            return

        colors = ["#d7263d", "#ffd447", "#2d9cff", "#ff9ff3"]

        for i, bill in enumerate(self.bills):
            color = colors[i % len(colors)]
            row = BillRowWidget(bill, color)
            row.clicked.connect(self._open_edit_bill)  # click row to edit
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
                # remove bill
                if bill in self.bills:
                    self.bills.remove(bill)
                self._rebuild_bill_rows()
            else:
                # updated in place
                dlg.get_bill()
                for row in self.bill_rows:
                    if row.bill is bill:
                        row.update_from_bill()


    def _rebuild_goal_rows(self):
        # Clear existing widgets from the container
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
                # Remove goal
                if goal in self.goals:
                    self.goals.remove(goal)
                self._rebuild_goal_rows()

                # If it was the main goal, choose another or reset view
                if getattr(self, "current_main_goal", None) is goal:
                    self.current_main_goal = None
                    if self.goals:
                        self.set_main_goal(self.goals[0])
                    else:
                        # reset main goal UI
                        self.main_goal_name.setText("(no main goal)")
                        self.main_goal_progress.setValue(0)
                        self.main_goal_amount_label.setText("Saved: $0.00 of $0.00")
                        self.main_goal_progress_label.setText("You’re 0% of the way there.")
            else:
                # Save case: update goal in place + refresh UI
                dlg.get_goal_data()   
                for row in self.goal_rows:
                    if row.goal is goal:
                        row.update_from_goal()
                if getattr(self, "current_main_goal", None) is goal:
                    self.set_main_goal(goal)

    def _refresh_transactions_table(self):
        """Rebuild the (3,2) table from self.transactions."""
        if not hasattr(self, "tx_table"):
            return

        self.transactions = _prune_old_transactions(self.transactions)
        save_transactions(self.transactions)

        self.tx_table.setRowCount(len(self.transactions))

        for row_idx, tx in enumerate(self.transactions):
            # parse date safely
            ts = tx.get("timestamp")
            try:
                dt = datetime.fromisoformat(ts) if ts else None
            except Exception:
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
        # Simple dialog to directly set balance
        value, ok = QInputDialog.getDouble(
            self,
            "Edit Overall Balance",
            "Set new overall balance:",
            self.balance,
            -1_000_000_000,
            1_000_000_000,
            2
        )
        if ok:
            self.balance = value
            self._update_balance_label()

    def _add_income(self):
        dlg = TransactionDialog(kind="income", parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tx = dlg.get_transaction()
            if tx["amount"] <= 0:
                return
            tx["timestamp"] = datetime.now().isoformat()  
            self.transactions.append(tx)
            self.balance += tx["amount"]
            self._update_balance_label()
            save_transactions(self.transactions)       
            self._refresh_transactions_table()           

    def _add_expense(self):
        dlg = TransactionDialog(kind="expense", parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tx = dlg.get_transaction()
            if tx["amount"] <= 0:
                return
            tx["timestamp"] = datetime.now().isoformat()  
            self.transactions.append(tx)
            self.balance -= tx["amount"]
            self._update_balance_label()
            save_transactions(self.transactions)      
            self._refresh_transactions_table()        


    def closeEvent(self, event):
        save_goals(self.goals)
        save_bills(self.bills)
        save_balance(self.balance)
        save_transactions(self.transactions)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = BudgeterWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
