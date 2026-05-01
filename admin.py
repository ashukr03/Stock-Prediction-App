"""
admin.py — Admin Panel for Stock Market Prediction
Run with:  streamlit run admin.py
Access at: http://localhost:8502
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from auth import (
    init_db, get_all_users, get_verified_emails, get_notifications,
    send_email, log_notification, get_user, SMTP_SENDER, APP_NAME
)

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Stock Pro — Admin",
    page_icon="🛡️",
    layout="wide"
)

init_db()

# ── CUSTOM CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
  font-family: 'Syne', sans-serif;
  background: #05080f;
  color: #dde6f5;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: #080d18 !important;
  border-right: 1px solid #1a2d4a !important;
}

/* KPI Cards */
.kpi-grid { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.kpi-box {
  background: #0d1526; border: 1px solid #1a2d4a; border-radius: 12px;
  padding: 1.2rem 1.8rem; flex: 1; min-width: 160px;
}
.kpi-box .num { font-size: 2rem; font-weight: 800; }
.kpi-box .lbl { font-size: .75rem; color: #4a6a90; text-transform: uppercase; letter-spacing: .08em; margin-top: .2rem; }
.c-blue   { color: #00d4ff; }
.c-green  { color: #00e676; }
.c-gold   { color: #ffc107; }
.c-purple { color: #d580ff; }

/* Section title */
.sec-title {
  font-size: 1.1rem; font-weight: 700; color: #00d4ff;
  border-left: 3px solid #00d4ff; padding-left: .7rem;
  margin: 1.5rem 0 1rem;
}

/* Table tweaks */
.stDataFrame { border: 1px solid #1a2d4a; border-radius: 10px; overflow: hidden; }

/* Email composer */
.composer {
  background: #0d1526; border: 1px solid #1a2d4a;
  border-radius: 14px; padding: 1.8rem;
}

/* Badge */
.badge {
  display: inline-block;
  padding: .15rem .6rem; border-radius: 20px; font-size: .72rem; font-weight: 700;
}
.badge-admin { background: rgba(213,128,255,.15); color: #d580ff; border: 1px solid rgba(213,128,255,.3); }
.badge-user  { background: rgba(0,212,255,.1);   color: #00d4ff; border: 1px solid rgba(0,212,255,.25); }
.badge-ok    { background: rgba(0,230,118,.1);   color: #00e676; border: 1px solid rgba(0,230,118,.25); }
</style>
""", unsafe_allow_html=True)

# ── ADMIN AUTH ────────────────────────────────────────────────────────────────
# Simple admin session — uses the same SMTP_SENDER as admin identity
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if not st.session_state["admin_logged_in"]:
    st.markdown("## 🛡️ Admin Login")
    st.caption("Enter the admin email and OTP from Gmail to access the panel.")

    from auth import generate_otp, store_otp, verify_otp, clear_otp

    admin_email = st.text_input("Admin Gmail", value=SMTP_SENDER)
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Send OTP", use_container_width=True):
            admin_user = get_user(admin_email)
            if not admin_user or admin_user.get("role") != "admin":
                st.error("Not an admin account.")
            else:
                from auth import otp_email_html
                otp = generate_otp()
                store_otp(admin_email, otp, "admin_login", "Admin")
                ok = send_email(admin_email, f"{APP_NAME} Admin OTP", otp_email_html("Admin", otp, "login"))
                if ok:
                    st.success("OTP sent ✓")
                    st.session_state["admin_pending_email"] = admin_email
                else:
                    # Fallback: show OTP directly for local dev
                    st.info(f"[DEV MODE] OTP: {otp}")
                    st.session_state["admin_pending_email"] = admin_email

    if st.session_state.get("admin_pending_email"):
        otp_inp = st.text_input("Enter OTP", max_chars=6, placeholder="000000")
        if st.button("Verify & Enter", use_container_width=True):
            ok, _ = verify_otp(st.session_state["admin_pending_email"], otp_inp, "admin_login")
            if ok:
                clear_otp(st.session_state["admin_pending_email"])
                st.session_state["admin_logged_in"] = True
                st.session_state["admin_email"] = st.session_state["admin_pending_email"]
                st.rerun()
            else:
                st.error(_)
    st.stop()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ Admin Panel")
    st.markdown(f"**{st.session_state.get('admin_email', SMTP_SENDER)}**")
    st.caption(f"AI Stock Pro — Admin Console")
    st.divider()
    page = st.radio("Navigate", ["📊 Dashboard", "👥 Users", "📧 Send Notification", "📜 History"])
    st.divider()
    if st.button("🚪 Logout"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

# ── LOAD DATA ──────────────────────────────────────────────────────────────────
all_users      = get_all_users()
verified_emails = get_verified_emails()
notifications  = get_notifications()

total_users    = len([u for u in all_users if u["role"] == "user"])
verified_users = len([u for u in all_users if u["verified"] == 1 and u["role"] == "user"])
total_notifs   = len(notifications)
emails_sent    = sum(n["recipients"] for n in notifications)


# ══════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown("# 📊 Admin Dashboard")
    st.caption(f"Last refreshed: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}")

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-box"><div class="num c-blue">{total_users}</div><div class="lbl">Total Users</div></div>
      <div class="kpi-box"><div class="num c-green">{verified_users}</div><div class="lbl">Verified Users</div></div>
      <div class="kpi-box"><div class="num c-gold">{total_notifs}</div><div class="lbl">Notifications Sent</div></div>
      <div class="kpi-box"><div class="num c-purple">{emails_sent}</div><div class="lbl">Emails Delivered</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec-title">Recent Signups</div>', unsafe_allow_html=True)
    recent = [u for u in all_users if u["role"] == "user"][:10]
    if recent:
        df_recent = pd.DataFrame(recent)[["name", "email", "verified", "created_at", "last_login"]]
        df_recent["verified"] = df_recent["verified"].map({1: "✅ Yes", 0: "❌ No"})
        df_recent.columns = ["Name", "Email", "Verified", "Joined", "Last Login"]
        st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.info("No users yet.")

    st.markdown('<div class="sec-title">Recent Notifications</div>', unsafe_allow_html=True)
    if notifications:
        df_notifs = pd.DataFrame(notifications[:5])[["subject", "recipients", "sent_at"]]
        df_notifs.columns = ["Subject", "Recipients", "Sent At"]
        st.dataframe(df_notifs, use_container_width=True, hide_index=True)
    else:
        st.info("No notifications sent yet.")


# ══════════════════════════════════════════════════════════
# PAGE: USERS
# ══════════════════════════════════════════════════════════
elif page == "👥 Users":
    st.markdown("# 👥 Registered Users")

    search = st.text_input("🔍 Search by name or email", placeholder="Type to filter…")
    users_filtered = [
        u for u in all_users
        if search.lower() in u["name"].lower() or search.lower() in u["email"].lower()
    ] if search else all_users

    st.caption(f"Showing {len(users_filtered)} of {len(all_users)} total accounts")

    if users_filtered:
        rows = []
        for u in users_filtered:
            rows.append({
                "Name":       u["name"],
                "Email":      u["email"],
                "Role":       u["role"].upper(),
                "Verified":   "✅" if u["verified"] else "❌",
                "Joined":     u["created_at"][:16] if u["created_at"] else "—",
                "Last Login": u["last_login"][:16] if u["last_login"] else "Never",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No users match the search.")

    st.divider()
    st.markdown('<div class="sec-title">📤 Send Individual Email</div>', unsafe_allow_html=True)
    user_emails = [u["email"] for u in all_users if u["role"] == "user"]
    if user_emails:
        target = st.selectbox("Select user", user_emails)
        ind_subject = st.text_input("Subject", placeholder="Your account update")
        ind_body    = st.text_area("Message (plain text)", height=120, placeholder="Dear user…")
        if st.button("Send to this user"):
            if ind_subject and ind_body:
                target_user = get_user(target)
                html = _individual_email_html(target_user["name"], ind_body)
                ok = send_email(target, ind_subject, html)
                if ok:
                    log_notification(ind_subject, ind_body, st.session_state["admin_email"], 1)
                    st.success(f"Email sent to {target} ✓")
                else:
                    st.error("Failed. Check SMTP config.")
            else:
                st.warning("Fill in subject and message.")
    else:
        st.info("No users to email yet.")


# ══════════════════════════════════════════════════════════
# PAGE: SEND NOTIFICATION
# ══════════════════════════════════════════════════════════
elif page == "📧 Send Notification":
    st.markdown("# 📧 Broadcast Notification")

    st.markdown(f"""
    <div style="background:rgba(0,212,255,.06);border:1px solid rgba(0,212,255,.2);
         border-radius:10px;padding:1rem 1.2rem;margin-bottom:1.5rem;font-size:.88rem;color:#7a9cc8;">
      📡 This will send an email to <strong style="color:#00d4ff;">{len(verified_emails)} verified users</strong>.
      Use for market alerts, platform updates, important announcements.
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        # Template picker
        template = st.selectbox("Quick Template", [
            "— Custom message —",
            "📈 Market Alert — Significant movement detected",
            "🔔 Weekly Digest — Top movers this week",
            "⚠️ Volatility Warning — High VIX detected",
            "🚀 New Feature — Platform update",
            "📉 Market Correction Notice",
        ])

        subject = st.text_input("Email Subject *", value=template if template != "— Custom message —" else "",
                                placeholder="e.g. 📈 Market Alert: NVDA +8% Today")

        body_html_mode = st.checkbox("Use HTML body (for rich formatting)", value=False)

        if body_html_mode:
            body = st.text_area("Email Body (HTML)", height=200,
                                placeholder="<p>Dear <strong>{name}</strong>,</p><p>Your message here...</p>")
            st.caption("Use {name} as a placeholder — it will be replaced with each user's name.")
        else:
            body = st.text_area("Email Body (Plain Text)", height=200,
                                placeholder="Write your message here. You can use {name} as a placeholder for the recipient's name.")

        # Preview
        preview_name = "Rahul"
        if st.checkbox("Preview email"):
            preview_body = body.replace("{name}", preview_name)
            if body_html_mode:
                final_preview = _broadcast_email_html(preview_name, subject, preview_body, is_html=True)
            else:
                final_preview = _broadcast_email_html(preview_name, subject, preview_body, is_html=False)
            with st.expander("Email Preview", expanded=True):
                st.components.v1.html(final_preview, height=400, scrolling=True)

        col_send, col_test = st.columns([1, 1])
        with col_test:
            test_email = st.text_input("Send test to", placeholder="your@gmail.com")
            if st.button("Send Test Email"):
                if not test_email or "@" not in test_email:
                    st.error("Enter a valid test email.")
                elif not subject or not body:
                    st.error("Fill subject and body first.")
                else:
                    body_rendered = body.replace("{name}", "Test User")
                    html = _broadcast_email_html("Test User", subject, body_rendered, is_html=body_html_mode)
                    ok = send_email(test_email, f"[TEST] {subject}", html)
                    st.success("Test email sent ✓") if ok else st.error("Send failed.")

        with col_send:
            st.write("")
            st.write("")
            if st.button("🚀 Send to ALL Users", type="primary", use_container_width=True):
                if not subject or not body:
                    st.error("Subject and body are required.")
                elif not verified_emails:
                    st.warning("No verified users to send to.")
                else:
                    success_count = 0
                    fail_count    = 0
                    progress = st.progress(0, text="Sending emails…")

                    for i, email in enumerate(verified_emails):
                        user = get_user(email)
                        uname = user["name"] if user else "Valued User"
                        body_rendered = body.replace("{name}", uname)
                        html = _broadcast_email_html(uname, subject, body_rendered, is_html=body_html_mode)
                        ok = send_email(email, subject, html)
                        if ok: success_count += 1
                        else:  fail_count    += 1
                        progress.progress((i+1)/len(verified_emails), text=f"Sending… {i+1}/{len(verified_emails)}")

                    log_notification(subject, body, st.session_state["admin_email"], success_count)
                    progress.empty()
                    st.success(f"✅ Sent to {success_count} users. {f'⚠️ {fail_count} failed.' if fail_count else ''}")


# ══════════════════════════════════════════════════════════
# PAGE: HISTORY
# ══════════════════════════════════════════════════════════
elif page == "📜 History":
    st.markdown("# 📜 Notification History")

    if notifications:
        for n in notifications:
            with st.expander(f"📧 {n['subject']} — {n['sent_at'][:16]}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Recipients", n["recipients"])
                col2.metric("Sent At", n["sent_at"][:16])
                col3.metric("By", n["sent_by"][:25])
                st.markdown("**Message Preview:**")
                st.markdown(f"```\n{n['body'][:500]}\n```")
    else:
        st.info("No notifications sent yet.")


# ── EMAIL TEMPLATE HELPERS ─────────────────────────────────────────────────────
def _broadcast_email_html(name: str, subject: str, body: str, is_html: bool = False) -> str:
    body_content = body if is_html else body.replace("\n", "<br>")
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#05080f;font-family:'Segoe UI',sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
        <tr><td align="center">
          <table width="520" cellpadding="0" cellspacing="0"
                 style="background:#0d1526;border:1px solid #1a2d4a;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="background:linear-gradient(135deg,#001f3f,#0a2540);padding:28px 32px;">
                <div style="font-size:1.4rem;font-weight:800;color:#00d4ff;">📈 AI Stock Pro</div>
                <div style="color:#4a6a90;font-size:.75rem;margin-top:.2rem;letter-spacing:.08em;text-transform:uppercase;">
                  Market Intelligence · Admin Bulletin
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:32px 40px;">
                <h2 style="color:#dde6f5;font-size:1.15rem;margin:0 0 1.2rem;">{subject}</h2>
                <p style="color:#7a9cc8;font-size:.88rem;margin:0 0 1.2rem;">Hi {name},</p>
                <div style="color:#dde6f5;font-size:.9rem;line-height:1.75;">{body_content}</div>
              </td>
            </tr>
            <tr>
              <td style="background:#080d18;padding:16px 40px;text-align:center;">
                <a href="http://localhost:8501" style="color:#00d4ff;font-size:.8rem;text-decoration:none;">
                  Open AI Stock Pro Dashboard
                </a>
                <p style="color:#2a3d55;font-size:.7rem;margin:.5rem 0 0;">
                  You're receiving this as a registered AI Stock Pro user.
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def _individual_email_html(name: str, body: str) -> str:
    return _broadcast_email_html(name, "Message from AI Stock Pro Admin", body, is_html=False)