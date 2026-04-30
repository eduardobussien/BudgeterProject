from __future__ import annotations

from datetime import datetime, timedelta

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.budgeter_core import Goal
from src.theme import BG_CARD


class CardWidget(QFrame):
    """Reusable rounded dark card."""

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
    """Custom circular progress bar for the main goal."""

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

        rect = self.rect()
        margin = self._thickness // 2 + 4
        circle_rect = rect.adjusted(margin, margin, -margin, -margin)

        bg_pen = QPen()
        bg_pen.setWidth(self._thickness)
        bg_pen.setColor(Qt.GlobalColor.darkGreen)
        painter.setPen(bg_pen)
        painter.drawArc(circle_rect, 0, 360 * 16)

        angle_span = int(self._value / self._max * 360 * 16) if self._max > 0 else 0

        fg_pen = QPen()
        fg_pen.setWidth(self._thickness)
        fg_pen.setColor(Qt.GlobalColor.green)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)
        painter.drawArc(circle_rect, -90 * 16, -angle_span)

        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Segoe UI", 20, QFont.Weight.Bold)
        painter.setFont(font)
        text = f"{int(self._value)}%"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


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

        self.title_label = QLabel(goal.name)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self.title_label, stretch=2)

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
        percent = int(g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0
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

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self.title_label)

        layout.addStretch()

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


class SpendingTrendsWidget(QWidget):
    """Bar chart of weekly spending by category."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.transactions: list[dict] = []
        self.setMinimumHeight(200)

        self.bar_colors = [
            QColor("#ff6b81"),
            QColor("#ffd447"),
            QColor("#4da6ff"),
            QColor("#9b59b6"),
            QColor("#2ecc71"),
        ]

    def set_transactions(self, transactions: list[dict]):
        self.transactions = transactions
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        left_margin = 45
        right_margin = 20
        top_margin = 15
        bottom_margin = 40

        chart_left = left_margin
        chart_right = rect.width() - right_margin
        chart_top = top_margin
        chart_bottom = rect.height() - bottom_margin
        chart_width = chart_right - chart_left
        chart_height = chart_bottom - chart_top

        one_week_ago = datetime.now() - timedelta(days=7)
        categories: dict[str, float] = {}

        for tx in self.transactions:
            if tx.get("kind") != "expense":
                continue

            ts_str = tx.get("timestamp")
            try:
                ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            if ts < one_week_ago:
                continue

            cat = tx.get("category", "Other")
            categories[cat] = categories.get(cat, 0.0) + float(tx.get("amount", 0.0))

        if not categories:
            painter.setPen(QColor("#c8ffe6"))
            painter.setFont(QFont("Arial", 11))
            painter.drawText(
                rect,
                int(Qt.AlignmentFlag.AlignCenter),
                "No expense data for this week yet.",
            )
            painter.end()
            return

        axis_pen = QPen(QColor("#c8ffe6"))
        axis_pen.setWidth(1)
        painter.setPen(axis_pen)
        painter.drawLine(chart_left, chart_bottom, chart_right, chart_bottom)
        painter.drawLine(chart_left, chart_top, chart_left, chart_bottom)

        cats = list(categories.keys())
        values = [categories[c] for c in cats]

        max_tick = 100
        tick_step = 20

        painter.setFont(QFont("Arial", 9))
        for tick in range(0, max_tick + tick_step, tick_step):
            ratio = tick / max_tick
            y = chart_bottom - int(ratio * (chart_height - 10))

            painter.setPen(QPen(QColor("#235e4a")))
            painter.drawLine(chart_left - 4, y, chart_left, y)

            painter.setPen(QColor("#c8ffe6"))
            painter.drawText(
                chart_left - 38,
                y - 6,
                30,
                15,
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                str(tick),
            )

        bar_count = len(cats)
        bar_space = chart_width / max(bar_count, 1)
        bar_width = bar_space * 0.5

        for i, cat in enumerate(cats):
            val = values[i]
            capped = min(val, max_tick)
            ratio = capped / max_tick
            bar_h = ratio * (chart_height - 10)

            cx = chart_left + bar_space * i + bar_space / 2
            x1 = int(cx - bar_width / 2)
            y1 = int(chart_bottom - bar_h)
            w = int(bar_width)
            h = int(bar_h)

            color = self.bar_colors[i % len(self.bar_colors)]
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x1, y1, w, h, 4, 4)

            painter.setPen(QColor("#c8ffe6"))
            label_rect = QRect(
                int(cx - bar_space / 2),
                chart_bottom + 2,
                int(bar_space),
                20,
            )
            painter.drawText(
                label_rect,
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                cat,
            )

        painter.end()
