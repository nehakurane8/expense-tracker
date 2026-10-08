# PaisaTrack - Expense Tracker

A full stack expense tracker built with Flask, SQLAlchemy and JavaScript.

## Features
- Add and delete expenses
- Category-wise doughnut chart (Chart.js)
- Monthly and total spending summary
- REST APIs with input validation

## Tech Stack
Python, Flask, SQLAlchemy, SQLite, JavaScript, HTML/CSS

## How to run
```bash
git clone https://github.com/nehakurane8/expense-tracker.git
cd expense-tracker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 

## API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /api/expenses | List all expenses |
| POST | /api/expenses | Add an expense |
| DELETE | /api/expenses/<id> | Delete an expense |
| GET | /api/summary | Totals and category summary |