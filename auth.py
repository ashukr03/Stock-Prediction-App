"""
auth.py — Authentication module for Stock Market Prediction
Handles: user registration, OTP via Gmail SMTP, login, session management
Database: SQLite (users.db) — zero cost, no external service needed
"""

import sqlite3
import random
import hashlib
import smtplib
import string
import time
import os
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# ── CONFIG (fill in your Gmail app password) ──────────────────────────────────
SMTP_SENDER  = os.getenv("SMTP_SENDER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
# To get App Password: Google Account → Security → 2-Step Verification → App Passwords
APP_NAME     = "AI Stock Pro"
DB_PATH      = "users.db"
OTP_EXPIRY_SECONDS = 600  # 10 minutes


# ── PASSWORD HELPERS ───────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a static salt."""
    return hashlib.sha256((password + "AI_STOCK_PRO_SALT").encode()).hexdigest()

def check_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == password_hash


# ── DATABASE SETUP ─────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    DEFAULT '',
            verified      INTEGER DEFAULT 0,
            role          TEXT    DEFAULT 'user',
            created_at    TEXT    DEFAULT (datetime('now')),
            last_login    TEXT
        )
    """)

    # Add password_hash column if missing (migration for existing DBs)
    try:
        c.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists

    c.execute("""
        CREATE TABLE IF NOT EXISTS otps (
            email      TEXT PRIMARY KEY,
            otp        TEXT NOT NULL,
            purpose    TEXT NOT NULL,
            expires_at REAL NOT NULL,
            name       TEXT,
            password_hash TEXT DEFAULT ''
        )
    """)

    # Add password_hash column to otps if missing (migration for existing DBs)
    try:
        c.execute("ALTER TABLE otps ADD COLUMN password_hash TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            subject    TEXT NOT NULL,
            body       TEXT NOT NULL,
            sent_by    TEXT NOT NULL,
            sent_at    TEXT DEFAULT (datetime('now')),
            recipients INTEGER DEFAULT 0
        )
    """)

    # Create default admin if none exists
    admin_pw_hash = hash_password("admin123")
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT OR IGNORE INTO users (name, email, password_hash, verified, role)
            VALUES (?, ?, ?, 1, 'admin')
        """, ("Admin", SMTP_SENDER, admin_pw_hash))

    conn.commit()
    conn.close()


# ── OTP HELPERS ────────────────────────────────────────────────────────────────
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def store_otp(email: str, otp: str, purpose: str, name: str = "", password_hash: str = ""):
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO otps (email, otp, purpose, expires_at, name, password_hash)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email.lower(), otp, purpose, time.time() + OTP_EXPIRY_SECONDS, name, password_hash))
    conn.commit()
    conn.close()

def verify_otp(email: str, otp_input: str, purpose: str):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM otps WHERE email=? AND purpose=?",
        (email.lower(), purpose)
    ).fetchone()
    conn.close()

    if not row:
        return False, "No OTP found. Please request a new one.", ""
    if time.time() > row["expires_at"]:
        return False, "OTP expired. Please request a new one.", ""
    if row["otp"] != otp_input.strip():
        return False, "Incorrect OTP. Please try again.", ""
    return True, row["name"], row["password_hash"]

def clear_otp(email: str):
    conn = get_db()
    conn.execute("DELETE FROM otps WHERE email=?", (email.lower(),))
    conn.commit()
    conn.close()


# ── EMAIL SENDER ───────────────────────────────────────────────────────────────
def send_email(to_email: str, subject: str, html_body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{APP_NAME} <{SMTP_SENDER}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(SMTP_SENDER, SMTP_PASSWORD)
            server.sendmail(SMTP_SENDER, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email error: {e}")
        return False


def otp_email_html(name: str, otp: str, purpose: str) -> str:
    action = "verify your email and complete signup" if purpose == "signup" else "log in to your account"
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#05080f;font-family:'Segoe UI',sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
        <tr><td align="center">
          <table width="520" cellpadding="0" cellspacing="0"
                 style="background:#0d1526;border:1px solid #1a2d4a;border-radius:16px;overflow:hidden;">
            <!-- Header -->
            <tr>
              <td style="background:linear-gradient(135deg,#001f3f,#0a2540);padding:32px;text-align:center;">
                <div style="font-size:1.6rem;font-weight:800;color:#00d4ff;letter-spacing:-.02em;">
                  📈 AI Stock Pro
                </div>
                <div style="color:#4a6a90;font-size:.8rem;margin-top:.3rem;letter-spacing:.08em;text-transform:uppercase;">
                  Market Intelligence Platform
                </div>
              </td>
            </tr>
            <!-- Body -->
            <tr>
              <td style="padding:36px 40px;">
                <p style="color:#dde6f5;font-size:1rem;margin:0 0 .5rem;">Hi {name or 'there'},</p>
                <p style="color:#7a9cc8;font-size:.9rem;line-height:1.7;margin:0 0 2rem;">
                  Use the OTP below to {action}. It expires in <strong style="color:#ffc107;">10 minutes</strong>.
                </p>
                <!-- OTP Box -->
                <div style="text-align:center;margin:2rem 0;">
                  <div style="display:inline-block;background:#05080f;border:2px solid #00d4ff;
                              border-radius:14px;padding:1.2rem 3rem;">
                    <div style="letter-spacing:.5em;font-size:2.4rem;font-weight:800;
                                color:#00d4ff;font-family:'Courier New',monospace;">
                      {otp}
                    </div>
                    <div style="color:#4a6a90;font-size:.72rem;margin-top:.4rem;letter-spacing:.1em;
                                text-transform:uppercase;">
                      One-Time Password
                    </div>
                  </div>
                </div>
                <p style="color:#4a6a90;font-size:.78rem;line-height:1.6;margin:1.5rem 0 0;
                           border-top:1px solid #1a2d4a;padding-top:1.2rem;">
                  If you didn't request this, you can safely ignore this email.
                  Never share your OTP with anyone.
                </p>
              </td>
            </tr>
            <!-- Footer -->
            <tr>
              <td style="background:#080d18;padding:16px 40px;text-align:center;">
                <p style="color:#2a3d55;font-size:.72rem;margin:0;">
                  © {datetime.now().year} AI Stock Pro · Educational use only · Not financial advice
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


# ── USER CRUD ──────────────────────────────────────────────────────────────────
def user_exists(email: str) -> bool:
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email=?", (email.lower(),)).fetchone()
    conn.close()
    return row is not None

def register_user(name: str, email: str, password_hash: str = ""):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash, verified) VALUES (?, ?, ?, 1)",
        (name.strip(), email.lower(), password_hash)
    )
    conn.commit()
    conn.close()

def get_user(email: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email.lower(),)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_last_login(email: str):
    conn = get_db()
    conn.execute("UPDATE users SET last_login=datetime('now') WHERE email=?", (email.lower(),))
    conn.commit()
    conn.close()

def update_password(email: str, new_password: str):
    """Update user's password hash in the database."""
    pw_hash = hash_password(new_password)
    conn = get_db()
    conn.execute("UPDATE users SET password_hash=? WHERE email=?", (pw_hash, email.lower()))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_verified_emails():
    conn = get_db()
    rows = conn.execute("SELECT email FROM users WHERE verified=1 AND role='user'").fetchall()
    conn.close()
    return [r["email"] for r in rows]

def log_notification(subject: str, body: str, sent_by: str, recipients: int):
    conn = get_db()
    conn.execute(
        "INSERT INTO notifications (subject, body, sent_by, recipients) VALUES (?,?,?,?)",
        (subject, body, sent_by, recipients)
    )
    conn.commit()
    conn.close()

def get_notifications():
    conn = get_db()
    rows = conn.execute("SELECT * FROM notifications ORDER BY sent_at DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(r) for r in rows]




def _welcome_email_html(name: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#05080f;font-family:'Segoe UI',sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
        <tr><td align="center">
          <table width="520" cellpadding="0" cellspacing="0"
                 style="background:#0d1526;border:1px solid #1a2d4a;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="background:linear-gradient(135deg,#001f3f,#0a2540);padding:32px;text-align:center;">
                <div style="font-size:2rem;margin-bottom:.5rem;">🚀</div>
                <div style="font-size:1.6rem;font-weight:800;color:#00d4ff;">Welcome to AI Stock Pro</div>
              </td>
            </tr>
            <tr>
              <td style="padding:36px 40px;">
                <p style="color:#dde6f5;font-size:1rem;margin:0 0 1rem;">Hi {name},</p>
                <p style="color:#7a9cc8;font-size:.9rem;line-height:1.7;margin:0 0 1.5rem;">
                  Your account is now active. Here's what you can do:
                </p>
                <ul style="color:#7a9cc8;font-size:.88rem;line-height:2;padding-left:1.2rem;">
                  <li>📈 AI-powered LSTM price predictions</li>
                  <li>📰 Live news sentiment analysis</li>
                  <li>🌐 Sector-wise growth tracking</li>
                  <li>📊 Real-time financials & balance sheets</li>
                  <li>⚡ Volatility & risk metrics</li>
                </ul>
                <div style="text-align:center;margin:2rem 0;">
                  <a href="http://localhost:8501" style="background:#00d4ff;color:#05080f;
                     padding:.8rem 2rem;border-radius:8px;text-decoration:none;
                     font-weight:700;font-size:.95rem;">Open Dashboard →</a>
                </div>
              </td>
            </tr>
            <tr>
              <td style="background:#080d18;padding:16px 40px;text-align:center;">
                <p style="color:#2a3d55;font-size:.72rem;margin:0;">
                  © {datetime.now().year} AI Stock Pro · Not financial advice
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

