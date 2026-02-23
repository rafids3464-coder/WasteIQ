"""
WASTE IQ – Login / Signup Page
Firebase Auth REST-based login with role selection.
"""

import streamlit as st
import requests
import os
from utils import inject_css, init_session, show_toast, api_post, BACKEND_URL
from languages import t, LANGUAGE_NAMES

FIREBASE_KEY = os.getenv("FIREBASE_API_KEY", "")


def _sign_in(email: str, password: str) -> dict:
    if not FIREBASE_KEY or FIREBASE_KEY == "...":
        raise ValueError("CRITICAL: FIREBASE_API_KEY is missing or invalid! Please go precisely to your Render Dashboard > Environment Variables, and securely paste your REAL Firebase Web API Key (do not use '...').")
        
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_KEY}"
    resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
    data = resp.json()
    if "error" in data:
        err_msg = data["error"].get("message", "Login failed").replace("_", " ").title()
        if "Unregistered Callers" in err_msg or "Invalid Api Key" in err_msg.title():
            raise ValueError(f"Render Config Error: Your FIREBASE_API_KEY is invalid. Please check your Render Dashboard Environment Variables. (Google API Error: {err_msg})")
        raise ValueError(err_msg)
    return data


def _get_profile(id_token: str) -> dict:
    """Fetch user profile from backend after login."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/auth/me",
            headers={"Authorization": f"Bearer {id_token}"},
            timeout=10,
        )
        if resp.ok:
            return resp.json().get("data", {})
    except Exception:
        pass
    return {}


def show_login():
    inject_css()

    # Centered layout
    _, col, _ = st.columns([1, 1.6, 1])

    with col:
        # Language selector at top
        lang_options = list(LANGUAGE_NAMES.keys())
        chosen = st.selectbox(
            "🌐 Language",
            options=lang_options,
            format_func=lambda x: LANGUAGE_NAMES[x],
            index=lang_options.index(st.session_state.get("language", "en")),
            key="login_lang",
        )
        st.session_state.language = chosen

        # Logo & branding
        st.markdown("""
        <div style="text-align:center;padding:2rem 0 1.5rem;">
          <div style="width:80px;height:80px;background:linear-gradient(135deg,#1a7a4a,#40c87a);
               border-radius:22px;display:inline-flex;align-items:center;justify-content:center;
               font-size:42px;box-shadow:0 8px 24px rgba(26,122,74,.35);margin-bottom:14px;">
            ♻️
          </div>
          <h1 style="font-size:32px;font-weight:900;color:#1a7a4a;letter-spacing:-1.5px;margin:0;">
            WASTE IQ
          </h1>
          <p style="color:#718096;font-size:15px;font-weight:500;margin-top:4px;">
            Smart Waste. Cleaner Cities.
          </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs([f"🔑 {t('auth_login')}", f"✨ {t('auth_signup')}"])

        # ── LOGIN TAB ──────────────────────────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                email    = st.text_input(t("auth_email"),    placeholder="you@example.com")
                password = st.text_input(t("auth_password"), placeholder="••••••••", type="password")
                submitted = st.form_submit_button(t("auth_login"), use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter email and password.")
                else:
                    with st.spinner("Signing in..."):
                        try:
                            data    = _sign_in(email, password)
                            id_token = data["idToken"]
                            profile = _get_profile(id_token)

                            st.session_state.logged_in  = True
                            st.session_state.id_token   = id_token
                            st.session_state.uid        = data["localId"]
                            st.session_state.email      = email
                            st.session_state.name       = profile.get("name", data.get("displayName", email.split("@")[0]))
                            st.session_state.role       = profile.get("role", "household")
                            st.session_state.ward_id    = profile.get("ward_id")
                            st.session_state.language   = profile.get("language", chosen)
                            st.session_state.active_page= "dashboard"
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Connection error: {e}")

            st.markdown("---")
            st.markdown("**Quick Demo Login**", help="Pre-fill credentials for demo roles")
            demo_roles = [
                ("🏠 Household", "household@wasteiq.demo", "demo1234"),
                ("🏛️ Municipal", "municipal@wasteiq.demo", "demo1234"),
                ("🚛 Driver",    "driver@wasteiq.demo",   "demo1234"),
                ("⚙️ Admin",    "admin@wasteiq.demo",    "demo1234"),
            ]
            cols = st.columns(2)
            for i, (label, d_email, d_pw) in enumerate(demo_roles):
                with cols[i % 2]:
                    if st.button(label, key=f"demo_{i}", use_container_width=True):
                        with st.spinner("Signing in..."):
                            try:
                                data     = _sign_in(d_email, d_pw)
                                id_token = data["idToken"]
                                profile  = _get_profile(id_token)
                                st.session_state.logged_in   = True
                                st.session_state.id_token    = id_token
                                st.session_state.uid         = data["localId"]
                                st.session_state.email       = d_email
                                st.session_state.name        = profile.get("name", label)
                                st.session_state.role        = profile.get("role", "household")
                                st.session_state.ward_id     = profile.get("ward_id")
                                st.session_state.active_page = "dashboard"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Demo login failed: {e}. Run seed_firestore.py first.")

        # ── SIGNUP TAB ────────────────────────────────────────────────────
        with tab_signup:
            with st.form("signup_form"):
                s_name     = st.text_input(t("auth_name"),     placeholder="Your full name")
                s_email    = st.text_input(t("auth_email"),    placeholder="you@example.com")
                s_password = st.text_input(t("auth_password"), placeholder="Min 6 characters", type="password")
                s_role     = st.selectbox(
                    t("auth_role"),
                    options=["household", "municipal", "driver"],
                    format_func=lambda r: {"household": "🏠 Household User",
                                           "municipal": "🏛️ Municipal Officer",
                                           "driver":    "🚛 Transport Driver"}.get(r, r),
                )
                s_ward = st.text_input("Ward ID (optional)", placeholder="e.g. WARD_01")
                sub_signup = st.form_submit_button(t("auth_signup"), use_container_width=True)

            if sub_signup:
                if not all([s_name, s_email, s_password]):
                    st.error("Please fill all required fields.")
                elif len(s_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account..."):
                        try:
                            resp = requests.post(f"{BACKEND_URL}/auth/signup", json={
                                "name":     s_name,
                                "email":    s_email,
                                "password": s_password,
                                "role":     s_role,
                                "ward_id":  s_ward or None,
                            }, timeout=15)
                            
                            if resp.ok and resp.json().get("success"):
                                st.success("✅ Account created! Please sign in.")
                            else:
                                err = resp.json().get('detail', 'Email may already be registered.') if resp.status_code == 400 else resp.text
                                st.error(f"Signup failed: {err}")
                        except Exception as e:
                            st.error(f"Signup failed (Server offline): {e}")

        # Footer
        st.markdown(
            '<div style="text-align:center;margin-top:2rem;color:#a0aec0;font-size:12px;">'
            'WASTE IQ © 2025 · Powered by Firebase & TensorFlow</div>',
            unsafe_allow_html=True,
        )
