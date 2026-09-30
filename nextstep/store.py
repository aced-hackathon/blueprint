"""Reproducible synthetic histories. Amounts are integer euro cents."""
import random
import sqlite3
from pathlib import Path

TODAY = "2026-09-30"
PEOPLE = [("sofia", "Sofia Martin", "SM", "Leuven", 580000),
          ("thomas", "Thomas Peeters", "TP", "Ghent", 430000),
          ("emma", "Emma Laurent", "EL", "Brussels", 690000),
          ("noah", "Noah Vermeulen", "NV", "Antwerp", 520000)]

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS customers(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, initials TEXT NOT NULL,
 city TEXT NOT NULL, opening_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS transactions(
 id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id),
 date TEXT NOT NULL, category TEXT NOT NULL, label TEXT NOT NULL, cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS events(
 id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id),
 date TEXT NOT NULL, kind TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS preferences(
 customer_id TEXT PRIMARY KEY REFERENCES customers(id),
 trends INTEGER NOT NULL DEFAULT 1, activity INTEGER NOT NULL DEFAULT 1,
 revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS goals(
 customer_id TEXT PRIMARY KEY REFERENCES customers(id),
 status TEXT NOT NULL DEFAULT 'unconfirmed', target_date TEXT,
 reminder_date TEXT, suppressed INTEGER NOT NULL DEFAULT 0,
 rent_cents INTEGER NOT NULL DEFAULT 95000, deposit_months INTEGER NOT NULL DEFAULT 2,
 moving_cents INTEGER NOT NULL DEFAULT 45000,
 checklist TEXT NOT NULL DEFAULT '[]', shared_statement TEXT);
CREATE TABLE IF NOT EXISTS decisions(
 id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT NOT NULL REFERENCES customers(id),
 date TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS travel_scenarios(
 customer_id TEXT PRIMARY KEY REFERENCES customers(id),
 commute_one_way_m INTEGER NOT NULL, commute_car_days INTEGER NOT NULL,
 grocery_current_one_way_m INTEGER NOT NULL, grocery_nearby_one_way_m INTEGER NOT NULL,
 grocery_trips_month INTEGER NOT NULL, car_g_per_km INTEGER NOT NULL,
 selected_option TEXT);
"""

class Connection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

def connect(path):
    db = sqlite3.connect(path, factory=Connection)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

def seed(db):
    rng = random.Random(20260930)
    for cid, name, initials, city, opening in PEOPLE:
        seed_person(db, (cid, name, initials, city, opening), rng)
    db.commit()

def seed_person(db, person, rng):
    cid, name, initials, city, opening = person
    db.execute("INSERT INTO customers VALUES(?,?,?,?,?)", (cid, name, initials, city, opening))
    db.execute("INSERT INTO preferences(customer_id) VALUES(?)", (cid,))
    db.execute("INSERT INTO goals(customer_id) VALUES(?)", (cid,))
    for month in range(4, 10):
        rows = [("income", "Monthly salary", 305000 + (15000 if cid == "thomas" else 0)),
                ("rent", "Monthly rent", -95000),
                ("groceries", "Groceries & everyday essentials", -rng.randint(34000, 41000)),
                ("transport", "Transport", -rng.randint(8500, 14500)),
                ("utilities", "Utilities & connectivity", -19500),
                ("leisure", "Leisure & dining", -rng.randint(17000, 27000)),
                ("other", "Other spending", -rng.randint(23000, 32000)),
                ("home", "Home & furnishings", -(18500 if month == 9 and cid in {"sofia", "thomas"} else rng.randint(2800, 4800)))]
        for i, (category, label, cents) in enumerate(rows):
            day = 1 if category == "income" else 3 + i * 3
            db.execute("INSERT INTO transactions VALUES(?,?,?,?,?,?)", (
                f"{cid}-{month}-{i}", cid, f"2026-{month:02d}-{day:02d}", category, label, cents))
    db.execute("INSERT INTO transactions VALUES(?,?,?,?,?,?)", (f"{cid}-refund", cid, "2026-08-25", "home", "Home purchase refund", 1500))
    if cid == "noah":
        for i in range(3):
            db.execute("INSERT INTO events VALUES(?,?,?,?)", (f"{cid}-carbon-{i}", cid, f"2026-09-{19+i:02d}", "lower_carbon_guide_view"))
        for i in range(2):
            db.execute("INSERT INTO events VALUES(?,?,?,?)", (f"{cid}-bike-{i}", cid, f"2026-09-{24+i:02d}", "bike_route_preview"))
        # Customer-provided what-if settings, separate from inferred payment behaviour.
        db.execute("INSERT INTO travel_scenarios VALUES(?,?,?,?,?,?,?,NULL)",
                   (cid, 6000, 5, 4400, 1200, 4, 160))
    else:
        for i in range(1 if cid == "emma" else 3):
            db.execute("INSERT INTO events VALUES(?,?,?,?)", (f"{cid}-guide-{i}", cid, f"2026-09-{21+i:02d}", "rental_guide_view"))

def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript(SCHEMA)
        if not db.execute("SELECT 1 FROM customers LIMIT 1").fetchone():
            seed(db)
        elif not db.execute("SELECT 1 FROM customers WHERE id='noah'").fetchone():
            seed_person(db, PEOPLE[-1], random.Random(20260930))

def reset_customer(db, cid):
    db.execute("DELETE FROM decisions WHERE customer_id=?", (cid,))
    db.execute("DELETE FROM goals WHERE customer_id=?", (cid,))
    db.execute("DELETE FROM preferences WHERE customer_id=?", (cid,))
    db.execute("INSERT INTO goals(customer_id) VALUES(?)", (cid,))
    db.execute("INSERT INTO preferences(customer_id) VALUES(?)", (cid,))
    db.execute("UPDATE travel_scenarios SET selected_option=NULL WHERE customer_id=?", (cid,))
