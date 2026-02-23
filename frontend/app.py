"""
WASTE IQ – Main Streamlit App Entry Point
Run: streamlit run app.py --server.port 8501
"""

import sys
import os
from pathlib import Path

# Ensure frontend directory is in path for imports
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import streamlit as st

st.set_page_config(
    page_title="WASTE IQ",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils import inject_css, init_session, check_backend
from languages import t, LANGUAGE_NAMES

# ── Auto-Start FastAPI Backend (For Render/Production Deploy) ───────────────
@st.cache_resource
def start_backend():
    import subprocess
    print("🚀 Auto-starting FastAPI backend on port 8000...")
    backend_dir = Path(__file__).parent.parent / "backend"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(backend_dir)
    )
    return proc

# Initialize backend immediately when Streamlit starts
_backend_process = start_backend()

# ── Initialise session & inject CSS ──────────────────────────────────────────
init_session()
inject_css()

# ── If not logged in → show login page ───────────────────────────────────────
if not st.session_state.logged_in:
    from _pages.login import show_login
    show_login()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Logo
    st.markdown("""
    <div class="wiq-sidebar-logo">
      <div class="logo-icon">♻️</div>
      <div class="logo-text">
        <h1>WASTE IQ</h1>
        <span>Smart Waste Management</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # User card
    role = st.session_state.role
    name = st.session_state.name
    st.markdown(
        f"""
        <div class="wiq-user-card">
          <div class="user-name">👤 {name}</div>
          <div class="user-role-badge role-{role}">{role.title()}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### Navigation")

    def nav_btn(label: str, page: str):
        active_style = "border-left:3px solid #1a7a4a;background:rgba(26,122,74,.08);font-weight:600;color:#1a7a4a;" if st.session_state.active_page == page else ""
        if st.button(label, key=f"nav_{page}", use_container_width=True):
            st.session_state.active_page = page
            st.rerun()

    nav_btn(f"📊  {t('nav_dashboard')}",     "dashboard")
    nav_btn(f"🔍  {t('nav_classify')}",      "classify")
    nav_btn(f"📢  {t('nav_complaints')}",    "complaints")
    nav_btn(f"🏆  {t('nav_rewards')}",       "rewards")
    nav_btn(f"🔔  {t('nav_notifications')}", "notifications")
    nav_btn(f"👤  {t('nav_profile')}",       "profile")

    if role in ("driver", "admin"):
        st.markdown("---")
        nav_btn(f"🗺️  {t('nav_route')}", "route")

    if role == "admin":
        nav_btn(f"⚙️  {t('nav_admin')}", "admin")

    # ── Settings ──────────────────────────────────────────────────────────
    st.markdown("---")

    lang_options = list(LANGUAGE_NAMES.keys())
    current_lang = st.session_state.get("language", "en")
    sel_idx      = lang_options.index(current_lang) if current_lang in lang_options else 0

    chosen_lang = st.selectbox(
        f"🌐 {t('lbl_language')}",
        options=lang_options,
        format_func=lambda x: LANGUAGE_NAMES[x],
        index=sel_idx,
        key="lang_selector",
    )
    if chosen_lang != current_lang:
        st.session_state.language = chosen_lang
        st.rerun()

    dark = st.toggle(f"🌙 {t('lbl_dark_mode')}", value=st.session_state.dark_mode, key="dark_toggle")
    if dark != st.session_state.dark_mode:
        st.session_state.dark_mode = dark
        st.rerun()

    st.markdown("---")

    if st.button(f"🚪 {t('nav_logout')}", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    with st.expander("System Status", expanded=False):
        if check_backend():
            st.success("Backend ✅ Online")
        else:
            st.warning("Backend ⚠️ Offline")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════════════════════
page = st.session_state.active_page

if page == "dashboard":
    if role == "household":
        from _pages.household_dashboard import show
    elif role == "municipal":
        from _pages.municipal_dashboard import show
    elif role == "driver":
        from _pages.driver_dashboard import show
    else:
        from _pages.admin_dashboard import show
    show()

elif page == "classify":
    from _pages.classifier import show
    show()

elif page == "complaints":
    from _pages.complaints import show
    show()

elif page == "rewards":
    from _pages.rewards import show
    show()

elif page == "notifications":
    from _pages.notifications import show
    show()

elif page == "profile":
    from _pages.profile import show
    show()

elif page == "route":
    from _pages.driver_route import show
    show()

elif page == "admin":
    from _pages.admin_dashboard import show
    show()

else:
    st.error(f"Unknown page: {page}")
