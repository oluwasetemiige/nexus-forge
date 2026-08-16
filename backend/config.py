"""
config.py
---------
Central configuration for Nexus Forge backend.
All settings live here — change them once, they apply everywhere.
"""

import os

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "nexus_forge.db")

# ── App settings ───────────────────────────────────────────────────────────
DEBUG = True
PORT  = 5000
HOST  = "0.0.0.0"

# ── Auth ───────────────────────────────────────────────────────────────────
MIN_PASSWORD_LENGTH = 6

# ── Roles ──────────────────────────────────────────────────────────────────
VALID_ROLES = ("freelancer", "client")
