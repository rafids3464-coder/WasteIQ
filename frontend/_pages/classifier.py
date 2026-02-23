"""WASTE IQ – Waste Classifier Page"""

import streamlit as st
import pandas as pd
from utils import page_header, api_get, show_toast, BACKEND_URL, get_headers
from languages import t
import requests


# Bin config: color, SVG fill, label
BIN_CONFIG = {
    "Wet Waste":      {"color": "#22c55e", "bg": "#052e16", "border": "#16a34a", "label": "GREEN BIN",  "emoji": "🟢", "icon": "🌿"},
    "Dry Waste":      {"color": "#3b82f6", "bg": "#172554", "border": "#2563eb", "label": "BLUE BIN",   "emoji": "🔵", "icon": "📦"},
    "Recyclable":     {"color": "#f59e0b", "bg": "#2d1a02", "border": "#d97706", "label": "YELLOW BIN", "emoji": "🟡", "icon": "♻️"},
    "Hazardous Waste":{"color": "#ef4444", "bg": "#2d0a0a", "border": "#dc2626", "label": "RED BIN",    "emoji": "🔴", "icon": "⚠️"},
    "E-Waste":        {"color": "#a855f7", "bg": "#1a0a2e", "border": "#9333ea", "label": "PURPLE BIN", "emoji": "🟣", "icon": "📱"},
    "General Waste":  {"color": "#6b7280", "bg": "#111827", "border": "#4b5563", "label": "BLACK BIN",  "emoji": "⚫", "icon": "🗑️"},
}


def _bin_svg(color: str, size: int = 80) -> str:
    """Render a waste bin SVG with the given color."""
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 60 70" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- Lid -->
      <rect x="8" y="6" width="44" height="8" rx="4" fill="{color}" opacity="0.9"/>
      <rect x="22" y="2" width="16" height="6" rx="3" fill="{color}"/>
      <!-- Body -->
      <path d="M12 14 L10 62 Q10 66 14 66 L46 66 Q50 66 50 62 L48 14 Z" fill="{color}" opacity="0.85"/>
      <!-- Lines -->
      <line x1="23" y1="20" x2="22" y2="60" stroke="white" stroke-width="2.5" stroke-opacity="0.3" stroke-linecap="round"/>
      <line x1="30" y1="20" x2="30" y2="60" stroke="white" stroke-width="2.5" stroke-opacity="0.3" stroke-linecap="round"/>
      <line x1="37" y1="20" x2="38" y2="60" stroke="white" stroke-width="2.5" stroke-opacity="0.3" stroke-linecap="round"/>
    </svg>"""


def _result_cards(obj: str, cat: str, conf: float, inst: str, tip: str, reasoning: str, mode: str, alternatives: list = None) -> str:
    """Return 3-column animated result HTML cards."""
    cfg = BIN_CONFIG.get(cat, BIN_CONFIG["General Waste"])
    c = cfg["color"]
    bg = cfg["bg"]
    border = cfg["border"]
    label = cfg["label"]
    icon = cfg["icon"]
    bin_svg = _bin_svg(c, 90)

    conf_pct = min(max(conf, 0), 100)
    conf_color = "#22c55e" if conf_pct >= 70 else "#f59e0b" if conf_pct >= 45 else "#ef4444"
    mode_badge = (
        f'<span style="background:rgba(124,58,237,0.2);color:#a855f7;border:1px solid rgba(124,58,237,0.4);'
        f'padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:1px;">✦ AI GEMINI</span>'
        if mode == "gemini" else
        f'<span style="background:rgba(107,114,128,0.2);color:#9ca3af;border:1px solid rgba(107,114,128,0.3);'
        f'padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:1px;">HEURISTIC</span>'
    )

    # Top-3 alternatives list
    alts_html = ""
    if alternatives:
        items = ""
        for alt in alternatives[:3]:
            n = alt.get("name", "")
            ac = float(alt.get("confidence", 0))
            if n:
                bar_w = min(max(int(ac), 0), 100)
                items += f"""
                <div style="margin:4px 0;">
                  <div style="display:flex;justify-content:space-between;font-size:11px;color:#9ca3af;margin-bottom:2px;">
                    <span>{n}</span><span style="color:#6b9c7d;">{ac:.0f}%</span>
                  </div>
                  <div style="background:rgba(255,255,255,0.06);border-radius:4px;height:4px;overflow:hidden;">
                    <div style="height:100%;width:{bar_w}%;background:rgba(0,229,125,0.35);border-radius:4px;"></div>
                  </div>
                </div>"""
        if items:
            alts_html = f"""
            <div style="margin-top:10px;padding:8px 10px;background:rgba(0,0,0,0.25);border-radius:8px;border:1px solid rgba(0,229,125,0.08);">
              <div style="font-size:10px;color:#3a5e49;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Top alternatives</div>
              {items}
            </div>"""

    return f"""
<style>
@keyframes cardSlideUp {{
  from {{ opacity:0; transform:translateY(20px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
@keyframes binBounce {{
  0%,100% {{ transform:translateY(0) rotate(0deg); }}
  25%     {{ transform:translateY(-6px) rotate(-3deg); }}
  75%     {{ transform:translateY(-3px) rotate(3deg); }}
}}
@keyframes confFill {{
  from {{ width: 0%; }}
  to   {{ width: {conf_pct:.0f}%; }}
}}
@keyframes glowPulse {{
  0%,100% {{ box-shadow: 0 0 12px {c}44, 0 0 0 1px {border}; }}
  50%     {{ box-shadow: 0 0 30px {c}77, 0 0 0 1px {border}; }}
}}
.wiq-result-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin: 16px 0;
}}
.wiq-res-card {{
  background: #0c1812;
  border: 1px solid rgba(0,229,125,0.12);
  border-radius: 14px;
  padding: 20px 16px;
  text-align: center;
  animation: cardSlideUp 0.45s ease both;
  position: relative;
  overflow: hidden;
}}
.wiq-res-card::before {{
  content: '';
  position: absolute; top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, {c}, transparent);
}}
.wiq-res-card:nth-child(2) {{ animation-delay: 0.1s; }}
.wiq-res-card:nth-child(3) {{ animation-delay: 0.2s; }}
.card-label {{
  font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; color: #6b9c7d; margin-bottom: 12px;
}}
.card-value {{
  font-size: 18px; font-weight: 800;
  color: #e8f5ee; line-height: 1.2; margin: 6px 0;
}}
.card-sub {{
  font-size: 12px; color: #6b9c7d; margin-top: 6px;
}}
.cat-badge {{
  display: inline-block;
  background: {bg};
  border: 1px solid {border};
  color: {c};
  padding: 6px 14px; border-radius: 20px;
  font-size: 13px; font-weight: 800;
  text-transform: uppercase; letter-spacing: 0.8px;
  margin: 8px 0;
}}
.bin-wrap {{
  animation: binBounce 2.5s ease-in-out infinite;
  display: inline-block; margin: 8px 0;
}}
.bin-card {{
  border-color: {border} !important;
  animation: glowPulse 2.5s ease-in-out infinite !important;
}}
.conf-bar-outer {{
  background: rgba(255,255,255,0.07);
  border-radius: 20px; height: 8px; overflow: hidden;
  margin: 12px 0 6px; width: 100%;
}}
.conf-bar-inner {{
  height: 100%; border-radius: 20px;
  background: linear-gradient(90deg, {conf_color}99, {conf_color});
  animation: confFill 0.9s ease 0.3s both;
  box-shadow: 0 0 8px {conf_color}88;
}}
.disposal-box {{
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(0,229,125,0.1);
  border-radius: 10px;
  padding: 12px 14px;
  text-align: left;
  font-size: 13px; color: #a8c5b0;
  margin-top: 12px; line-height: 1.6;
}}
.tip-box {{
  background: rgba(124,58,237,0.08);
  border: 1px solid rgba(124,58,237,0.2);
  border-radius: 10px;
  padding: 10px 14px;
  text-align: left;
  font-size: 12px; color: #c4b5fd;
  margin-top: 8px; line-height: 1.5;
}}
</style>

<div style="margin-bottom:8px; display:flex; align-items:center; gap:8px;">
  {mode_badge}
  <span style="font-size:11px;color:#6b9c7d;">Classification Result</span>
</div>

<div class="wiq-result-grid">

  <!-- Card 1: Object Detected -->
  <div class="wiq-res-card">
    <div class="card-label">🔍 Object Detected</div>
    <div style="font-size:36px; margin:8px 0;">{icon}</div>
    <div class="card-value">{obj}</div>
    <div class="conf-bar-outer">
      <div class="conf-bar-inner" style="width:{conf_pct:.0f}%;"></div>
    </div>
    <div class="card-sub" style="color:{conf_color};font-weight:700;">{conf_pct:.1f}% confidence</div>
    {alts_html}
  </div>

  <!-- Card 2: Waste Category -->
  <div class="wiq-res-card">
    <div class="card-label">♻️ Waste Category</div>
    <div style="font-size:36px; margin:8px 0;">🗂️</div>
    <div class="cat-badge">{cat}</div>
    <div class="disposal-box">{inst}</div>
    <div class="tip-box">{tip}</div>
  </div>

  <!-- Card 3: Disposal Bin -->
  <div class="wiq-res-card bin-card">
    <div class="card-label">🗑️ Dispose In</div>
    <div class="bin-wrap">{bin_svg}</div>
    <div class="card-value" style="color:{c};">{label}</div>
    <div class="card-sub">Place in the <strong style="color:{c};">{label.lower()}</strong></div>
  </div>

</div>
"""


def show():
    page_header("🔍 Waste Classifier", "Upload a photo and let AI identify your waste")

    tab_upload, tab_camera, tab_history = st.tabs(["📁 Upload Image", "📷 Use Camera", "📋 History"])

    # ── Upload Tab ────────────────────────────────────────────────────────
    with tab_upload:
        uploaded = st.file_uploader(
            t("cls_upload"),
            type=["jpg", "jpeg", "png", "webp"],
            help="Max 10MB. JPG, PNG, WebP supported.",
        )
        if uploaded:
            col_img, col_result = st.columns([1, 1])
            with col_img:
                st.image(uploaded, caption="Uploaded Image", use_container_width=True)
                if st.button("🔍 Classify This Image", use_container_width=True, key="classify_upload"):
                    _classify(uploaded, col_result)

    # ── Camera Tab ────────────────────────────────────────────────────────
    with tab_camera:
        cam_col, cam_result = st.columns([1, 1])
        with cam_col:
            camera_img = st.camera_input(t("cls_camera"))
            if camera_img:
                if st.button("🔍 Classify Photo", use_container_width=True, key="classify_camera"):
                    _classify(camera_img, cam_result)

    # ── History Tab ───────────────────────────────────────────────────────
    with tab_history:
        with st.spinner("Loading history..."):
            data = api_get("/classify/history", params={"limit": 50})
        logs = data["data"] if data else []
        if logs:
            rows = []
            for l in logs:
                cfg = BIN_CONFIG.get(l.get("waste_category", ""), BIN_CONFIG["General Waste"])
                rows.append({
                    "Date":       pd.to_datetime(l["timestamp"]).strftime("%b %d, %H:%M"),
                    "Object":     l.get("object_name", "—"),
                    "Category":   l.get("waste_category", "—"),
                    "Confidence": f"{l.get('confidence', 0):.1f}%",
                    "Mode":       l.get("mode", "heuristic"),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            import plotly.express as px
            cat_df = pd.DataFrame(logs)
            counts = cat_df["waste_category"].value_counts().reset_index()
            counts.columns = ["Category", "Count"]
            color_map = {k: v["color"] for k, v in BIN_CONFIG.items()}
            fig = px.bar(counts, x="Category", y="Count",
                         color="Category", color_discrete_map=color_map,
                         title="Your Waste Breakdown")
            fig.update_layout(showlegend=False, height=260,
                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                              font=dict(family="Inter", color="#e8f5ee"),
                              font_size=12, margin=dict(l=0, r=0, t=40, b=0),
                              title_font_color="#e8f5ee")
            fig.update_xaxes(showgrid=False, tickfont_color="#6b9c7d")
            fig.update_yaxes(showgrid=True, gridcolor="rgba(0,229,125,0.08)", tickfont_color="#6b9c7d")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No classification history yet. Classify an image to get started!")


def _classify(file_obj, result_col):
    from utils import api_post
    with st.spinner("🤖 Analyzing with AI — Step 1: Object detection..."):
        file_obj.seek(0)
        files = {"file": (getattr(file_obj, "name", "image.jpg"), file_obj, "image/jpeg")}
        resp = api_post("/classify/", files=files)

    if not resp or not resp.get("success"):
        st.error("Classification failed — check the backend is running.")
        return

    result = resp.get("data", {})
    cat    = result.get("waste_category", "General Waste")
    conf   = result.get("confidence", 0)
    obj    = result.get("object_name", "Unknown Item")
    inst   = result.get("disposal_instructions", "")
    tip    = result.get("recycling_tip", "")
    mode   = result.get("mode", "heuristic")
    alts   = result.get("alternatives", [])

    with result_col:
        st.markdown(
            _result_cards(obj, cat, conf, inst, tip, "", mode, alts),
            unsafe_allow_html=True,
        )
        show_toast(f"{obj} → {cat} | +5 pts 🌱", "success")
