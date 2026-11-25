# NexGen Shop Manager — MVP 0.1.0

Offline-first Android shop-management starter built with Python, Kivy 2.3.0 and SQLite.

## Included
- Product catalogue, cost and selling price, quantity and low-stock alert
- Single-product sales with stock deduction in the same SQLite transaction
- Customer contact records and expense records
- Today's dashboard and all-time sales/profit/expense/stock report
- SQLite database stored in the app's private Android data directory

## Build
Run in this directory on Linux with Java 17 and Android SDK prerequisites:
```bash
python -m pip install buildozer==1.5.0 cython==0.29.33 virtualenv
buildozer android debug
```
APK output is in bin/. A separate manual GitHub Actions workflow builds this app.

## MVP limitations
USD only; no ZWG/USD multi-currency, barcode scanner, cart, receipts, refunds, tax settings, customer credit ledger, login, cloud sync or automatic backup. Test on a device and back up records before live bookkeeping.
