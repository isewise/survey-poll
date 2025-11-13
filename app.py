import os
import sqlite3
import hashlib
from datetime import datetime
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    abort,
    jsonify,
)

DB_PATH = os.environ.get("DB_PATH", "votes.db")
RESULTS_KEY = os.environ.get("RESULTS_KEY", "changeme")
QUESTION_TEXT = os.environ.get("QUESTION_TEXT", "Do you support this position?")
SECRET_SALT = os.environ.get("SECRET_SALT", "super_secret_salt")
PUBLIC_VOTE_URL = os.environ.get("PUBLIC_VOTE_URL", "").rstrip("/")


app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            choice TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            user_agent TEXT,
            ip TEXT,
            created_at TEXT NOT NULL
        );
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_fingerprint ON votes(fingerprint);")
    conn.commit()
    conn.close()


with app.app_context():
    init_db()


def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")


def make_fingerprint(ip, user_agent):
    raw = f"{ip}|{user_agent}|{SECRET_SALT}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", question=QUESTION_TEXT)


@app.route("/vote", methods=["POST"])
def vote():
    choice = request.form.get("choice")
    if choice not in ("yes", "no"):
        abort(400, "Invalid choice")

    user_agent = request.headers.get("User-Agent", "")
    ip = get_client_ip()
    fp = make_fingerprint(ip, user_agent)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM votes WHERE fingerprint = ?", (fp,))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return "You’ve already submitted a vote from this device. Thank you!", 200

    cur.execute(
        "INSERT INTO votes (choice, fingerprint, user_agent, ip, created_at) VALUES (?, ?, ?, ?, ?)",
        (choice, fp, user_agent, ip, datetime.utcnow().isoformat() + "Z")
    )
    conn.commit()
    conn.close()
    return redirect(url_for("thanks"))


@app.route("/thanks", methods=["GET"])
def thanks():
    return render_template("thanks.html")


@app.route("/results", methods=["GET"])
def results():
    key = request.args.get("key", "")
    if key != RESULTS_KEY:
        abort(403)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM votes WHERE choice = 'yes'")
    yes_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM votes WHERE choice = 'no'")
    no_count = cur.fetchone()[0]
    cur.execute("SELECT * FROM votes ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()

    total = yes_count + no_count
    return render_template(
        "results.html",
        yes=yes_count,
        no=no_count,
        total=total,
        votes=rows,
        question=QUESTION_TEXT,
    )


@app.route("/stats", methods=["GET"])
def stats():
    key = request.args.get("key", "")
    if key != RESULTS_KEY:
        abort(403)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM votes WHERE choice = 'yes'")
    yes_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM votes WHERE choice = 'no'")
    no_count = cur.fetchone()[0]
    conn.close()

    total = yes_count + no_count
    return jsonify({"yes": yes_count, "no": no_count, "total": total})


@app.route("/dashboard", methods=["GET"])
def dashboard():
    key = request.args.get("key", "")
    if key != RESULTS_KEY:
        abort(403)

    # Prefer the externally reachable URL if provided
    vote_url = (PUBLIC_VOTE_URL + "/") if PUBLIC_VOTE_URL else (request.url_root.rstrip("/") + "/")

    return render_template(
        "dashboard.html",
        question=QUESTION_TEXT,
        vote_url=vote_url,
        results_key=RESULTS_KEY,
    )



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
