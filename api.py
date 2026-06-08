import sqlite3
from contextlib import contextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="VolunteerApp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).parent / "db.sqlite"

# Seed data matching Variant 20 exam tables
SEED = [
    {"VolunteerID": 1, "FullName": "Nargiz T.",  "Skills": "First Aid",  "Phone": "055-200"},
    {"VolunteerID": 2, "FullName": "Rashad H.",  "Skills": "Teaching",   "Phone": "070-300"},
    {"VolunteerID": 3, "FullName": "Ulviyya M.", "Skills": "IT Support", "Phone": "051-400"},
]


# ── Helper function get_db() — connects to SQLite ─────────────
@contextmanager
def get_db():
    """Helper function get_db() — connects to SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Volunteers (
                VolunteerID  INTEGER PRIMARY KEY,
                FullName     TEXT    NOT NULL,
                Skills       TEXT    NOT NULL DEFAULT '',
                Phone        TEXT    NOT NULL DEFAULT ''
            )
        """)
        if conn.execute("SELECT COUNT(*) FROM Volunteers").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO Volunteers VALUES (:VolunteerID, :FullName, :Skills, :Phone)",
                SEED,
            )


init_db()


# ── Pydantic model for Volunteers — Question 5(a) ─────────────
class VolunteerIn(BaseModel):
    VolunteerID: int
    FullName:    str = Field(min_length=3, max_length=100)
    Skills:      str = Field(min_length=2, max_length=100)
    Phone:       str = Field(min_length=6, max_length=20)


# GET /volunteers — return all records
@app.get("/volunteers")
def get_volunteers():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM Volunteers ORDER BY VolunteerID"
        ).fetchall()
    return [dict(r) for r in rows]


# POST /volunteers — add a new record
@app.post("/volunteers", status_code=201)
def add_volunteer(volunteer: VolunteerIn):
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM Volunteers WHERE VolunteerID = ?",
            (volunteer.VolunteerID,)
        ).fetchone()
        if exists:
            raise HTTPException(
                status_code=400,
                detail=f"VolunteerID {volunteer.VolunteerID} already exists"
            )
        conn.execute(
            "INSERT INTO Volunteers VALUES (?, ?, ?, ?)",
            (volunteer.VolunteerID, volunteer.FullName, volunteer.Skills, volunteer.Phone),
        )
    return volunteer.model_dump()


# DELETE /volunteers/{id} — delete a record by ID
@app.delete("/volunteers/{volunteer_id}")
def delete_volunteer(volunteer_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM Volunteers WHERE VolunteerID = ?", (volunteer_id,)
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"VolunteerID {volunteer_id} not found"
            )
        conn.execute("DELETE FROM Volunteers WHERE VolunteerID = ?", (volunteer_id,))
    return dict(row)
