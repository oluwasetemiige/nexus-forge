"""
database.py
-----------
Handles everything SQLite-related:
  - Per-request connection via Flask's `g`
  - Schema creation (init_db)
  - Teardown hook
"""

import sqlite3
from flask import g
from config import DB_PATH


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
def get_db():
    """Return the current request's DB connection, creating it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    """Tear down the DB connection at the end of each request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK(role IN ('freelancer', 'client')),
    is_student    INTEGER DEFAULT 0,
    bio           TEXT    DEFAULT '',
    skills        TEXT    DEFAULT '',
    nexus_score   INTEGER DEFAULT 50,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    token      TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    created_at TEXT    NOT NULL,
    expires_at TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS gigs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id        INTEGER NOT NULL,
    title            TEXT    NOT NULL,
    description      TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    budget           REAL    NOT NULL,
    budget_type      TEXT    NOT NULL CHECK(budget_type IN ('fixed', 'hourly')),
    deadline         TEXT,
    status           TEXT    NOT NULL DEFAULT 'open'
                             CHECK(status IN ('open', 'in_progress', 'completed', 'cancelled')),
    beginner_friendly INTEGER DEFAULT 0,
    created_at       TEXT    NOT NULL,
    FOREIGN KEY (client_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    gig_id        INTEGER NOT NULL,
    freelancer_id INTEGER NOT NULL,
    proposal      TEXT    NOT NULL,
    price         REAL    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'pending'
                          CHECK(status IN ('pending', 'accepted', 'rejected')),
    created_at    TEXT    NOT NULL,
    FOREIGN KEY (gig_id)        REFERENCES gigs(id)  ON DELETE CASCADE,
    FOREIGN KEY (freelancer_id) REFERENCES users(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS messages(
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id       INTEGER NOT NULL,
   receiver_id      INTEGER NOT NULL,
    gig_id          INTEGER NOT NULL,
    content         TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sender_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (gig_id)  REFERENCES gigs(id) ON DELETE CASCADE
);

"""


def init_db():
    """Create all tables if they don't exist. Called once at startup."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"✅ Database ready → {DB_PATH}")
