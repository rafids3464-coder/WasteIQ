"""
WASTE IQ – Login / Signup Page
Single-process architecture (No FastAPI)
"""

import streamlit as st
import requests
import os
from firebase_admin import auth as admin_auth
from backend.firestore_client import set_doc, get_doc
from languages import t, LANGUAGE_NAMES

FIREBASE_KEY = os.getenv("FIREBASE_API_KEY", "")


# ─────────────────────────────────────────────
# Firebase REST Login
# ─────────────────────────────────────────────
def _sign_in(email: str, password: str) -> dict:
    if not FIREBASE_KEY or FIREBASE_KEY == "...":
        raise ValueError("FIREBASE_API_KEY missing in Render Environment Variables.")

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_KEY}"

    resp = requests.post(
        url,
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=10,
    )

    data = resp.json()

    if "error" in data:
        raise ValueError(data["error"].get("message", "Login failed"))

    return data


# ─────────────────────────────────────────────
# Login Page
# ─────────────────────────────────────────────
def show_login():

    _, col, _ = st.columns([1, 1.6, 1])

    with col:

        # Language selector
        lang_options = list(LANGUAGE_NAMES.keys())
        chosen = st.selectbox(
            "🌐 Language",
            options=lang_options,
            format_func=lambda x: LANGUAGE_NAMES[x],
            index=lang_options.index(st.session_state.get("language", "en")),
        )
        st.session_state.language = chosen

        st.markdown("""
        <div style="text-align:center;padding:2rem 0 1.5rem;">
          <div style="width:80px;height:80px;background:linear-gradient(135deg,#1a7a4a,#40c87a);
               border-radius:22px;display:inline-flex;align-items:center;justify-content:center;
               font-size:42px;box-shadow:0 8px 24px rgba(26,122,74,.35);margin-bottom:14px;">
            ♻️
          </div>
          <h1 style="font-size:32px;font-weight:900;color:#1a7a4a;margin:0;">
            WASTE IQ
          </h1>
          <p style="color:#718096;font-size:15px;margin-top:4px;">
            Smart Waste. Cleaner Cities.
          </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔑 Login", "✨ Sign Up"])

        # ───────── LOGIN ─────────
        with tab_login:

            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                try:
                    data = _sign_in(email, password)
                    uid = data["localId"]

                    profile = get_doc("users", uid) or {}

                    st.session_state.logged_in = True
                    st.session_state.uid = uid
                    st.session_state.email = email
                    st.session_state.name = profile.get("name", email.split("@")[0])
                    st.session_state.role = profile.get("role", "household")
                    st.session_state.active_page = "dashboard"

                    st.rerun()

                except Exception as e:
                    st.error(str(e))

            # ───── DEMO LOGIN BUTTONS ─────
            st.markdown("---")
            st.markdown("### 🚀 Quick Demo Login")

            demo_accounts = [
                ("🏠 Household", "household@wasteiq.demo", "demo1234"),
                ("🏛️ Municipal", "municipal@wasteiq.demo", "demo1234"),
                ("🚛 Driver", "driver@wasteiq.demo", "demo1234"),
                ("⚙️ Admin", "admin@wasteiq.demo", "demo1234"),
            ]

            cols = st.columns(2)

            for i, (label, d_email, d_pw) in enumerate(demo_accounts):
                with cols[i % 2]:
                    if st.button(label, use_container_width=True):
                        try:
                            data = _sign_in(d_email, d_pw)
                            uid = data["localId"]

                            profile = get_doc("users", uid) or {}

                            st.session_state.logged_in = True
                            st.session_state.uid = uid
                            st.session_state.email = d_email
                            st.session_state.name = profile.get("name", label)
                            st.session_state.role = profile.get("role", "household")
                            st.session_state.active_page = "dashboard"

                            st.rerun()

                        except Exception as e:
                            st.error(f"Demo login failed: {e}")

        # ───────── SIGNUP ─────────
        with tab_signup:

            with st.form("signup_form"):
                s_name = st.text_input("Full Name")
                s_email = st.text_input("Email")
                s_password = st.text_input("Password", type="password")
                s_role = st.selectbox("Role", ["household", "municipal", "driver"])
                s_ward = st.text_input("Ward ID (optional)")
                submit_signup = st.form_submit_button("Create Account", use_container_width=True)

            if submit_signup:

                if not all([s_name, s_email, s_password]):
                    st.error("Please fill all required fields.")
                elif len(s_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        # Create Firebase Auth user
                        user = admin_auth.create_user(
                            email=s_email,
                            password=s_password,
                            display_name=s_name,
                        )

                        # Create Firestore profile
                        set_doc("users", user.uid, {
                            "name": s_name,
                            "email": s_email,
                            "role": s_role,
                            "ward_id": s_ward or None,
                            "language": "en",
                        })

                        st.success("✅ Account created successfully. Please log in.")

                    except Exception as e:
                        st.error(f"Signup failed: {e}")

        st.markdown(
            '<div style="text-align:center;margin-top:2rem;color:#a0aec0;font-size:12px;">'
            'WASTE IQ © 2025</div>',
            unsafe_allow_html=True,
        )
