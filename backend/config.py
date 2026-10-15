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
# Debug mode exposes an interactive debugger, so it is OFF by default.
# Turn it on locally with:  NF_DEBUG=1 python app.py
DEBUG = os.environ.get("NF_DEBUG") == "1"
PORT  = 5000
# Localhost only by default. Set NF_HOST=0.0.0.0 to expose it on your network.
HOST  = os.environ.get("NF_HOST", "127.0.0.1")

# ── Auth ───────────────────────────────────────────────────────────────────
MIN_PASSWORD_LENGTH = 6

# ── Roles ──────────────────────────────────────────────────────────────────
VALID_ROLES = ("freelancer", "client")
