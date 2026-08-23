"""
auth.py
-------
Authentication helpers used across all route files.

  current_user()  → returns the logged-in user Row or None
  require_auth()  → returns (user, None) or (None, error_response)
  require_role()  → decorator that checks role after auth
"""

import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import request, jsonify
from database import get_db




# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------
def current_user():
    """
    Get the currently authenticated user from the Authorization header.

    Expected format:
        Authorization: Bearer <token>

    Returns:
        user row, or None if authentication fails.
    """

    header = request.headers.get("Authorization", "")
    token = request.cookies.get("nf_token")

    if header.startswith("Bearer "):
        token = header[7:].strip()

    if not header:
        return None

    parts = header.split(" ", 1)

    if len(parts) != 2:
        return None

    scheme, token = parts

    if scheme.lower() != "bearer" or not token.strip():
        return None

    token = token.strip()

    db = get_db()

    # IMPORTANT:
    # The table is called "tokens", so use tokens.expires_at.
    token_row = db.execute(
        """
        SELECT
            tokens.token,
            tokens.user_id,
            tokens.created_at,
            tokens.expires_at
        FROM tokens
        JOIN users
            ON tokens.user_id = users.id
        WHERE tokens.token = ?
          AND (
              tokens.expires_at IS NULL
              OR tokens.expires_at > ?
          )
        """,
        (
            token,
            datetime.utcnow().isoformat(),
        ),
    ).fetchone()

    if token_row is None:
        return None

    user_row = db.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (token_row["user_id"],),
    ).fetchone()

    return user_row

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
    now   = datetime.utcnow()
    expires_at = now + timedelta(days=7)
    db    = get_db()
    db.execute(
        "INSERT INTO tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, 
         user_id,
           now.isoformat(), 
           expires_at.isoformat(),
        ),
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
