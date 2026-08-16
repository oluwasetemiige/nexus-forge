"""
routes/dashboard_routes.py
--------------------------
Dashboard endpoint — returns different data based on role:
  GET /api/dashboard  → client gets gigs + stats
                        freelancer gets applications + stats
  GET /api/health     → quick health check
"""

from flask import Blueprint, jsonify

from database import get_db
from models import gig_to_dict, application_to_dict
from auth import require_auth

dashboard_bp = Blueprint("dashboard", __name__)


# ---------------------------------------------------------------------------
# GET /api/dashboard
# ---------------------------------------------------------------------------
@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    user, err = require_auth()
    if err:
        return err

    db = get_db()

    if user["role"] == "client":
        return _client_dashboard(db, user)
    return _freelancer_dashboard(db, user)


def _client_dashboard(db, user) -> tuple:
    """Build dashboard payload for a client user."""
    gigs = db.execute(
        "SELECT * FROM gigs WHERE client_id = ? ORDER BY created_at DESC",
        (user["id"],),
    ).fetchall()

    # Count all applications across this client's gigs efficiently
    applications_count = 0
    if gigs:
        placeholders = ",".join("?" * len(gigs))
        gig_ids      = [g["id"] for g in gigs]
        applications_count = db.execute(
            f"SELECT COUNT(*) AS c FROM applications WHERE gig_id IN ({placeholders})",
            gig_ids,
        ).fetchone()["c"]

    return jsonify({
        "role":  "client",
        "gigs":  [gig_to_dict(g) for g in gigs],
        "stats": {
            "total_gigs":         len(gigs),
            "open_gigs":          sum(1 for g in gigs if g["status"] == "open"),
            "in_progress_gigs":   sum(1 for g in gigs if g["status"] == "in_progress"),
            "completed_gigs":     sum(1 for g in gigs if g["status"] == "completed"),
            "total_applications": applications_count,
        },
    })


def _freelancer_dashboard(db, user) -> tuple:
    """Build dashboard payload for a freelancer user."""
    apps = db.execute(
        """SELECT applications.*,
                  gigs.title  AS gig_title,
                  gigs.status AS gig_status,
                  gigs.budget
           FROM applications
           JOIN gigs ON applications.gig_id = gigs.id
           WHERE freelancer_id = ?
           ORDER BY applications.created_at DESC""",
        (user["id"],),
    ).fetchall()

    return jsonify({
        "role":         "freelancer",
        "applications": [application_to_dict(a, include_gig_info=True) for a in apps],
        "stats": {
            "total_applications": len(apps),
            "accepted":           sum(1 for a in apps if a["status"] == "accepted"),
            "pending":            sum(1 for a in apps if a["status"] == "pending"),
            "rejected":           sum(1 for a in apps if a["status"] == "rejected"),
            "nexus_score":        user["nexus_score"],
        },
    })


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------
@dashboard_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "nexus-forge-api"})
