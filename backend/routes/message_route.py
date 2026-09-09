from datetime import datetime

from flask import Blueprint, request, jsonify

from database import get_db
from auth import require_auth


message_bp = Blueprint("messages", __name__)

def can_message(db, current_user_id, other_user_id, gig_id):

    # Get the gig
    gig = db.execute(
        """
        SELECT client_id
        FROM gigs
        WHERE id = ?
        """,
        (gig_id,)
    ).fetchone()

    if not gig:
        return False

    client_id = gig["client_id"]

    # --------------------------------------------------
    # CLIENT -> FREELANCER
    # --------------------------------------------------

    if current_user_id == client_id:

        accepted = db.execute(
            """
            SELECT id
            FROM applications
            WHERE gig_id = ?
              AND freelancer_id = ?
              AND status = 'accepted'
            """,
            (gig_id, other_user_id)
        ).fetchone()

        return accepted is not None

    # --------------------------------------------------
    # FREELANCER -> CLIENT
    # --------------------------------------------------

    if other_user_id == client_id:

        accepted = db.execute(
            """
            SELECT id
            FROM applications
            WHERE gig_id = ?
              AND freelancer_id = ?
              AND status = 'accepted'
            """,
            (gig_id, current_user_id)
        ).fetchone()

        return accepted is not None

    # Nobody else can communicate
    return False


# ======================================================
# SEND MESSAGE
# POST /api/messages
# ======================================================

@message_bp.route("/messages", methods=["POST"])
def send_message():

    user, err = require_auth()

    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}
    gig_id = data.get("gig_id")
    receiver_id = data.get("receiver_id")
    content = (data.get("content") or " ").strip()

    if not gig_id or not receiver_id or not content:
        return jsonify({
            "error": "gig_id, receiver_id and content are required"
        }), 400

    try:
        gig_id = int(gig_id)
        receiver_id = int(receiver_id)
    except (TypeError, ValueError):
        return jsonify({
            "error": "gig_id and receiver_id must be numbers"
        }), 400

    if receiver_id == user["id"]:
        return jsonify({
            "error": "You cannot message yourself"
        }), 400

    db = get_db()

    # Check whether these two users are allowed
    # to communicate about this gig.
    if not can_message(
        db,
        user["id"],
        receiver_id,
        gig_id
    ):
        return jsonify({
            "error": "Messaging is only available after acceptance"
        }), 403

    now = datetime.utcnow().isoformat()

    db.execute(
        """
        INSERT INTO messages
        (sender_id, receiver_id, gig_id, content, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            receiver_id,
            gig_id,
            content,
            now
        )
    )

    db.commit()

    return jsonify({
        "ok": True,
        "message": "Message sent"
    }), 201


# ======================================================
# GET MESSAGES
# GET /api/messages/<gig_id>/<user_id>
# ======================================================

@message_bp.route("/messages/<int:gig_id>/<int:user_id>", methods=["GET"])
def get_messages(gig_id, user_id):

    user, err = require_auth()

    if err:
        return err

    db = get_db()

    # Make sure this conversation is allowed
    if not can_message(
        db,
        user["id"],
        user_id,
        gig_id
    ):
        return jsonify({
            "error": "Messaging is only available after acceptance"
        }), 403

    messages = db.execute(
        """
        SELECT
            id,
            sender_id,
           receiver_id,
            gig_id,
            content,
            created_at
        FROM messages
        WHERE gig_id = ?
          AND
            (
              (sender_id = ? AND receiver_id = ?)
              OR
              (sender_id = ? AND receiver_id = ?)
            )
        ORDER BY id ASC
        """,
        (
            gig_id,
            user["id"],
            user_id,
            user_id,
            user["id"]
        )
    ).fetchall()

    return jsonify({
        "messages": [dict(message) for message in messages]
    })