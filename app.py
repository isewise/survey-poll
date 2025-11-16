import os
import sqlite3
import hashlib
import csv
import io
import boto3
import time
from datetime import datetime, timedelta
from collections import defaultdict
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    abort,
    jsonify,
    make_response,
    session,
)

DB_PATH = os.getenv("DB_PATH", "/app/votes.db")
RESULTS_KEY = os.getenv("RESULTS_KEY", "changeme")
QUESTION_TEXT = os.getenv("QUESTION_TEXT", "Do you support this position?")
SECRET_SALT = os.getenv("SECRET_SALT", "super_secret_salt")
PUBLIC_VOTE_URL = os.getenv("PUBLIC_VOTE_URL", "").rstrip("/")

# Security Configuration
ADMIN_SESSION_TIMEOUT = int(os.getenv("ADMIN_SESSION_TIMEOUT", "3600"))  # 1 hour
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "900"))  # 15 minutes

# Rate limiting storage
failed_attempts = defaultdict(list)
blocked_ips = {}

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_KEY = os.getenv("S3_KEY", "survey-poll/votes.db")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize S3 client if bucket is configured
s3_client = None
if S3_BUCKET:
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
    except Exception as e:
        print(f"Warning: Could not initialize S3 client: {e}")


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", SECRET_SALT)  # Use for sessions


def check_rate_limit(ip):
    """Check if IP is rate limited"""
    current_time = time.time()
    
    # Check if IP is currently blocked
    if ip in blocked_ips:
        if current_time < blocked_ips[ip]:
            return False  # Still blocked
        else:
            del blocked_ips[ip]  # Unblock expired block
    
    # Clean old failed attempts
    failed_attempts[ip] = [
        attempt_time for attempt_time in failed_attempts[ip]
        if current_time - attempt_time < RATE_LIMIT_WINDOW
    ]
    
    # Check if too many attempts
    if len(failed_attempts[ip]) >= MAX_LOGIN_ATTEMPTS:
        blocked_ips[ip] = current_time + RATE_LIMIT_WINDOW  # Block for 15 minutes
        return False
    
    return True


def record_failed_attempt(ip):
    """Record a failed login attempt"""
    failed_attempts[ip].append(time.time())


def is_admin_authenticated():
    """Check if current session is authenticated as admin"""
    if 'admin_authenticated' not in session:
        return False
    
    if 'admin_login_time' not in session:
        return False
    
    # Check session timeout
    login_time = session['admin_login_time']
    if time.time() - login_time > ADMIN_SESSION_TIMEOUT:
        session.clear()
        return False
    
    return session['admin_authenticated']


def require_admin_auth():
    """Decorator-like function to check admin authentication"""
    ip = get_client_ip()
    
    # Check rate limiting first
    if not check_rate_limit(ip):
        abort(429, "Too many failed attempts. Try again later.")
    
    # Check session authentication
    if is_admin_authenticated():
        return True
    
    # Check if key is provided in request
    key = request.args.get("key", "") or request.form.get("key", "")
    if key == RESULTS_KEY:
        # Valid key - create session
        session['admin_authenticated'] = True
        session['admin_login_time'] = time.time()
        session.permanent = True
        return True
    elif key:  # Wrong key provided
        record_failed_attempt(ip)
        abort(403, "Invalid authentication key")
    
    # No authentication
    abort(403, "Authentication required")


def backup_db_to_s3():
    """Backup database to S3"""
    if not s3_client or not S3_BUCKET:
        print("S3 not configured, skipping backup")
        return False
    
    try:
        if os.path.exists(DB_PATH):
            s3_client.upload_file(DB_PATH, S3_BUCKET, S3_KEY)
            print(f"Database backed up to s3://{S3_BUCKET}/{S3_KEY}")
            return True
        else:
            print("No database file to backup")
            return False
    except Exception as e:
        print(f"Failed to backup database to S3: {e}")
        return False


def restore_db_from_s3():
    """Restore database from S3 if it exists"""
    if not s3_client or not S3_BUCKET:
        print("S3 not configured, skipping restore")
        return False
    
    try:
        # Check if backup exists
        s3_client.head_object(Bucket=S3_BUCKET, Key=S3_KEY)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Download the backup
        s3_client.download_file(S3_BUCKET, S3_KEY, DB_PATH)
        print(f"Database restored from s3://{S3_BUCKET}/{S3_KEY}")
        return True
    except s3_client.exceptions.NoSuchKey:
        print("No backup found in S3, will create new database")
        return False
    except Exception as e:
        print(f"Failed to restore database from S3: {e}")
        return False


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # Try to restore from S3 first
    restore_db_from_s3()
    
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
    
    # Backup to S3 after new vote
    backup_db_to_s3()
    
    return redirect(url_for("thanks"))


@app.route("/thanks", methods=["GET"])
def thanks():
    return render_template("thanks.html")


@app.route("/results", methods=["GET"])
def results():
    require_admin_auth()

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
    require_admin_auth()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM votes WHERE choice = 'yes'")
    yes_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM votes WHERE choice = 'no'")
    no_count = cur.fetchone()[0]
    conn.close()

    total = yes_count + no_count
    return jsonify({"yes": yes_count, "no": no_count, "total": total})


@app.route("/preview", methods=["GET"])
def preview():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM votes WHERE choice = 'yes'")
    yes_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM votes WHERE choice = 'no'")
    no_count = cur.fetchone()[0]
    cur.execute("SELECT choice, created_at FROM votes ORDER BY created_at DESC LIMIT 10")
    recent_votes = cur.fetchall()
    conn.close()

    total = yes_count + no_count
    return render_template(
        "preview.html",
        yes=yes_count,
        no=no_count,
        total=total,
        recent_votes=recent_votes,
        question=QUESTION_TEXT,
    )

@app.route("/dashboard", methods=["GET"])
def dashboard():
    require_admin_auth()

    # Prefer the externally reachable URL if provided
    vote_url = (PUBLIC_VOTE_URL + "/") if PUBLIC_VOTE_URL else (request.url_root.rstrip("/") + "/")

    return render_template(
        "dashboard.html",
        question=QUESTION_TEXT,
        vote_url=vote_url,
    )


@app.route("/export", methods=["GET"])
def export_data():
    require_admin_auth()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, choice, ip, user_agent, created_at FROM votes ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()

    # Create CSV output
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["ID", "Choice", "IP Address", "User Agent", "Created At"])
    
    # Write data
    for row in rows:
        writer.writerow([row[0], row[1], row[2], row[3], row[4]])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = f"attachment; filename=poll_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return response


@app.route("/reset", methods=["POST"])
def reset_database():
    require_admin_auth()
    
    confirm = request.form.get("confirm", "")
    
    if confirm != "DELETE_ALL_VOTES":
        return redirect(url_for("dashboard", error="confirmation_failed"))
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM votes")
    deleted_count = cur.rowcount
    conn.commit()
    conn.close()
    
    # Backup to S3 after reset (empty database)
    backup_db_to_s3()
    
    return redirect(url_for("dashboard", reset="success", deleted=deleted_count))


@app.route("/backup", methods=["POST"])
def manual_backup():
    require_admin_auth()
    
    if backup_db_to_s3():
        return redirect(url_for("dashboard", backup="success"))
    else:
        return redirect(url_for("dashboard", backup="failed"))


@app.route("/logout", methods=["POST", "GET"])
def logout():
    """Logout admin user"""
    session.clear()
    return redirect(url_for("index"))



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
