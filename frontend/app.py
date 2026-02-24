"""
WASTE IQ – Main Streamlit App Entry Point
Single-process production architecture (Render-safe)
"""

import sys
from pathlib import Path

# ─────────────────────────────────────────────
# FIX: Add PROJECT ROOT to Python path
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="WASTE IQ",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from frontend.utils import inject_css, init_session
from frontend.languages import t, LANGUAGE_NAMES

# ─────────────────────────────────────────────
# Single-process architecture (No FastAPI)
# ─────────────────────────────────────────────

init_session()
inject_css()

# If not logged in → show login page
if not st.session_state.get("logged_in"):
    from frontend._pages.login import show_login
    show_login()
    st.stop()

# ════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════
with st.sidebar:

    st.markdown("""
    <div class="wiq-sidebar-logo">
      <div class="logo-icon">♻️</div>
      <div class="logo-text">
        <h1>WASTE IQ</h1>
        <span>Smart Waste Management</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

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

    st.markdown("---")

    lang_options = list(LANGUAGE_NAMES.keys())
    current_lang = st.session_state.get("language", "en")
    sel_idx = lang_options.index(current_lang) if current_lang in lang_options else 0

    chosen_lang = st.selectbox(
        f"🌐 {t('lbl_language')}",
        options=lang_options,
        format_func=lambda x: LANGUAGE_NAMES[x],
        index=sel_idx,
    )

    if chosen_lang != current_lang:
        st.session_state.language = chosen_lang
        st.rerun()

    dark = st.toggle(
        f"🌙 {t('lbl_dark_mode')}",
        value=st.session_state.get("dark_mode", False),
    )

    if dark != st.session_state.get("dark_mode"):
        st.session_state.dark_mode = dark
        st.rerun()

    st.markdown("---")

    if st.button(f"🚪 {t('nav_logout')}", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    with st.expander("System Status", expanded=False):
        st.success("System Running ✅")

# ════════════════════════════════════════════
# PAGE ROUTING
# ════════════════════════════════════════════
page = st.session_state.active_page

if page == "dashboard":
    if role == "household":
        from frontend._pages.household_dashboard import show
    elif role == "municipal":
        from frontend._pages.municipal_dashboard import show
    elif role == "driver":
        from frontend._pages.driver_dashboard import show
    else:
        from frontend._pages.admin_dashboard import show
    show()

elif page == "classify":
    from frontend._pages.classifier import show
    show()

elif page == "complaints":
    from frontend._pages.complaints import show
    show()

elif page == "rewards":
    from frontend._pages.rewards import show
    show()

elif page == "notifications":
    from frontend._pages.notifications import show
    show()

elif page == "profile":
    from frontend._pages.profile import show
    show()

elif page == "route":
    from frontend._pages.driver_route import show
    show()

elif page == "admin":
    from frontend._pages.admin_dashboard import show
    show()

else:
    st.error(f"Unknown page: {page}")
