
from email import message

from flask import Blueprint, request, jsonify
from database import get_db
from auth import require_auth

message_bp = Blueprint("messages", __name__)

@message_bp.route("/messages/<int:gig_id>/<int:user_id>", methods=["GET"])
def get_messages(gig_id, user_id):
    user, err = require_auth()

    if err:
        return err

    db = get_db()

    messages = db.execute(
         """
    SELECT 
    id, 
    sender_id,
    reciever_id,
    gig_id,
    message,
    created_at
    FROM message
    WHERE gig_id = ?
    AND(
        (sender_id = ? AND reciever_id = ?)
        OR
        (sender_id = ? AND reciever_id = ?)
    )
    ORDER BY id ASC
    """,
    (gig_id, 
     user_id["id"],user_id,
     user_id, user_id["id"]
    )
    ).fetchall()
    return jsonify([
        dict(message)
        for message in messages
    ])


@message_bp.route("/messages", methods=["POST"])
def send_message():
    user, err = require_auth()

    if err:
        return err
    
    data = request.get_json(force= True, silent=True) or{}

    reciever_id = data.get("reciever_id")
    gig_id = data.get("gig_id")
    message = (data.get("message") or "").strip()
    if not reciever_id or not gig_id or not message:
        return jsonify({
            "error": "reciever_id, gig_id and message are required"
        }), 400
    
    db = get_db()

    allowed = db.execute(
        """
SELECT applications.id
FROM applications
JOIN gigs ON applications.gig_id = gigs.id
WHERE applications.gig_id = ?
AND applications.freelancer_id = ?
AND gig.client_id = ?
AND applications.status = 'accepted'
   
         """,
         (gig_id, reciever_id, user["id"])
    ).fetchone()

    if not allowed:
         allowed = db.execute(
        """
SELECT applications.id
FROM applications
JOIN gigs ON applications.gig_id = gigs.id
WHERE applications.gig_id = ?
AND applications.freelancer_id = ?
AND gig.client_id = ?
AND applications.status = 'accepted'
   
         """,
         (gig_id, reciever_id, user["id"])
    ).fetchone()
         
         if not allowed:
             return jsonify({
                "error": "messaging is only avaliable after acceptance"
             }),403
         
    db.execute(
            """
            INSERT INTO messages
            (sender_id, reciever_id, gig_id, message)
            VALUES(?, ?, ?, ?)
            """,
            (user["id"], reciever_id, gig_id, message)
        )
    db.commit()
    return jsonify({
        "ok": True,
        "message": "message sent"
    }), 201 
    

    
    