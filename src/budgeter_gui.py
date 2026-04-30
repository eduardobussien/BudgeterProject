"""Backwards-compatible re-exports.

The GUI was split into focused modules:
- src/main_window.py  — BudgeterWindow + main()
- src/widgets.py      — custom widgets (cards, progress bar, rows, charts)
- src/dialogs.py      — modal edit dialogs
- src/storage.py      — JSON load/save + paths
- src/theme.py        — color palette
"""

from src.main_window import BudgeterWindow, main

__all__ = ["BudgeterWindow", "main"]
