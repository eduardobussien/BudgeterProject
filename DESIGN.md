# DESIGN DOCUMENT – Budgeter
Author: Eduardo Bussien  
Course: Software Engineering - Final Project

---

## 1. Introduction

Budgeter is a desktop personal finance dashboard designed to help users manage goals, bills, income, expenses, and overall financial progress. The application emphasizes **clean architecture**, **modularity**, **persistent storage**, **object-oriented design**, and **PyQt6 GUI development**.  
This document describes the system’s architecture, data model, interface design, interaction flows, and key design decisions.

---

## 2. High–Level Architecture

Budgeter follows a **modular, object-oriented architecture** divided into the following major components:

### **2.1 Core Data Layer (`budgeter_core.py`)**
- Defines the `Goal` class (name, current amount, target amount).
- Contains simple business logic such as progress calculation.
- Decoupled from the GUI to support unit testing and future extensions.

### **2.2 GUI Layer (`budgeter_gui.py`)**
- Implements all windows, dialogs, and custom widgets using PyQt6.
- Handles user input and updates the display in response to state changes.
- Contains:
  - `BudgeterWindow` (main window)
  - Dialogs (GoalEditDialog, BillEditDialog, TransactionDialog)
  - Custom widgets (GoalRowWidget, BillRowWidget, CircularProgressBar)
  - Layout structure for the 3×3 dashboard

### **2.3 Application Entry Point (`main.py`)**
- Initializes the PyQt application
- Loads the main window and begins the event loop

### **2.4 Persistent Storage**
Budgeter stores data in JSON files:
- goals.json  
- bills.json  
- balance.json  
- transactions.json  

When running as an EXE, these files are stored in:

%APPDATA%/BudgeterProject


The entire storage layer is isolated behind helper functions:
- `load_goals()`, `save_goals()`
- `load_bills()`, `save_bills()`
- `load_balance()`, `save_balance()`
- transaction load/save handlers

---

## 3. User Interface Design

The interface uses a **3×3 grid layout**, creating a structured dashboard similar to modern personal-finance apps. This design choice gives the UI a clean and predictable layout while allowing flexibility for future panels.

### **3.1 Grid Overview**

┌───────────┬───────────────┬───────────┐
│ Logo │ Main Goal (top) │ Menu │
├───────────┼───────────────┼───────────┤
│ Goals │ Main Goal (bottom) │ Trends │
├───────────┼───────────────┼───────────┤
│ Bills │ Transactions │ Tips │
└───────────┴───────────────┴───────────┘


### **3.2 Top-Left: Branding & Logo**
- Displays application name “Budgeter”
- Includes a custom dollar-sign logo
- Subtitle: *Track • Plan • Grow*

### **3.3 Top-Right: Menu**
- A `QToolButton` labeled **MENU**
- Contains placeholder actions:
  - Profile (WIP)
  - Appearance (WIP)
  - About (working)
  - Settings (WIP)

### **3.4 Main Goal Card (center panel)**
This card spans two grid rows and is the centerpiece of the application.

Components:
- Header: **Main Goal: {goal name}**
- Subtitle: “Overview of your primary savings goal.”
- **Circular progress bar** (custom-painted with PyQt6’s `QPainter`)
- Saved vs target (“$160 of $270”)
- Calculated percentage text (“59% of the way there”)
- **Overall Balance** with editable value
- Income/Expense buttons with dialogs

The internal layout uses nested HBoxes and VBoxes to organize:
- Title & subtitle
- Left: circular progress bar
- Right: saved/target text + balance
- Bottom: action buttons

### **3.5 Goals Summary (middle-left)**
- Displays a list of goals using `GoalRowWidget`
- Each row includes:
  - Name  
  - Progress bar  
  - Percentage  
  - “…” edit button  
- Rows are clickable—selecting one updates the Main Goal card
- Add Goal (“+”) button triggers `GoalEditDialog`

### **3.6 Upcoming Bills (bottom-left)**
- Bills stored as `{title, amount}`
- Displayed using `BillRowWidget`, with:
  - Colored circular indicator  
  - Title  
  - Amount  
- “Add / edit” button opens `BillEditDialog`

### **3.7 Transactions Summary (bottom-middle)**
- Scrollable table of:
  - Date  
  - Type (Income / Expense)  
  - Category  
  - Amount  
  - Note  
- Auto-pruning: records older than 7 days removed
- Updated live when income/expense is added

### **3.8 Spending Trend (top-right middle)**
- Bar chart visualizing weekly spending by category
- Generates totals for Food, Personal, School

### **3.9 Insights & Tips (bottom-right)**
- Weekly spending total
- Net change (income – expenses)
- Total monthly bills
- This panel auto-updates whenever transactions occur

---

## 4. Dialogs & Interaction Flow

The system uses several modal dialogs for user interactions:

### **4.1 GoalEditDialog**
Allows:
- Editing name
- Editing target amount
- Editing current amount
- Deleting a goal when applicable

### **4.2 BillEditDialog**
Allows:
- Editing bill title
- Editing amount
- Deleting a bill

### **4.3 TransactionDialog**
Used for **both** income and expenses:
- Amount (required)
- Category (dropdown)
- Optional note
- Saves to JSON and updates balance instantly

---

## 5. Data Model

### **5.1 Goals**
Stored as dictionaries in JSON:

{
"name": "Trip to Norway",
"current_amount": 760.0,
"target_amount": 4500.0
}


### **5.2 Bills**

{
"title": "House Rent",
"amount": 180.00
}


### **5.3 Balance**

{
"balance": 1776.60
}


### **5.4 Transactions**

{
"date": "2025-12-06",
"kind": "Expense",
"category": "Food",
"amount": 12.50,
"note": "Chick-Fil-A"
}


A pruning function automatically deletes entries older than 7 days.

---

## 6. Program Flow

### **Startup**
1. Main window created  
2. JSON files loaded (or created if missing)  
3. Main Goal selected (first goal by default)  
4. All panels populated  

### **User Interaction**
Examples:
- Adding a goal → updates goals list → updates main goal if none existed  
- Adding income → updates balance → adds transaction → updates Insights & Trends  
- Deleting a bill → removes it from JSON → GUI refreshes  

### **Shutdown**
- All JSON files are saved:
  - goals.json  
  - bills.json  
  - balance.json  
  - transactions.json  

---

## 7. Custom Widgets

### **CircularProgressBar**
- Drawn using QPainter arcs
- Supports smooth progress transitions
- Fully reusable in other future components

### **GoalRowWidget**
- Compact goal representation
- Clickable to change Main Goal
- Includes small progress bar and percent text

### **BillRowWidget**
- Colored circle indicator
- Title + amount layout
- Clickable to open edit dialog

---

## 8. Testing Strategy

### **Unit Tests**
- Located in `tests/test_budgeter_core.py`
- Test:
  - Goal initialization
  - Progress calculation logic
  - Basic data model integrity

### **Manual Integration Testing**
Performed for:
- Adding/editing/deleting goals  
- Adding/editing/deleting bills  
- Adding income/expense  
- Balance updating  
- Weekly trend graph  
- Transaction pruning  

---

## 9. Design Rationale

- **Modularity**: GUI and logic separated for easier maintenance.
- **JSON Storage**: Human-readable, simple, ideal for student desktop apps.
- **PyQt6 Layouts**: Grid structure ensures predictable UI scaling.
- **Custom Widgets**: Improve look-and-feel and give a polished, modern feel.
- **Auto-Pruning Transactions**: Prevents long-term JSON bloat.
- **Executable Packaging**: PyInstaller used to embed assets inside EXE for portability.

---

## 10. Future Extensions

- Full analytics dashboard  
- Multi-month trends  
- CSV export  
- Cloud sync  
- Multiple profiles  
- Theme customization  
- Recurring bill automation  

---

## 11. Conclusion

The final design achieves a clean, scalable, and modular budgeting application.  
The architecture allows new features (analytics, CSV export, user profiles) to be added easily without major structural changes.  
The 3×3 grid layout, custom widgets, and persistent JSON model create a professional and intuitive user experience.

Budgeter provides a strong foundation for continued development and demonstrates solid application of software-engineering principles.