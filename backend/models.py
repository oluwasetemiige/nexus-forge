"""
models.py
---------
Serializer functions that convert raw SQLite Row objects into
clean Python dicts ready to be returned as JSON.

Keep all data-shaping logic here — routes stay thin.
"""


def user_to_dict(row) -> dict:
    """Serialize a users row. Never exposes password_hash."""
    return {
        "id":          row["id"],
        "name":        row["name"],
        "email":       row["email"],
        "role":        row["role"],
        "is_student":  bool(row["is_student"]),
        "bio":         row["bio"],
        "skills":      row["skills"],
        "nexus_score": row["nexus_score"],
        "created_at":  row["created_at"],
    }


def gig_to_dict(row, client_name: str = None) -> dict:
    """Serialize a gigs row. Optionally include the client's display name."""
    d = {
        "id":               row["id"],
        "client_id":        row["client_id"],
        "title":            row["title"],
        "description":      row["description"],
        "category":         row["category"],
        "budget":           row["budget"],
        "budget_type":      row["budget_type"],
        "deadline":         row["deadline"],
        "status":           row["status"],
        "beginner_friendly": bool(row["beginner_friendly"]),
        "created_at":       row["created_at"],
    }
    if client_name is not None:
        d["client_name"] = client_name
    return d


def application_to_dict(row, include_gig_info: bool = False) -> dict:
    """Serialize an applications row."""
    d = {
        "id":            row["id"],
        "gig_id":        row["gig_id"],
        "freelancer_id": row["freelancer_id"],
        "proposal":      row["proposal"],
        "price":         row["price"],
        "status":        row["status"],
        "created_at":    row["created_at"],
    }
    # Optional extras when joined with gigs
    if include_gig_info:
        d["gig_title"]  = row["gig_title"]
        d["gig_status"] = row["gig_status"]
    # Optional extra when joined with users
    if "freelancer_name" in row.keys():
        d["freelancer_name"] = row["freelancer_name"]
    return d
