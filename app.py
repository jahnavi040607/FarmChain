from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import sqlite3, hashlib, json, os, io
from datetime import datetime, timezone
from pathlib import Path

try:
    import qrcode
except ImportError:
    qrcode = None

BASE = Path(__file__).resolve().parent
DB = BASE / "farmchain.db"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-for-production")

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def digest(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            farmer TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            harvest_date TEXT NOT NULL,
            quality TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL,
            event TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            record_hash TEXT NOT NULL
        )""")
        count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            con.execute("""INSERT INTO products
                (product_code,name,farmer,location,category,harvest_date,quality,notes,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                ("FARM001","Organic Tomatoes","Ravi Kumar","Rajanukunte, Bengaluru",
                 "Vegetables","2026-11-15","A","Demo product — replace with your own farm data",now))
            add_ledger(con, "FARM001", "Product registered",
                       "Organic Tomatoes registered by Ravi Kumar")

def add_ledger(con, code, event, details):
    last = con.execute("SELECT record_hash FROM ledger ORDER BY id DESC LIMIT 1").fetchone()
    previous = last["record_hash"] if last else "0" * 64
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = json.dumps({"product_code":code,"event":event,"details":details,
                          "timestamp":timestamp,"previous_hash":previous}, sort_keys=True)
    record_hash = digest(payload)
    con.execute("""INSERT INTO ledger
        (product_code,event,details,timestamp,previous_hash,record_hash)
        VALUES (?,?,?,?,?,?)""",
        (code,event,details,timestamp,previous,record_hash))

def quality_score(category, notes):
    # Transparent demo heuristic; replace with a trained ML model for a real AI score.
    text = (category + " " + notes).lower()
    score = 82
    if "organic" in text or "fresh" in text: score += 8
    if "damaged" in text or "spoiled" in text: score -= 35
    if "pesticide" in text: score -= 15
    score = max(0, min(100, score))
    grade = "A" if score >= 85 else ("B" if score >= 70 else "Needs review")
    return score, grade

@app.route("/")
def index():
    with connect() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        events = con.execute("SELECT * FROM ledger ORDER BY id DESC LIMIT 5").fetchall()
        total = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        avg = con.execute("SELECT AVG(CASE quality WHEN 'A' THEN 95 WHEN 'B' THEN 80 ELSE 60 END) FROM products").fetchone()[0] or 0
    return render_template("index.html", products=products, events=events, total=total, avg=round(avg))

@app.route("/products")
def products_page():
    with connect() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("products.html", products=products)

@app.route("/add", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        farmer = request.form.get("farmer","").strip()
        location = request.form.get("location","").strip()
        category = request.form.get("category","").strip()
        harvest_date = request.form.get("harvest_date","").strip()
        notes = request.form.get("notes","").strip()
        if not all([name, farmer, location, category, harvest_date]):
            flash("Please complete all required fields.", "error")
            return redirect(url_for("add_product"))
        code = "FC" + datetime.now().strftime("%y%m%d%H%M%S")
        score, grade = quality_score(category, notes)
        now = datetime.now(timezone.utc).isoformat()
        try:
            with connect() as con:
                con.execute("""INSERT INTO products
                    (product_code,name,farmer,location,category,harvest_date,quality,notes,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (code,name,farmer,location,category,harvest_date,grade,notes,now))
                add_ledger(con, code, "Product registered",
                           f"{name}; farmer: {farmer}; quality score: {score}/100")
            flash(f"Product added successfully. Tracking ID: {code}", "success")
            return redirect(url_for("track_product", code=code))
        except sqlite3.IntegrityError:
            flash("A product with this ID already exists. Please try again.", "error")
    return render_template("add.html")

@app.route("/track", methods=["GET", "POST"])
def track():
    if request.method == "POST":
        code = request.form.get("code","").strip()
        return redirect(url_for("track_product", code=code))
    return render_template("track.html")

@app.route("/track/<code>")
def track_product(code):
    with connect() as con:
        product = con.execute("SELECT * FROM products WHERE product_code=?", (code,)).fetchone()
        events = con.execute("SELECT * FROM ledger WHERE product_code=? ORDER BY id", (code,)).fetchall()
    if not product:
        flash("No product found for that tracking ID.", "error")
        return redirect(url_for("track"))
    return render_template("track_result.html", product=product, events=events)

@app.route("/qr/<code>.png")
def qr_code(code):
    if qrcode is None:
        return "Install qrcode[pil] to enable QR codes.", 503
    with connect() as con:
        exists = con.execute("SELECT 1 FROM products WHERE product_code=?", (code,)).fetchone()
    if not exists: return "Product not found", 404
    url = request.url_root.rstrip("/") + url_for("track_product", code=code)
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"{code}-qr.png")

@app.route("/verify")
def verify_chain():
    with connect() as con:
        rows = con.execute("SELECT * FROM ledger ORDER BY id").fetchall()
    previous = "0" * 64
    valid = True
    for row in rows:
        payload = json.dumps({"product_code":row["product_code"],"event":row["event"],
            "details":row["details"],"timestamp":row["timestamp"],
            "previous_hash":row["previous_hash"]}, sort_keys=True)
        expected = digest(payload)
        if row["previous_hash"] != previous or row["record_hash"] != expected:
            valid = False
            break
        previous = row["record_hash"]
    return render_template("verify.html", valid=valid, count=len(rows), rows=rows)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
