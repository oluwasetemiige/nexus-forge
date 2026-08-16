"""
routes/gig_routes.py
--------------------
Gig (job listing) endpoints:
  GET  /api/gigs              → browse open gigs (with search/filter)
  POST /api/gigs              → client posts a new gig
  GET  /api/gigs/<id>         → full gig detail + applications
"""

from datetime import datetime

from flask import Blueprint, request, jsonify

from database import get_db
from models import gig_to_dict, application_to_dict
from auth import require_auth

gig_bp = Blueprint("gigs", __name__)


# ---------------------------------------------------------------------------
# GET /api/gigs  — browse / search
# ---------------------------------------------------------------------------
@gig_bp.route("/gigs", methods=["GET"])
def list_gigs():
    category      = request.args.get("category", "").strip()
    search        = request.args.get("search", "").strip()
    beginner_only = request.args.get("beginner_only", "").strip().lower()

    db    = get_db()
    query = """
        SELECT gigs.*, users.name AS client_name
        FROM gigs
        JOIN users ON gigs.client_id = users.id
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


# ---------------------------------------------------------------------------
# POST /api/gigs  — create a gig (clients only)
# ---------------------------------------------------------------------------
@gig_bp.route("/gigs", methods=["POST"])
def create_gig():
    user, err = require_auth()
    if err:
        return err
    if user["role"] != "client":
        return jsonify({"error": "Only clients can post gigs"}), 403

    data              = request.get_json(force=True, silent=True) or {}
    title             = (data.get("title") or "").strip()
    description       = (data.get("description") or "").strip()
    category          = data.get("category") or "General"
    budget            = data.get("budget")
    budget_type       = data.get("budget_type") or "fixed"
    deadline          = data.get("deadline")
    beginner_friendly = bool(data.get("beginner_friendly", False))

    # ── Validation ─────────────────────────────────────────────────────────
    if not title or not description or budget is None:
        return jsonify({"error": "Title, description and budget are required"}), 400
    if budget_type not in ("fixed", "hourly"):
        return jsonify({"error": "budget_type must be fixed or hourly"}), 400
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return jsonify({"error": "Budget must be a number"}), 400

    # ── Insert ─────────────────────────────────────────────────────────────
    db  = get_db()
    now = datetime.utcnow().isoformat()
    cur = db.execute(
        """INSERT INTO gigs
               (client_id, title, description, category, budget, budget_type,
                deadline, beginner_friendly, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user["id"], title, description, category, budget,
         budget_type, deadline, int(beginner_friendly), now),
    )
    db.commit()

    gig_row = db.execute("SELECT * FROM gigs WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify({"gig": gig_to_dict(gig_row, user["name"])}), 201


# ---------------------------------------------------------------------------
# GET /api/gigs/<gig_id>  — full detail with applications
# ---------------------------------------------------------------------------
@gig_bp.route("/gigs/<int:gig_id>", methods=["GET"])
def get_gig(gig_id):
    db  = get_db()
    row = db.execute(
        """SELECT gigs.*, users.name AS client_name, users.nexus_score AS client_score
           FROM gigs
           JOIN users ON gigs.client_id = users.id
           WHERE gigs.id = ?""",
        (gig_id,),
    ).fetchone()

    if not row:
        return jsonify({"error": "Gig not found"}), 404

    gig_dict = gig_to_dict(row, row["client_name"])
    gig_dict["client_score"] = row["client_score"]

    app_rows = db.execute(
        """SELECT applications.*, users.name AS freelancer_name
           FROM applications
           JOIN users ON applications.freelancer_id = users.id
           WHERE gig_id = ?
           ORDER BY applications.created_at DESC""",
        (gig_id,),
    ).fetchall()

    gig_dict["applications"] = [application_to_dict(a) for a in app_rows]
    return jsonify({"gig": gig_dict})
