"""
WASTE IQ – Household Dashboard
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timezone
from utils import (
    page_header, kpi_card, category_chip,
    api_get, api_post, show_toast, time_greeting, card_start, card_end
)
from languages import t


def show():
    page_header(
        f"{time_greeting()}, {st.session_state.name} 👋",
        "Your personal waste management overview"
    )

    # ── Fetch data ────────────────────────────────────────────────────────
    with st.spinner("Loading your data..."):
        cls_data  = api_get("/classify/history",     params={"limit": 100})
        cls_stats = api_get("/classify/stats")
        gam_data  = api_get("/gamification/me")
        comp_data = api_get("/complaints", params={"status": None})

    logs       = cls_data["data"]  if cls_data  else []
    gam        = gam_data["data"]  if gam_data  else {}
    complaints = comp_data["data"] if comp_data else []
    cat_stats  = cls_stats["data"] if cls_stats else {"total_classifications": 0, "by_category": {}}

    total_cls   = cat_stats.get("total_classifications", 0)
    total_pts   = gam.get("total_points", 0)
    level       = gam.get("level", "Beginner")
    open_comp   = sum(1 for c in complaints if c.get("status") == "open")

    # ── KPI Row ───────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("🔍", total_cls, t("dash_total_class"), "#1a7a4a")
    with c2:
        kpi_card("⭐", total_pts, t("dash_total_points"), "#f59e0b")
    with c3:
        kpi_card("🏅", level, "Current Level", "#8b5cf6")
    with c4:
        kpi_card("📢", open_comp, t("dash_complaints"), "#ef4444" if open_comp > 0 else "#22c55e")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Waste Trend Chart + Category Breakdown ────────────────────────────
    left, right = st.columns([2, 1])

    with left:
        st.markdown("#### 📈 Waste Classification History")
        if logs:
            df = pd.DataFrame(logs)
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date
            daily = df.groupby(["date", "waste_category"]).size().reset_index(name="count")
            fig = px.bar(
                daily, x="date", y="count", color="waste_category",
                color_discrete_map={
                    "Wet Waste": "#4ade80", "Dry Waste": "#facc15",
                    "Recyclable": "#60a5fa", "Hazardous Waste": "#f87171",
                    "E-Waste": "#a78bfa", "General Waste": "#94a3b8",
                },
                labels={"count": "Items", "date": "Date", "waste_category": "Category"},
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_family="Inter", legend_title="Category",
                margin=dict(l=0, r=0, t=20, b=0), height=280,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No classification history yet. Classify your first waste item!")

    with right:
        st.markdown("#### 🗑️ By Category")
        by_cat = cat_stats.get("by_category", {})
        if by_cat:
            fig2 = px.pie(
                names=list(by_cat.keys()),
                values=list(by_cat.values()),
                color_discrete_sequence=px.colors.qualitative.Pastel,
                hole=0.45,
            )
            fig2.update_layout(
                margin=dict(l=0, r=0, t=20, b=0), height=280,
                showlegend=True, paper_bgcolor="rgba(0,0,0,0)",
                font_family="Inter",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.caption("No data yet")

    st.markdown("---")

    # ── Recent Classifications ────────────────────────────────────────────
    col_recent, col_complaint = st.columns([3, 2])

    with col_recent:
        st.markdown("#### 🕒 Recent Classifications")
        if logs:
            display = []
            for l in logs[:10]:
                display.append({
                    "Date":       pd.to_datetime(l["timestamp"]).strftime("%b %d, %H:%M"),
                    "Object":     l.get("object_name", "—"),
                    "Category":   l.get("waste_category", "—"),
                    "Confidence": f"{l.get('confidence', 0):.1f}%",
                })
            st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)
        else:
            st.caption("No records found.")

    with col_complaint:
        st.markdown("#### 📢 Submit a Complaint")
        with st.form("quick_complaint"):
            ct = st.text_input("Issue Title*", placeholder="Overflowing bin near park")
            cd = st.text_area("Description*", placeholder="Describe the issue...", height=80)
            cl = st.text_input("📍 Location / Landmark", placeholder="Near City Park, Gate 3")
            cw = st.text_input("Ward ID*", value=st.session_state.get("ward_id") or "", placeholder="WARD_01")
            sub = st.form_submit_button("Submit Complaint", use_container_width=True)

        if sub:
            if ct and cd and cw:
                result = api_post("/complaints/", json_data={
                    "title": ct, "description": cd, "ward_id": cw,
                    "location_text": cl or None,
                })
                if result and result.get("success"):
                    show_toast("Complaint submitted! +20 points awarded 🎉", "success")
                    st.rerun()
                else:
                    show_toast("Failed to submit complaint", "error")
            else:
                st.warning("Please fill Title, Ward ID, and Description.")

    # ── Badges ────────────────────────────────────────────────────────────
    badges = gam.get("badges", [])
    if badges:
        st.markdown("---")
        st.markdown("#### 🏅 Your Badges")
        cols = st.columns(min(len(badges), 4))
        for i, badge in enumerate(badges[:4]):
            with cols[i]:
                tier_cls = f"tier-{badge['tier'].lower()}"
                st.markdown(
                    f"""<div class="badge-card earned">
                      <div class="badge-icon">{badge['icon']}</div>
                      <div class="badge-name">{badge['name']}</div>
                      <div class="badge-tier {tier_cls}">{badge['tier']}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
