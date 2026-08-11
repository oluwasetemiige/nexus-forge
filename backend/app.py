"""
Nexus Forge — Backend API
Flask + SQLite. No external DB required — runs out of the box.

Run:
    pip install -r requirements.txt
    python app.py

Server starts on http://localhost:5000
"""

import sqlite3
import secrets
import os
from datetime import datetime
from flask import Flask, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "nexus_forge.db")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# CORS (manual — no flask-cors dependency needed)
# ---------------------------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def cors_preflight(_any):
    return "", 204


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('freelancer', 'client')),
            is_student INTEGER DEFAULT 0,
            bio TEXT DEFAULT '',
            skills TEXT DEFAULT '',
            nexus_score INTEGER DEFAULT 50,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gigs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            budget REAL NOT NULL,
            budget_type TEXT NOT NULL CHECK(budget_type IN ('fixed', 'hourly')),
            deadline TEXT,
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'completed', 'cancelled')),
            beginner_friendly INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gig_id INTEGER NOT NULL,
            freelancer_id INTEGER NOT NULL,
            proposal TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected')),
            created_at TEXT NOT NULL,
            FOREIGN KEY (gig_id) REFERENCES gigs(id) ON DELETE CASCADE,
            FOREIGN KEY (freelancer_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    db = get_db()
    row = db.execute(
        "SELECT users.* FROM tokens JOIN users ON tokens.user_id = users.id WHERE tokens.token = ?",
        (token,),
    ).fetchone()
    return row


def require_auth():
    user = current_user()
    if not user:
        return None, (jsonify({"error": "Authentication required"}), 401)
    return user, None


def user_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "is_student": bool(row["is_student"]),
        "bio": row["bio"],
        "skills": row["skills"],
        "nexus_score": row["nexus_score"],
        "created_at": row["created_at"],
    }


def gig_to_dict(row, client_name=None):
    d = {
        "id": row["id"],
        "client_id": row["client_id"],
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "budget": row["budget"],
        "budget_type": row["budget_type"],
        "deadline": row["deadline"],
        "status": row["status"],
        "beginner_friendly": bool(row["beginner_friendly"]),
        "created_at": row["created_at"],
    }
    if client_name is not None:
        d["client_name"] = client_name
    return d


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") or "freelancer"
    is_student = bool(data.get("is_student", False))

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400
    if role not in ("freelancer", "client"):
        return jsonify({"error": "Role must be freelancer or client"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({"error": "An account with this email already exists"}), 409

    password_hash = generate_password_hash(password)
    now = datetime.utcnow().isoformat()
    cur = db.execute(
        "INSERT INTO users (name, email, password_hash, role, is_student, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, password_hash, role, int(is_student), now),
    )
    db.commit()
    user_id = cur.lastrowid

    token = secrets.token_hex(32)
    db.execute(
        "INSERT INTO tokens (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, now),
    )
    db.commit()

    user_row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return jsonify({"token": token, "user": user_to_dict(user_row)}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = get_db()
    user_row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user_row or not check_password_hash(user_row["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = secrets.token_hex(32)
    db.execute(
        "INSERT INTO tokens (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_row["id"], datetime.utcnow().isoformat()),
    )
    db.commit()

    return jsonify({"token": token, "user": user_to_dict(user_row)})


@app.route("/api/me", methods=["GET"])
def me():
    user, err = require_auth()
    if err:
        return err
    return jsonify({"user": user_to_dict(user)})


@app.route("/api/logout", methods=["POST"])
def logout():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        db = get_db()
        db.execute("DELETE FROM tokens WHERE token = ?", (token,))
        db.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Gig routes
# ---------------------------------------------------------------------------
@app.route("/api/gigs", methods=["GET"])
def list_gigs():
    db = get_db()
    category = request.args.get("category")
    search = request.args.get("q")
    beginner_only = request.args.get("beginner_friendly")

    query = """
        SELECT gigs.*, users.name as client_name
        FROM gigs JOIN users ON gigs.client_id = users.id
        WHERE gigs.status = 'open'
    """
    params = []
    if category and category != "all":
        query += " AND gigs.category = ?"
        params.append(category)
    if search:
        query += " AND (gigs.title LIKE ? OR gigs.description LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])
    if beginner_only == "true":
        query += " AND gigs.beginner_friendly = 1"
    query += " ORDER BY gigs.created_at DESC"

    rows = db.execute(query, params).fetchall()
    return jsonify({"gigs": [gig_to_dict(r, r["client_name"]) for r in rows]})


@app.route("/api/gigs", methods=["POST"])
def create_gig():
    user, err = require_auth()
    if err:
        return err
    if user["role"] != "client":
        return jsonify({"error": "Only clients can post gigs"}), 403

    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category = data.get("category") or "General"
    budget = data.get("budget")
    budget_type = data.get("budget_type") or "fixed"
    deadline = data.get("deadline")
    beginner_friendly = bool(data.get("beginner_friendly", False))

    if not title or not description or budget is None:
        return jsonify({"error": "Title, description and budget are required"}), 400
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return jsonify({"error": "Budget must be a number"}), 400

    db = get_db()
    now = datetime.utcnow().isoformat()
    cur = db.execute(
        """INSERT INTO gigs
           (client_id, title, description, category, budget, budget_type, deadline, beginner_friendly, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user["id"], title, description, category, budget, budget_type, deadline, int(beginner_friendly), now),
    )
    db.commit()
    gig_row = db.execute("SELECT * FROM gigs WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify({"gig": gig_to_dict(gig_row, user["name"])}), 201


@app.route("/api/gigs/<int:gig_id>", methods=["GET"])
def get_gig(gig_id):
    db = get_db()
    row = db.execute(
        """SELECT gigs.*, users.name as client_name, users.nexus_score as client_score
           FROM gigs JOIN users ON gigs.client_id = users.id WHERE gigs.id = ?""",
        (gig_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "Gig not found"}), 404
    d = gig_to_dict(row, row["client_name"])
    d["client_score"] = row["client_score"]
    apps = db.execute(
        """SELECT applications.*, users.name as freelancer_name
           FROM applications JOIN users ON applications.freelancer_id = users.id
           WHERE gig_id = ? ORDER BY applications.created_at DESC""",
        (gig_id,),
    ).fetchall()
    d["applications"] = [
        {
            "id": a["id"],
            "freelancer_id": a["freelancer_id"],
            "freelancer_name": a["freelancer_name"],
            "proposal": a["proposal"],
            "price": a["price"],
            "status": a["status"],
            "created_at": a["created_at"],
        }
        for a in apps
    ]
    return jsonify({"gig": d})


@app.route("/api/gigs/<int:gig_id>/apply", methods=["POST"])
def apply_to_gig(gig_id):
    user, err = require_auth()
    if err:
        return err
    if user["role"] != "freelancer":
        return jsonify({"error": "Only freelancers can apply to gigs"}), 403

    data = request.get_json(force=True, silent=True) or {}
    proposal = (data.get("proposal") or "").strip()
    price = data.get("price")
    if not proposal or price is None:
        return jsonify({"error": "Proposal and price are required"}), 400
    try:
        price = float(price)
    except (TypeError, ValueError):
        return jsonify({"error": "Price must be a number"}), 400

    db = get_db()
    gig = db.execute("SELECT * FROM gigs WHERE id = ?", (gig_id,)).fetchone()
    if not gig:
        return jsonify({"error": "Gig not found"}), 404
    if gig["status"] != "open":
        return jsonify({"error": "This gig is no longer accepting applications"}), 400

    existing = db.execute(
        "SELECT id FROM applications WHERE gig_id = ? AND freelancer_id = ?",
        (gig_id, user["id"]),
    ).fetchone()
    if existing:
        return jsonify({"error": "You already applied to this gig"}), 409

    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO applications (gig_id, freelancer_id, proposal, price, created_at) VALUES (?, ?, ?, ?, ?)",
        (gig_id, user["id"], proposal, price, now),
    )
    db.commit()
    return jsonify({"ok": True}), 201


@app.route("/api/applications/<int:app_id>/status", methods=["PUT"])
def update_application_status(app_id):
    user, err = require_auth()
    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    status = data.get("status")
    if status not in ("accepted", "rejected"):
        return jsonify({"error": "Status must be accepted or rejected"}), 400

    db = get_db()
    application = db.execute(
        """SELECT applications.*, gigs.client_id, gigs.id as gig_id
           FROM applications JOIN gigs ON applications.gig_id = gigs.id
           WHERE applications.id = ?""",
        (app_id,),
    ).fetchone()
    if not application:
        return jsonify({"error": "Application not found"}), 404
    if application["client_id"] != user["id"]:
        return jsonify({"error": "Not authorized to update this application"}), 403

    db.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
    if status == "accepted":
        db.execute("UPDATE gigs SET status = 'in_progress' WHERE id = ?", (application["gig_id"],))
    db.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    user, err = require_auth()
    if err:
        return err
    db = get_db()

    if user["role"] == "client":
        gigs = db.execute(
            "SELECT * FROM gigs WHERE client_id = ? ORDER BY created_at DESC", (user["id"],)
        ).fetchall()
        gig_ids = [g["id"] for g in gigs]
        applications_count = 0
        if gig_ids:
            placeholders = ",".join("?" * len(gig_ids))
            applications_count = db.execute(
                f"SELECT COUNT(*) as c FROM applications WHERE gig_id IN ({placeholders})", gig_ids
            ).fetchone()["c"]
        return jsonify({
            "role": "client",
            "gigs": [gig_to_dict(g) for g in gigs],
            "stats": {
                "total_gigs": len(gigs),
                "open_gigs": sum(1 for g in gigs if g["status"] == "open"),
                "total_applications": applications_count,
            },
        })
    else:
        apps = db.execute(
            """SELECT applications.*, gigs.title as gig_title, gigs.status as gig_status, gigs.budget
               FROM applications JOIN gigs ON applications.gig_id = gigs.id
               WHERE freelancer_id = ? ORDER BY applications.created_at DESC""",
            (user["id"],),
        ).fetchall()
        return jsonify({
            "role": "freelancer",
            "applications": [
                {
                    "id": a["id"], "gig_id": a["gig_id"], "gig_title": a["gig_title"],
                    "gig_status": a["gig_status"], "proposal": a["proposal"],
                    "price": a["price"], "status": a["status"], "created_at": a["created_at"],
                }
                for a in apps
            ],
            "stats": {
                "total_applications": len(apps),
                "accepted": sum(1 for a in apps if a["status"] == "accepted"),
                "pending": sum(1 for a in apps if a["status"] == "pending"),
                "nexus_score": user["nexus_score"],
            },
        })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "nexus-forge-api"})


if __name__ == "__main__":
    init_db()
    print("Nexus Forge API running -> http://localhost:5000")
    app.run(debug=True, port=5000)
