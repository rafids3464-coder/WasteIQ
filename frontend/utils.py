"""
WASTE IQ – Frontend Utilities
CSS injection, Firebase Auth REST helpers, session management, API calls.
"""

import os
import streamlit as st
import requests
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", override=True)

BACKEND_URL  = os.getenv("BACKEND_URL", "http://localhost:8000")
FIREBASE_KEY = os.getenv("FIREBASE_API_KEY", "")
CSS_PATH     = Path(__file__).parent / "styles.css"

# ── CSS Injection ─────────────────────────────────────────────────────────────
def inject_css():
    """Inject stylesheet + animated cursor JS into the parent Streamlit page."""
    css = CSS_PATH.read_text(encoding="utf-8")
    st.html(f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
        <style>{css}</style>

        <script>
        (function() {{
          // Inject cursor into the PARENT window (actual Streamlit page, not sandboxed iframe)
          var parent = window.parent || window;
          var pdoc = parent.document;

          // Remove old cursor if it exists (hot reload)
          var old = pdoc.getElementById('wiq-cursor');
          var oldR = pdoc.getElementById('wiq-cursor-ring');
          if (old) old.remove();
          if (oldR) oldR.remove();

          // Create cursor dot
          var cursor = pdoc.createElement('div');
          cursor.id = 'wiq-cursor';
          cursor.style.cssText = [
            'position:fixed', 'width:12px', 'height:12px', 'border-radius:50%',
            'background:#00e57d', 'pointer-events:none', 'z-index:999999',
            'transform:translate(-50%,-50%)',
            'box-shadow:0 0 14px rgba(0,229,125,0.7),0 0 40px rgba(0,229,125,0.3)',
            'transition:width 0.18s,height 0.18s',
            'mix-blend-mode:screen', 'top:0', 'left:0'
          ].join(';');

          // Create cursor ring
          var ring = pdoc.createElement('div');
          ring.id = 'wiq-cursor-ring';
          ring.style.cssText = [
            'position:fixed', 'width:38px', 'height:38px',
            'border:1.5px solid rgba(0,229,125,0.55)', 'border-radius:50%',
            'pointer-events:none', 'z-index:999998',
            'transform:translate(-50%,-50%)',
            'transition:width 0.3s ease,height 0.3s ease,border-color 0.2s',
            'top:0', 'left:0'
          ].join(';');

          pdoc.body.appendChild(cursor);
          pdoc.body.appendChild(ring);

          // Hide system cursor on parent
          pdoc.body.style.cursor = 'none';

          var rx = 0, ry = 0, mx = 0, my = 0;

          pdoc.addEventListener('mousemove', function(e) {{
            mx = e.clientX; my = e.clientY;
            cursor.style.left = mx + 'px';
            cursor.style.top  = my + 'px';
          }});

          // Smooth ring follow
          function tick() {{
            rx += (mx - rx) * 0.14;
            ry += (my - ry) * 0.14;
            ring.style.left = rx + 'px';
            ring.style.top  = ry + 'px';
            parent.requestAnimationFrame(tick);
          }}
          tick();

          // Expand ring on interactive hover
          pdoc.addEventListener('mouseover', function(e) {{
            var el = e.target;
            if (el.tagName === 'BUTTON' || el.tagName === 'A' ||
                el.closest && (el.closest('button') || el.closest('[role="button"]') ||
                el.closest('[data-baseweb="tab"]'))) {{
              cursor.style.width  = '20px';
              cursor.style.height = '20px';
              cursor.style.background = '#a855f7';
              cursor.style.boxShadow  = '0 0 20px rgba(168,85,247,0.8)';
              ring.style.width  = '56px';
              ring.style.height = '56px';
              ring.style.borderColor = 'rgba(168,85,247,0.7)';
            }}
          }});
          pdoc.addEventListener('mouseout', function(e) {{
            cursor.style.width  = '12px';
            cursor.style.height = '12px';
            cursor.style.background = '#00e57d';
            cursor.style.boxShadow  = '0 0 14px rgba(0,229,125,0.7)';
            ring.style.width  = '38px';
            ring.style.height = '38px';
            ring.style.borderColor = 'rgba(0,229,125,0.55)';
          }});

          // Inject parent-level CSS for dark theme global fixes
          var pstyle = pdoc.getElementById('wiq-parent-style');
          if (!pstyle) {{
            pstyle = pdoc.createElement('style');
            pstyle.id = 'wiq-parent-style';
            pdoc.head.appendChild(pstyle);
          }}
          pstyle.textContent = [
            '@import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap");',
            'body {{ background:#060d0a !important; font-family:Inter,sans-serif !important; cursor:none !important; }}',
            '[data-testid="stAppViewContainer"] {{ background:#060d0a !important; }}',
            '[data-testid="stHeader"] {{ background:transparent !important; }}',
          ].join('\\n');
        }})();
        </script>
    """)



# ── Session Defaults ──────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "logged_in":   False,
        "id_token":    None,
        "uid":         None,
        "email":       None,
        "name":        "User",
        "role":        "household",
        "ward_id":     None,
        "language":    "en",
        "dark_mode":   False,
        "active_page": "dashboard",
        "toast":       None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── Toast Notification ────────────────────────────────────────────────────────
def show_toast(message: str, toast_type: str = "success"):
    """Display a toast notification (client-side via HTML)."""
    icons = {"success": "✅", "error": "❌", "info": "ℹ️", "warning": "⚠️"}
    icon = icons.get(toast_type, "ℹ️")
    st.markdown(
        f"""
        <div class="wiq-toast toast-{toast_type}" id="wiq-toast" style="position:fixed;bottom:24px;right:24px;z-index:9999;
             padding:14px 20px;border-radius:12px;font-size:14px;font-weight:500;
             box-shadow:0 10px 28px rgba(0,0,0,.15);animation:slideInRight 0.3s ease;
             max-width:360px;display:flex;align-items:center;gap:10px;">
          <span>{icon}</span><span>{message}</span>
        </div>
        <script>
          setTimeout(()=>{{var t=document.getElementById('wiq-toast');if(t)t.remove();}},3500);
        </script>
        """,
        unsafe_allow_html=True,
    )

# ── Firebase Auth REST API ────────────────────────────────────────────────────
def firebase_sign_in(email: str, password: str) -> dict:
    """Sign in with Firebase Auth REST API. Returns {idToken, localId, email}."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_KEY}"
    resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
    data = resp.json()
    if "error" in data:
        raise ValueError(data["error"].get("message", "Authentication failed"))
    return data

def firebase_sign_up_rest(email: str, password: str) -> dict:
    """Create user via Firebase Auth REST API (for frontend-only flow)."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_KEY}"
    resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
    data = resp.json()
    if "error" in data:
        raise ValueError(data["error"].get("message", "Registration failed"))
    return data

def firebase_refresh_token(refresh_token: str) -> dict:
    """Refresh the Firebase ID token."""
    url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_KEY}"
    resp = requests.post(url, json={"grant_type": "refresh_token", "refresh_token": refresh_token}, timeout=10)
    return resp.json()

# ── API Helpers ────────────────────────────────────────────────────────────────
def get_headers() -> dict:
    """Return Authorization headers using the stored ID token."""
    token = st.session_state.get("id_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def api_get(path: str, params: dict = None) -> dict | None:
    """GET request to backend. Returns parsed JSON or None on error."""
    if not st.session_state.get("id_token"):
        return None  # Not logged in — silently skip
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", headers=get_headers(), params=params, timeout=15)
        if resp.status_code == 401:
            # Token expired — clear session and redirect to login
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
            return None
        if resp.status_code == 404:
            return None  # Endpoint not found — silent (don't spam red boxes)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Backend offline — start the FastAPI server on port 8000")
        return None
    except Exception:
        return None


def api_post(path: str, json_data: dict = None, files=None) -> dict | None:
    if not st.session_state.get("id_token"):
        return None
    
    headers = get_headers()
    # Requests requires us NOT to set Content-Type header when uploading files 
    # so it can automatically set multipart/form-data boundary.
    if files and "Content-Type" in headers:
            del headers["Content-Type"]

    try:
        resp = requests.post(
            f"{BACKEND_URL}{path}",
            headers=headers,
            json=json_data if not files else None,
            files=files,
            timeout=30,
        )
        if resp.status_code == 401:
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Backend offline")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_patch(path: str, json_data: dict) -> dict | None:
    if not st.session_state.get("id_token"):
        return None
    try:
        resp = requests.patch(f"{BACKEND_URL}{path}", headers=get_headers(), json=json_data, timeout=15)
        if resp.status_code == 401:
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Backend offline")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def api_download(path: str, params: dict = None):
    """Download bytes from a backend endpoint (for CSV/PDF)."""
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", headers=get_headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.content, resp.headers.get("content-type",""), resp.headers.get("content-disposition","")
    except Exception as e:
        st.error(f"Download error: {e}")
        return None, None, None

# ── KPI Card HTML ─────────────────────────────────────────────────────────────
def kpi_card(icon: str, value: str | int, label: str, accent: str = "#1a7a4a", delta: str = None, delta_up: bool = True):
    delta_html = ""
    if delta:
        arrow = "▲" if delta_up else "▼"
        cls   = "kpi-delta-up" if delta_up else "kpi-delta-down"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {delta}</div>'

    st.markdown(
        f"""
        <div class="wiq-kpi-card" style="--card-accent:{accent}">
          <div class="kpi-icon">{icon}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-label">{label}</div>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Category Chip ─────────────────────────────────────────────────────────────
CATEGORY_CHIP_CLASS = {
    "Wet Waste":       "chip-wet",
    "Dry Waste":       "chip-dry",
    "Recyclable":      "chip-recyclable",
    "Hazardous Waste": "chip-hazardous",
    "E-Waste":         "chip-ewaste",
    "General Waste":   "chip-general",
}

CATEGORY_ICONS = {
    "Wet Waste":       "🥬",
    "Dry Waste":       "📦",
    "Recyclable":      "♻️",
    "Hazardous Waste": "☢️",
    "E-Waste":         "💻",
    "General Waste":   "🗑️",
}

def category_chip(category: str) -> str:
    cls  = CATEGORY_CHIP_CLASS.get(category, "chip-general")
    icon = CATEGORY_ICONS.get(category, "🗑️")
    return f'<span class="chip {cls}">{icon} {category}</span>'

# ── Greeting ──────────────────────────────────────────────────────────────────
def time_greeting() -> str:
    from datetime import datetime, timezone, timedelta
    # IST offset
    hour = datetime.now(timezone(timedelta(hours=5, minutes=30))).hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    return "Good evening"

# ── Page header ───────────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = ""):
    sub_html = f'<div class="subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="wiq-page-header"><div><h1>{title}</h1>{sub_html}</div></div>',
        unsafe_allow_html=True,
    )

# ── Card wrapper ──────────────────────────────────────────────────────────────
def card_start(title: str = "", icon: str = ""):
    icon_html = f"{icon} " if icon else ""
    hdr = f'<div class="wiq-card-title">{icon_html}{title}</div>' if title else ""
    st.markdown(f'<div class="wiq-card">{hdr}', unsafe_allow_html=True)

def card_end():
    st.markdown("</div>", unsafe_allow_html=True)

# ── Backend health check ──────────────────────────────────────────────────────
def check_backend() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return resp.ok
    except Exception:
        return False
