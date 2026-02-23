"""WASTE IQ – Driver Dashboard (Route Map)"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from utils import page_header, kpi_card, api_get, show_toast, BACKEND_URL, get_headers, time_greeting
from languages import t
import requests


def show():
    page_header(
        f"{time_greeting()}, {st.session_state.name} 🚛",
        "Your daily collection route and bin assignments"
    )

    with st.spinner("Loading your route..."):
        route_data = api_get("/route/optimize")
        stats_data = api_get("/route/stats")

    route  = route_data["data"]  if route_data  else {}
    stats  = stats_data["data"]  if stats_data  else {}
    waypoints = route.get("waypoints", [])

    # ── KPI Cards ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("🗑️", len(waypoints),                       "Bins Remaining",          "#1a7a4a")
    with c2: kpi_card("📏", f"{route.get('total_distance_km', 0):.1f} km", "Route Distance",  "#3b82f6")
    with c3: kpi_card("⏱️", f"{route.get('eta_minutes', 0):.0f} min",      "Estimated Time",  "#8b5cf6")
    with c4: kpi_card("⭐", stats.get("total_points", 0),          "My Points",               "#f59e0b")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Map + Bin List ────────────────────────────────────────────────────
    map_col, list_col = st.columns([3, 2])

    with map_col:
        st.markdown("#### 🗺️ Optimized Collection Route")

        # Build Folium map
        if waypoints:
            center_lat = sum(w["location"]["lat"] for w in waypoints) / len(waypoints)
            center_lng = sum(w["location"]["lng"] for w in waypoints) / len(waypoints)
        else:
            center_lat, center_lng = 11.2588, 75.7804  # Kozhikode default

        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=13,
            tiles="CartoDB positron",
        )

        # Draw route polyline from GeoJSON
        geojson = route.get("geojson")
        if geojson and geojson.get("coordinates"):
            coords = geojson["coordinates"]
            # GeoJSON is [lng, lat], Folium needs [lat, lng]
            folium_coords = [[c[1], c[0]] for c in coords]
            folium.PolyLine(
                folium_coords,
                color="#1a7a4a",
                weight=4,
                opacity=0.8,
                dash_array="8 4",
                tooltip="Collection route",
            ).add_to(m)

        # Add bin markers
        for wp in waypoints:
            lat = wp["location"]["lat"]
            lng = wp["location"]["lng"]
            fill = wp.get("fill_level", 0)
            status = wp.get("status", "active")

            # Color based on fill level
            if fill >= 80 or status == "overflow":
                color = "red"
                icon  = "exclamation-circle"
            elif fill >= 50:
                color = "orange"
                icon  = "info-circle"
            else:
                color = "green"
                icon  = "check-circle"

            folium.Marker(
                [lat, lng],
                tooltip=f"Bin #{wp['order']} — {fill:.0f}% full",
                popup=folium.Popup(
                    f"<b>Bin #{wp['order']}</b><br>Fill: {fill:.0f}%<br>Status: {status}",
                    max_width=200,
                ),
                icon=folium.Icon(color=color, icon=icon, prefix="fa"),
            ).add_to(m)

        st_folium(m, width=700, height=420, returned_objects=[])

        if route.get("fallback"):
            st.caption("ℹ️ Using Haversine fallback routing (ORS API key not configured)")

    with list_col:
        st.markdown("#### 🗑️ Bins to Collect")
        if not waypoints:
            st.success("✅ No bins assigned. All done for today!")
        else:
            for wp in waypoints:
                fill   = wp.get("fill_level", 0)
                status = wp.get("status", "active")
                bin_id = wp.get("bin_id", "")
                color  = "🔴" if fill >= 80 else "🟡" if fill >= 50 else "🟢"

                with st.container():
                    col_info, col_btn = st.columns([3, 2])
                    with col_info:
                        st.markdown(
                            f"**#{wp['order']}** {color} {fill:.0f}%  \n"
                            f"<small style='color:#718096;'>Ward: {wp.get('ward_id','—')} | "
                            f"{status.title()}</small>",
                            unsafe_allow_html=True,
                        )
                    with col_btn:
                        if st.button(
                            "Collected ✓",
                            key=f"collect_{bin_id}",
                            use_container_width=True,
                        ):
                            _mark_collected(bin_id)

                    st.markdown("<hr style='margin:6px 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

    # ── Today's Stats ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Today's Stats")
    s1, s2, s3 = st.columns(3)
    s1.metric("Bins Collected Today", stats.get("bins_collected_today", 0))
    s2.metric("Total Collections",    stats.get("total_collections", 0))
    s3.metric("Points Earned",        stats.get("total_points", 0))


def _mark_collected(bin_id: str):
    with st.spinner("Marking as collected..."):
        resp = requests.post(
            f"{BACKEND_URL}/route/collect/{bin_id}",
            headers=get_headers(),
            timeout=15,
        )
    if resp.ok:
        show_toast("Bin collected! +5 points earned 🎉", "success")
        st.rerun()
    else:
        show_toast("Failed to mark bin as collected.", "error")
