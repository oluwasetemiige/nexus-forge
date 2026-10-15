
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import (
    Blueprint,
    request,
    jsonify,
    send_file,
)

from werkzeug.utils import secure_filename

from database import get_db
from auth import require_auth


message_bp = Blueprint("messages", __name__)

# ---------------------------------------------------------
# FILE STORAGE
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_FOLDER = BASE_DIR / "private_message_uploads"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".pdf",
}

ALLOWED_MIME_TYPES = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".gif": {"image/gif"},
    ".webp": {"image/webp"},
    ".pdf": {"application/pdf"},
}


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def json_error(message, status=400):
    return jsonify({"error": message}), status


def can_message(db, current_user_id, other_user_id, gig_id):
    """
    Allow communication only between:
      - The client who owns the gig.
      - A freelancer whose application was accepted.

    Other users cannot access this conversation.
    """

    gig = db.execute(
        """
        SELECT client_id
        FROM gigs
        WHERE id = ?
        """,
        (gig_id,),
    ).fetchone()

    if not gig:
        return False

    client_id = gig["client_id"]

    # Client communicating with an accepted freelancer.
    if current_user_id == client_id:

        accepted = db.execute(
            """
            SELECT id
            FROM applications
            WHERE gig_id = ?
              AND freelancer_id = ?
              AND status = 'accepted'
            """,
            (gig_id, other_user_id),
        ).fetchone()

        return accepted is not None

    # Accepted freelancer communicating with the client.
    if other_user_id == client_id:

        accepted = db.execute(
            """
            SELECT id
            FROM applications
            WHERE gig_id = ?
              AND freelancer_id = ?
              AND status = 'accepted'
            """,
            (gig_id, current_user_id),
        ).fetchone()

        return accepted is not None

    return False


def valid_file_signature(extension, content):
    """
    Check the actual file signature instead of trusting
    the filename and browser-provided MIME type alone.
    """

    if extension == ".pdf":
        return content.startswith(b"%PDF-")

    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")

    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")

    if extension == ".gif":
        return content.startswith((b"GIF87a", b"GIF89a"))

    if extension == ".webp":
        return (
            len(content) >= 12
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        )

    return False


def serialize_message(row):
    return {
        "id": row["id"],
        "sender_id": row["sender_id"],
        "receiver_id": row["receiver_id"],
        "gig_id": row["gig_id"],
        "content": row["content"],
        "created_at": row["created_at"],
        "attachment": (
            {
                "name": row["attachment_name"],
                "mime": row["attachment_mime"],
                "size": row["attachment_size"],
                "url": (
                    f"/api/messages/attachments/{row['id']}"
                ),
            }
            if row["attachment_name"]
            else None
        ),
    }


# ---------------------------------------------------------
# SEND MESSAGE
#
# POST /api/messages
#
# Accepts:
#   - JSON for text messages.
#   - multipart/form-data for messages with attachments.
# ---------------------------------------------------------

@message_bp.route("/messages", methods=["POST"])
def send_message():

    user, err = require_auth()

    if err:
        return err

    db = get_db()

    uploaded_file = None
    saved_path = None

    # -----------------------------------------------------
    # Read request data
    # -----------------------------------------------------

    if request.files or request.mimetype == "multipart/form-data":

        data = request.form

        uploaded_file = request.files.get("attachment")

        content = (data.get("content") or "").strip()

        gig_id = data.get("gig_id")
        receiver_id = data.get("receiver_id")

    else:

        data = request.get_json(silent=True) or {}

        content = (data.get("content") or "").strip()

        gig_id = data.get("gig_id")
        receiver_id = data.get("receiver_id")

    # -----------------------------------------------------
    # Validate IDs
    # -----------------------------------------------------

    try:
        gig_id = int(gig_id)
        receiver_id = int(receiver_id)

    except (TypeError, ValueError):
        return json_error(
            "gig_id and receiver_id must be valid numbers"
        )

    if receiver_id == user["id"]:
        return json_error("You cannot message yourself")

    if not content and not uploaded_file:
        return json_error(
            "Enter a message or attach a file"
        )

    if len(content) > 5000:
        return json_error(
            "Messages cannot exceed 5,000 characters"
        )

    # -----------------------------------------------------
    # Check authorization
    # -----------------------------------------------------

    if not can_message(
        db,
        user["id"],
        receiver_id,
        gig_id,
    ):
        return json_error(
            "Messaging is only available after acceptance",
            403,
        )

    # -----------------------------------------------------
    # Validate attachment
    # -----------------------------------------------------

    attachment_name = None
    attachment_path = None
    attachment_mime = None
    attachment_size = None

    if uploaded_file and uploaded_file.filename:

        original_name = secure_filename(
            uploaded_file.filename
        )

        extension = Path(original_name).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            return json_error(
                "Only JPG, PNG, GIF, WEBP and PDF files are allowed"
            )

        if not original_name:
            return json_error("Invalid filename")

        # Read at most 10 MB plus one byte.
        file_content = uploaded_file.stream.read(
            MAX_FILE_SIZE + 1
        )

        if not file_content:
            return json_error("The uploaded file is empty")

        if len(file_content) > MAX_FILE_SIZE:
            return json_error(
                "Files cannot exceed 10 MB"
            )

        mime_type = uploaded_file.mimetype or ""

        if mime_type not in ALLOWED_MIME_TYPES[extension]:
            return json_error(
                "The file type does not match its extension"
            )

        if not valid_file_signature(
            extension,
            file_content,
        ):
            return json_error(
                "The uploaded file is not a valid supported file"
            )

        # Never use the user's filename as the storage path.
        stored_name = f"{uuid.uuid4().hex}{extension}"

        destination = UPLOAD_FOLDER / stored_name

        try:

            with open(destination, "xb") as file:
                file.write(file_content)

        except OSError:
            return json_error(
                "The attachment could not be saved",
                500,
            )

        saved_path = str(destination)

        attachment_name = original_name
        attachment_path = stored_name
        attachment_mime = mime_type
        attachment_size = len(file_content)

    # -----------------------------------------------------
    # Save message
    # -----------------------------------------------------

    # Store real UTC with a trailing "Z" so browsers convert it to local time correctly.
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    try:

        cursor = db.execute(
            """
            INSERT INTO messages (
                sender_id,
                receiver_id,
                gig_id,
                content,
                created_at,
                attachment_name,
                attachment_path,
                attachment_mime,
                attachment_size
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                receiver_id,
                gig_id,
                content,
                now,
                attachment_name,
                attachment_path,
                attachment_mime,
                attachment_size,
            ),
        )

        db.commit()

    except Exception:

        db.rollback()

        # Remove an uploaded file if saving its message failed.
        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)

        raise

    return jsonify({
        "ok": True,
        "message": "Message sent",
        "message_id": cursor.lastrowid,
    }), 201


# ---------------------------------------------------------
# GET CONVERSATION MESSAGES
#
# GET /api/messages/<gig_id>/<user_id>
# ---------------------------------------------------------

@message_bp.route(
    "/messages/<int:gig_id>/<int:user_id>",
    methods=["GET"],
)
def get_messages(gig_id, user_id):

    user, err = require_auth()

    if err:
        return err

    db = get_db()

    if user["id"] == user_id:
        return json_error(
            "You cannot open a conversation with yourself"
        )

    if not can_message(
        db,
        user["id"],
        user_id,
        gig_id,
    ):
        return json_error(
            "You are not allowed to access this conversation",
            403,
        )

    rows = db.execute(
        """
        SELECT
            id,
            sender_id,
            receiver_id,
            gig_id,
            content,
            created_at,
            attachment_name,
            attachment_path,
            attachment_mime,
            attachment_size
        FROM messages
        WHERE gig_id = ?
          AND (
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
            user["id"],
        ),
    ).fetchall()

    return jsonify({
        "messages": [
            serialize_message(row)
            for row in rows
        ]
    })


# ---------------------------------------------------------
# GET CONVERSATION LIST
#
# GET /api/messages/conversations
#
# A conversation exists as soon as a client ACCEPTS an application,
# even before anyone has sent a message. (The old version built the
# list from existing messages, so nobody could ever send the first one.)
# ---------------------------------------------------------

@message_bp.route(
    "/messages/conversations",
    methods=["GET"],
)
def get_conversations():

    user, err = require_auth()

    if err:
        return err

    db = get_db()
    me = user["id"]

    rows = db.execute(
        """
        WITH pairs AS (
            SELECT
                g.id    AS gig_id,
                g.title AS gig_title,
                CASE
                    WHEN g.client_id = ? THEN a.freelancer_id
                    ELSE g.client_id
                END AS other_id
            FROM applications a
            JOIN gigs g ON g.id = a.gig_id
            WHERE a.status = 'accepted'
              AND (g.client_id = ? OR a.freelancer_id = ?)
        )
        SELECT
            p.gig_id,
            p.gig_title,
            p.other_id        AS other_user_id,
            u.name            AS other_user_name,
            u.role            AS other_user_role,
            m.content         AS last_content,
            m.attachment_name AS last_attachment,
            m.created_at      AS last_message_at
        FROM pairs p
        JOIN users u ON u.id = p.other_id
        LEFT JOIN messages m ON m.id = (
            SELECT MAX(id)
            FROM messages
            WHERE gig_id = p.gig_id
              AND (
                  (sender_id = ? AND receiver_id = p.other_id)
                  OR
                  (sender_id = p.other_id AND receiver_id = ?)
              )
        )
        ORDER BY COALESCE(m.id, 0) DESC, p.gig_id DESC
        """,
        (me, me, me, me, me),
    ).fetchall()

    conversations = []

    for row in rows:

        if row["last_content"]:
            preview = row["last_content"]
        elif row["last_attachment"]:
            preview = "\U0001F4CE " + row["last_attachment"]
        else:
            preview = ""

        conversations.append({
            "gig_id": row["gig_id"],
            "gig_title": row["gig_title"],
            "other_user_id": row["other_user_id"],
            "other_user_name": row["other_user_name"],
            "other_user_role": row["other_user_role"],
            "last_message": preview,
            "last_message_at": row["last_message_at"],
        })

    return jsonify({"conversations": conversations})


# ---------------------------------------------------------
# DOWNLOAD / VIEW ATTACHMENT
#
# GET /api/messages/attachments/<message_id>
#
# Attachment URLs are protected by authentication.
# ---------------------------------------------------------

@message_bp.route(
    "/messages/attachments/<int:message_id>",
    methods=["GET"],
)
def get_attachment(message_id):

    user, err = require_auth()

    if err:
        return err

    db = get_db()

    row = db.execute(
        """
        SELECT
            id,
            sender_id,
            receiver_id,
            gig_id,
            attachment_name,
            attachment_path,
            attachment_mime
        FROM messages
        WHERE id = ?
        """,
        (message_id,),
    ).fetchone()

    if not row or not row["attachment_path"]:
        return json_error(
            "Attachment not found",
            404,
        )

    # Only the sender or receiver may access the file,
    # and the accepted-application relationship must remain valid.
    other_user_id = (
        row["receiver_id"]
        if row["sender_id"] == user["id"]
        else row["sender_id"]
    )

    if user["id"] not in (
        row["sender_id"],
        row["receiver_id"],
    ):
        return json_error(
            "You are not allowed to access this attachment",
            403,
        )

    if not can_message(
        db,
        user["id"],
        other_user_id,
        row["gig_id"],
    ):
        return json_error(
            "You are not allowed to access this attachment",
            403,
        )

    # attachment_path contains a generated filename,
    # never an arbitrary user-supplied filesystem path.
    file_path = UPLOAD_FOLDER / row["attachment_path"]

    if not file_path.is_file():
        return json_error(
            "The attachment file is missing",
            404,
        )

    response = send_file(
        file_path,
        mimetype=row["attachment_mime"],
        as_attachment=True,
        download_name=row["attachment_name"],
    )

    response.headers["X-Content-Type-Options"] = "nosniff"

    return response