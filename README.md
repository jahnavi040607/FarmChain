# FarmChain

A beginner-friendly farm-to-customer traceability demo.

## Included features
- Dashboard with product counts and recent activity
- Register products with farmer, location, category and harvest details
- Product inventory
- Customer tracking by unique product ID
- QR code generation for each product
- SQLite database
- Tamper-evident SHA-256 hash-linked ledger and integrity verification
- Simple demo quality score (transparent heuristic)

## Run on Windows
1. Install Python 3.10 or newer from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract this ZIP.
3. Double-click `run.bat`. It creates a virtual environment, installs requirements and starts the app.
4. Open http://127.0.0.1:5000 in your browser.
5. Try tracking the sample product with ID `FARM001`.

If `run.bat` does not work, open Command Prompt in this folder and run:
```
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

## Important project note
The current version is a working local prototype. Its ledger is a SHA-256 hash chain in SQLite, which demonstrates linked, tamper-evident records; it is **not** yet deployed to Ethereum/Ganache and is not decentralized. The quality score is a simple demonstration heuristic, not a trained AI/ML model. These can be connected in a later phase.

## GitHub
Create a public repository named `FarmChain`, upload the project files, and push to the `main` branch. Do not upload `.venv`, `farmchain.db`, or secrets. GitHub Pages can host only a static frontend; this Flask + SQLite app needs a Python-capable host for a public live website.

## Main files
- `app.py` — Flask routes, SQLite database and hash-chain logic
- `templates/` — website pages
- `static/style.css` — styling
