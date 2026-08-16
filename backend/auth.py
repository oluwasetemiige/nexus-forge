"""
auth.py
-------
Authentication helpers used across all route files.

  current_user()  → returns the logged-in user Row or None
  require_auth()  → returns (user, None) or (None, error_response)
  require_role()  → decorator that checks role after auth
"""

import secrets
from datetime import datetime
from functools import wraps

from flask import request, jsonify
from database import get_db


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------
def current_user():
    """Extract and validate Bearer token → return user Row or None."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    db = get_db()
    return db.execute(
        """SELECT users.*
           FROM tokens
           JOIN users ON tokens.user_id = users.id
           WHERE tokens.token = ?""",
        (token,),
    ).fetchone()


def require_auth():
    """
    Call at the top of any protected route.
    Returns (user_row, None) on success, or (None, error_response) on failure.

    Usage:
        user, err = require_auth()
        if err:
            return err
    """
    user = current_user()
    if not user:
        return None, (jsonify({"error": "Authentication required"}), 401)
    return user, None


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------
def create_token(user_id: int) -> str:
    """Generate a secure token and persist it to the DB."""
    token = secrets.token_hex(32)
    now   = datetime.utcnow().isoformat()
    db    = get_db()
    db.execute(
        "INSERT INTO tokens (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, now),
    )
    db.commit()
    return token


def revoke_token(token: str) -> None:
    """Delete a token from the DB (logout)."""
    db = get_db()
    db.execute("DELETE FROM tokens WHERE token = ?", (token,))
    db.commit()


# ---------------------------------------------------------------------------
# Role decorator (optional convenience)
# ---------------------------------------------------------------------------
def require_role(*roles):
    """
    Decorator that enforces auth AND a specific role.

    Usage:
        @app.route("/api/gigs", methods=["POST"])
        @require_role("client")
        def create_gig(user):   ← user is injected automatically
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user, err = require_auth()
            if err:
                return err
            if user["role"] not in roles:
                allowed = " or ".join(roles)
                return jsonify({"error": f"Only {allowed}s can do this"}), 403
            return fn(user, *args, **kwargs)
        return wrapper
    return decorator
