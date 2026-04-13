"""
web_api.py — User management REST API built with Flask + SQLite.
Handles account creation, login, profile updates, and image proxying.
"""

import sqlite3
import hashlib
import urllib.request
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)
DB_PATH = "users.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def validate_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1]


def normalize_username(username: str) -> str:
    return username.strip().lower()


# ------------------------------------------------------------------ #
# VULNERABILITY 1: SQL Injection (line ~37)
# User input is concatenated directly into the SQL query string.
# ------------------------------------------------------------------ #
@app.route("/api/users/search")
def search_users():
    query = request.args.get("q", "")
    conn = get_db()
    # Dangerous: unsanitised `query` is injected directly into SQL
    sql = f"SELECT id, username, email FROM users WHERE username LIKE '%{query}%'"
    results = conn.execute(sql).fetchall()
    conn.close()
    return jsonify([dict(r) for r in results])


@app.route("/api/users/<int:user_id>")
def get_user(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, email, bio FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


# ------------------------------------------------------------------ #
# VULNERABILITY 2: Stored XSS — bio is stored raw and returned
# without sanitisation; any HTML/JS in bio will execute in the browser.
# ------------------------------------------------------------------ #
@app.route("/api/users/<int:user_id>/profile", methods=["PUT"])
def update_profile(user_id):
    data = request.get_json()
    bio = data.get("bio", "")
    # No sanitisation — raw HTML/JS stored directly
    conn = get_db()
    conn.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})


@app.route("/api/users/<int:user_id>/avatar")
def get_avatar(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT avatar_url FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({"url": row["avatar_url"]})


# ------------------------------------------------------------------ #
# VULNERABILITY 3: SSRF — the `url` param is fetched server-side with
# no allowlist; attackers can target internal services (e.g. metadata API).
# ------------------------------------------------------------------ #
@app.route("/api/proxy/image")
def proxy_image():
    url = request.args.get("url", "")
    # Dangerous: fetches arbitrary URLs — enables SSRF
    with urllib.request.urlopen(url) as response:
        data = response.read()
    return data, 200, {"Content-Type": "image/jpeg"}


# ------------------------------------------------------------------ #
# VULNERABILITY 4: Open Redirect — destination is taken directly from
# user input; attackers craft phishing links via this endpoint.
# ------------------------------------------------------------------ #
@app.route("/login/callback")
def login_callback():
    token = request.args.get("token")
    next_url = request.args.get("next", "/dashboard")
    if not token:
        return jsonify({"error": "missing token"}), 400
    # Dangerous: redirects to attacker-controlled URL with no validation
    return redirect(next_url)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/stats")
def stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return jsonify({"total_users": total})


def create_tables():
    conn = get_db()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            bio TEXT DEFAULT '',
            avatar_url TEXT DEFAULT ''
        )"""
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
