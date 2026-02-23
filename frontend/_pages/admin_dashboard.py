"""WASTE IQ – Admin Dashboard"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import folium
from streamlit_folium import st_folium
from utils import (
    page_header, kpi_card, api_get, api_download, show_toast,
    BACKEND_URL, get_headers, time_greeting
)
import requests


def show():
    page_header(
        f"{time_greeting()}, {st.session_state.name} ⚙️",
        "Full system overview — powered by real Firestore data"
    )

    with st.spinner("Loading city-wide data..."):
        city_data      = api_get("/reports/city-summary")
        bins_data      = api_get("/bins/")
        leaderboard    = api_get("/gamification/leaderboard", params={"limit": 10})
        overflow_data  = api_get("/overflow/high-risk")

    city       = city_data["data"]      if city_data      else {}
    bins       = bins_data["data"]      if bins_data      else []
    lb_entries = leaderboard["data"]    if leaderboard    else []
    high_risk  = overflow_data["data"]  if overflow_data  else []

    # ── KPI Row ───────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kpi_card("👥", city.get("total_users", 0),           "Total Users",           "#1a7a4a")
    with c2: kpi_card("🗑️", city.get("total_bins", 0),            "Total Bins",            "#3b82f6")
    with c3: kpi_card("🔍", city.get("total_classifications", 0), "Classifications",        "#8b5cf6")
    with c4: kpi_card("📢", city.get("total_complaints", 0),      "Total Complaints",       "#f59e0b")
    with c5: kpi_card("🔴", len(high_risk),                       "High-Risk Bins",         "#ef4444" if high_risk else "#22c55e")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Export buttons ────────────────────────────────────────────────────
    exp1, exp2, exp3, _ = st.columns([1, 1, 1, 3])
    with exp1:
        if st.button("📥 Export Waste Logs CSV", use_container_width=True):
            content, ctype, _ = api_download("/reports/export-csv", params={"report_type": "waste_logs"})
            if content:
                st.download_button("Download CSV", content, "waste_logs.csv", "text/csv", use_container_width=True)

    with exp2:
        if st.button("📥 Export Complaints CSV", use_container_width=True):
            content, ctype, _ = api_download("/reports/export-csv", params={"report_type": "complaints"})
            if content:
                st.download_button("Download CSV", content, "complaints.csv", "text/csv", use_container_width=True)

    with exp3:
        if st.button("📄 Download PDF Report", use_container_width=True):
            content, ctype, _ = api_download("/reports/export-pdf")
            if content:
                st.download_button("Download PDF", content, "city_report.pdf", "application/pdf", use_container_width=True)

    st.markdown("---")

    # ── Charts Row ────────────────────────────────────────────────────────
    left, right = st.columns([2, 1])

    with left:
        st.markdown("#### 🗑️ Waste by Category (City-wide)")
        by_cat = city.get("waste_by_category", {})
        if by_cat:
            fig = px.bar(
                x=list(by_cat.keys()), y=list(by_cat.values()),
                color=list(by_cat.keys()),
                color_discrete_sequence=["#4ade80","#facc15","#60a5fa","#f87171","#a78bfa","#94a3b8"],
                labels={"x": "Category", "y": "Count"},
                title="City-wide Waste Classification Breakdown",
            )
            fig.update_layout(
                showlegend=False, height=280, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_family="Inter",
                margin=dict(l=0,r=0,t=40,b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No classification data yet.")

    with right:
        st.markdown("#### 👥 Users by Role")
        roles = city.get("users_by_role", {})
        if roles:
            fig2 = px.pie(
                names=list(roles.keys()),
                values=list(roles.values()),
                color_discrete_sequence=["#4ade80","#60a5fa","#f59e0b","#ef4444"],
                hole=0.5,
            )
            fig2.update_layout(
                height=280, margin=dict(l=0,r=0,t=20,b=0),
                paper_bgcolor="rgba(0,0,0,0)", font_family="Inter",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.caption("No user data.")

    st.markdown("---")

    # ── Bin Heatmap + Ward Ranking ─────────────────────────────────────────
    map_col, ranking_col = st.columns([3, 2])

    with map_col:
        st.markdown("#### 🗺️ Bin Location Heatmap")
        if bins:
            # Calculate center
            lats = [b["location"]["lat"] for b in bins if b.get("location")]
            lngs = [b["location"]["lng"] for b in bins if b.get("location")]
            center = [sum(lats)/len(lats), sum(lngs)/len(lngs)] if lats else [11.25, 75.78]

            m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

            # Add heatmap using fill levels as intensity
            from folium.plugins import HeatMap
            heat_data = []
            for b in bins:
                loc = b.get("location", {})
                if loc.get("lat") and loc.get("lng"):
                    intensity = b.get("fill_level", 0) / 100.0
                    heat_data.append([loc["lat"], loc["lng"], intensity])

            if heat_data:
                HeatMap(heat_data, min_opacity=0.3, radius=20, blur=15).add_to(m)

            # Also add circle markers
            for b in bins:
                loc = b.get("location", {})
                if loc.get("lat") and loc.get("lng"):
                    fill = b.get("fill_level", 0)
                    color = "#ef4444" if fill >= 80 else "#f59e0b" if fill >= 50 else "#22c55e"
                    folium.CircleMarker(
                        [loc["lat"], loc["lng"]],
                        radius=6,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.7,
                        tooltip=f"Fill: {fill:.0f}%",
                    ).add_to(m)

            st_folium(m, width=600, height=380, returned_objects=[])
        else:
            st.info("No bin data available.")

    with ranking_col:
        st.markdown("#### 🏆 Ward Performance Ranking")
        ward_ranking = city.get("ward_ranking", [])
        if ward_ranking:
            for i, w in enumerate(ward_ranking[:8]):
                medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}."
                rate  = w.get("resolution_rate", 0)
                color = "#22c55e" if rate >= 80 else "#f59e0b" if rate >= 50 else "#ef4444"
                st.markdown(
                    f"""<div style="display:flex;align-items:center;justify-content:space-between;
                         padding:8px 12px;border:1px solid #e2e8f0;border-radius:8px;
                         margin-bottom:6px;background:#fff;">
                      <span><b>{medal}</b> {w.get('ward_id','—')}</span>
                      <span style="color:{color};font-weight:700;">{rate}%</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No ward data yet.")

    st.markdown("---")

    # ── Leaderboard + User Management ─────────────────────────────────────
    lb_col, user_col = st.columns([1, 1])

    with lb_col:
        st.markdown("#### 🏆 System Leaderboard")
        if lb_entries:
            lb_rows = [{
                "Rank":   e["rank"],
                "Name":   e["name"],
                "Role":   e["role"].title(),
                "Points": e["total_points"],
                "Level":  e.get("level","Beginner"),
            } for e in lb_entries]
            st.dataframe(pd.DataFrame(lb_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No leaderboard data yet.")

    with user_col:
        st.markdown("#### 👥 User Management")
        users_resp = api_get("/auth/users")
        users = users_resp["data"] if users_resp else []
        if users:
            u_rows = [{
                "Name":  u.get("display_name","—"),
                "Email": u.get("email","—"),
                "Role":  u.get("role","household"),
                "UID":   u.get("uid","")[:8],
            } for u in users[:15]]
            st.dataframe(pd.DataFrame(u_rows), use_container_width=True, hide_index=True)

            st.markdown("**Change User Role**")
            uid_input  = st.text_input("User UID (full)", placeholder="Paste full UID")
            new_role   = st.selectbox("New Role", ["household","municipal","driver","admin"])
            if st.button("Update Role", use_container_width=True):
                if uid_input:
                    resp = requests.patch(
                        f"{BACKEND_URL}/auth/users/{uid_input}/role",
                        headers=get_headers(),
                        json={"role": new_role},
                        timeout=10,
                    )
                    if resp.ok:
                        show_toast(f"Role updated to {new_role} ✅", "success")
                    else:
                        show_toast("Failed to update role", "error")
        else:
            st.caption("No users found or insufficient permissions.")
