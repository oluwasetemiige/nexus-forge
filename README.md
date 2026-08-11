# Nexus Forge — HTML/CSS/JS + Python Prototype

A working prototype of Nexus Forge: plain HTML/CSS/JS frontend, Python (Flask) backend, SQLite database. No build tools, no frameworks — just files you can open and run.

## Structure

```
nexus-forge/
├── backend/
│   ├── app.py              # Flask API (auth, gigs, applications, dashboard)
│   ├── requirements.txt
│   └── nexus_forge.db      # created automatically on first run
└── frontend/
    ├── index.html          # landing / marketing page
    ├── signup.html
    ├── login.html
    ├── browse.html         # gig listings with search + filters
    ├── gig-detail.html     # gig detail, apply, accept/decline applications
    ├── post-gig.html       # client-only: post a new gig
    ├── dashboard.html      # role-aware dashboard (client vs freelancer)
    ├── profile.html
    ├── css/style.css       # shared brand styling (charcoal + molten orange)
    └── js/
        ├── api.js          # fetch wrapper + auth/token handling
        └── nav.js          # shared navbar, auth-aware
```

## Running it

**1. Start the backend**

```bash
cd backend
pip install -r requirements.txt
python app.py
```

This starts the API at `http://localhost:5000` and creates `nexus_forge.db` automatically the first time you run it.

**2. Open the frontend**

Just open `frontend/index.html` directly in your browser, or serve it with a simple static server (recommended, avoids some browser file:// quirks):

```bash
cd frontend
python -m http.server 8000
```

Then visit `http://localhost:8000`.

> The frontend calls the API at `http://localhost:5000/api` — that's set in `frontend/js/api.js` as `API_BASE`. Change it there if you deploy the backend elsewhere.

## What's implemented

- **Auth**: signup/login with hashed passwords (Werkzeug), token-based sessions stored in `localStorage`
- **Roles**: freelancer vs client, different dashboard and permissions
- **Gigs**: post, browse (search + category + beginner-friendly filter), view detail
- **Applications**: freelancers apply with a proposal + price; clients accept/decline from the gig detail page
- **Dashboard**: stats + your gigs (client) or your applications (freelancer)
- **Student Verification badge**, **Nexus Score** (starts at 50), **Beginner Friendly** gig tagging

## What's stubbed / not yet built

- Payments (Paystack/Flutterwave/Stripe) — not wired up, this is UI + data model only
- Escrow flow — gig `status` field supports it (`open → in_progress → completed`) but no payment holding logic
- Messaging between client/freelancer
- Skill Quizzes, Dispute Shield workflow
- Profile editing (currently read-only)

These are natural next slices to build once you want to go deeper on any one of them.

## Notes

- Database is SQLite — zero setup, but not meant for concurrent production use. Swapping to Postgres later just means changing the `sqlite3` calls in `app.py`.
- CORS is handled manually in `app.py` (no `flask-cors` dependency) so it works out of the box.
