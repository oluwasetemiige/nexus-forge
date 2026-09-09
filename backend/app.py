"""
app.py
------
Nexus Forge — Backend entry point.

All it does:
  1. Create the Flask app
  2. Register CORS
  3. Register all Blueprints
  4. Wire the DB teardown hook
  5. Run

Nothing else lives here. Business logic belongs in routes/ and helpers.

Run:
    pip install -r requirements.txt
    python app.py
"""

from flask import Flask, make_response,request,jsonify
from config import DEBUG, HOST, PORT
from database import init_db, close_db
from routes.auth_routes        import auth_bp, login
from routes.gig_routes         import gig_bp
from routes.application_routes import application_bp
from routes.dashboard_routes   import dashboard_bp
from routes.message_route import message_bp



# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> Flask:
    app = Flask(__name__)

    # ── CORS (no external library needed) ───────────────────────────────────
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"]  = "http://localhost:8000"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @app.route("/api/<path:_any>", methods=["OPTIONS"])
    def cors_preflight(_any):
        return "", 204

    # ── DB teardown ──────────────────────────────────────────────────────────
    app.teardown_appcontext(close_db)

    # ── Blueprints ───────────────────────────────────────────────────────────
    url = "/api"
    app.register_blueprint(auth_bp,        url_prefix=url)
    app.register_blueprint(gig_bp,         url_prefix=url)
    app.register_blueprint(application_bp, url_prefix=url)
    app.register_blueprint(dashboard_bp,   url_prefix=url)
    app.register_blueprint(message_bp,     url_prefix=url)

    return app


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
app = create_app()
print(app.url_map)

if __name__ == "__main__":
    init_db()
    print(f"Nexus Forge API  →  http://{HOST}:{PORT}")
    app.run(debug=DEBUG, host=HOST, port=PORT)
