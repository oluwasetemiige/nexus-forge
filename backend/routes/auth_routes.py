"""
routes/auth_routes.py
---------------------
Authentication endpoints:
  POST /api/register  → create account + return token
  POST /api/login     → verify credentials + return token
  GET  /api/me        → return current user profile
  POST /api/logout    → revoke token
"""

from datetime import datetime

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db
from models import user_to_dict
from auth import require_auth, create_token, revoke_token
from config import MIN_PASSWORD_LENGTH, VALID_ROLES

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# POST /api/register
# ---------------------------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data       = request.get_json(force=True, silent=True) or {}
    name       = (data.get("name") or "").strip()
    email      = (data.get("email") or "").strip().lower()
    password   = data.get("password") or ""
    role       = data.get("role") or "freelancer"
    is_student = bool(data.get("is_student", False))

    # ── Validation ─────────────────────────────────────────────────────────
    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400
    if role not in VALID_ROLES:
        return jsonify({"error": f"Role must be one of: {', '.join(VALID_ROLES)}"}), 400
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters"}), 400

    db = get_db()

    if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify({"error": "An account with this email already exists"}), 409

    # ── Create user ────────────────────────────────────────────────────────
    now  = datetime.utcnow().isoformat()
    cur  = db.execute(
        "INSERT INTO users (name, email, password_hash, role, is_student, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, generate_password_hash(password), role, int(is_student), now),
    )
    db.commit()

    token    = create_token(cur.lastrowid)
    user_row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify({"token": token, "user": user_to_dict(user_row)}), 201


# ---------------------------------------------------------------------------
# POST /api/login
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json(force=True, silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db       = get_db()
    user_row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user_row or not check_password_hash(user_row["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(user_row["id"])
    return jsonify({"token": token, "user": user_to_dict(user_row)})
                                                         


# ---------------------------------------------------------------------------
# GET /api/me
# ---------------------------------------------------------------------------
@auth_bp.route("/me", methods=["GET"])
def me():
    user, err = require_auth()
    if err:
        return err
    return jsonify({"user": user_to_dict(user)})


# ---------------------------------------------------------------------------
# POST /api/logout
# ---------------------------------------------------------------------------
@auth_bp.route("/logout", methods=["POST"])
def logout():
    user, err = require_auth()
    if err:
        return err
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ", 1)[1].strip()
    revoke_token(token)
    return jsonify({"ok": True})
