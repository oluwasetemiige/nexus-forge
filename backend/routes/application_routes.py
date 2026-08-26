"""
routes/application_routes.py
----------------------------
Application (proposal) endpoints:
  POST /api/gigs/<id>/apply              → freelancer submits proposal
  PUT  /api/applications/<id>/status     → client accepts or rejects
"""

from datetime import datetime

from flask import Blueprint, request, jsonify

from database import get_db
from auth import require_auth

application_bp = Blueprint("applications", __name__)


# ---------------------------------------------------------------------------
# POST /api/gigs/<gig_id>/apply  — freelancer submits a proposal
# ---------------------------------------------------------------------------
@application_bp.route("/gigs/<int:gig_id>/apply", methods=["POST"])
def apply_to_gig(gig_id):
    user, err = require_auth()
    if err:
        return err
    if user["role"] != "freelancer":
        return jsonify({"error": "Only freelancers can apply to gigs"}), 403

    data     = request.get_json(force=True, silent=True) or {}
    proposal = (data.get("proposal") or "").strip()
    price    = data.get("price")

    # ── Validation ─────────────────────────────────────────────────────────
    if not proposal or price is None:
        return jsonify({"error": "Proposal and price are required"}), 400
    try:
        price = float(price)
    except (TypeError, ValueError):
        return jsonify({"error": "Price must be a number"}), 400
    if price <= 0:
        return jsonify({"error": "Price must be greater than zero"}), 400

    db  = get_db()
    gig = db.execute("SELECT * FROM gigs WHERE id = ?", (gig_id,)).fetchone()

    if not gig:
        return jsonify({"error": "Gig not found"}), 404
    if gig["status"] != "open":
        return jsonify({"error": "This gig is no longer accepting applications"}), 400
    if gig["client_id"] == user["id"]:
        return jsonify({"error": "You cannot apply to your own gig"}), 400

    # ── Duplicate check ────────────────────────────────────────────────────
    existing = db.execute(
        "SELECT id FROM applications WHERE gig_id = ? AND freelancer_id = ?",
        (gig_id, user["id"]),
    ).fetchone()
    if existing:
        return jsonify({"error": "You already applied to this gig"}), 409

    # ── Insert ─────────────────────────────────────────────────────────────
    now = datetime.utcnow().isoformat()
    cur = db.execute(
        "INSERT INTO applications (gig_id, freelancer_id, proposal, price, created_at) VALUES (?, ?, ?, ?, ?)",
        (gig_id, user["id"], proposal, price, now),
    )
    db.commit()
    return jsonify({"ok": True, "application_id": cur.lastrowid}), 201


# ---------------------------------------------------------------------------
# PUT /api/applications/<app_id>/status  — client accepts or rejects
# ---------------------------------------------------------------------------
@application_bp.route("/applications/<int:app_id>/status", methods=["PUT"])
def update_application_status(app_id):
    user, err = require_auth()
    if err:
        return err
    if user["role"] != "client":
        return jsonify({"error": "Only clients can update application status"}), 403

    data   = request.get_json(force=True, silent=True) or {}
    status = data.get("status")

    if status not in ("accepted", "rejected"):
        return jsonify({"error": "Status must be 'accepted' or 'rejected'"}), 400

    db          = get_db()
    application = db.execute(
        """SELECT applications.*, gigs.client_id, gigs.id AS gig_id
           FROM applications
           JOIN gigs ON applications.gig_id = gigs.id
           WHERE applications.id = ?""",
        (app_id,),
    ).fetchone()

    if not application:
        return jsonify({"error": "Application not found"}), 404
    if application["client_id"] != user["id"]:
        return jsonify({"error": "Not authorized to update this application"}), 403

    # ── Update ─────────────────────────────────────────────────────────────
    db.execute(
        "UPDATE applications SET status = ? WHERE id = ?",
          (status, app_id)
          )
    db.commit()    
    return jsonify({"ok": True, "status": status})
