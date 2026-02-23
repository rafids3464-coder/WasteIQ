"""WASTE IQ – Driver KPI Dashboard (shown as main dashboard for driver role)"""

import streamlit as st
import plotly.express as px
import pandas as pd
from utils import page_header, kpi_card, api_get, time_greeting
from languages import t


def show():
    page_header(
        f"{time_greeting()}, {st.session_state.name} 🚛",
        "Your daily overview and performance metrics"
    )

    with st.spinner("Loading..."):
        stats_data = api_get("/route/stats")
        gam_data   = api_get("/gamification/me")
        route_data = api_get("/route/optimize")

    stats      = stats_data["data"]  if stats_data  else {}
    gam        = gam_data["data"]    if gam_data    else {}
    route      = route_data["data"]  if route_data  else {}
    waypoints  = route.get("waypoints", [])

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("🗑️", stats.get("bins_collected_today", 0), "Collected Today",  "#1a7a4a")
    with c2: kpi_card("📦", len(waypoints),                        "Remaining Bins",   "#3b82f6")
    with c3: kpi_card("⭐", gam.get("total_points", 0),            "Total Points",     "#f59e0b")
    with c4: kpi_card("📏", f"{route.get('total_distance_km',0):.1f} km", "Route Today","#8b5cf6")

    st.markdown("<br>", unsafe_allow_html=True)

    # Show pending bins table
    if waypoints:
        st.markdown("#### 🗑️ Pending Bins")
        rows = [{
            "Order":      wp["order"],
            "Fill Level": f"{wp.get('fill_level',0):.0f}%",
            "Ward":       wp.get("ward_id","—"),
            "Status":     wp.get("status","active").title(),
        } for wp in waypoints]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.info("Go to **My Route** in the sidebar to see the interactive map and mark bins as collected.")

    # Badges
    badges = gam.get("badges", [])
    if badges:
        st.markdown("---")
        st.markdown("#### 🏅 Earned Badges")
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
