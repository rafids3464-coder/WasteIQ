"""WASTE IQ – Complaints Page"""

import streamlit as st
import pandas as pd
from utils import page_header, api_get, api_post, show_toast
from languages import t


def show():
    page_header("📢 Complaints", "Track and submit waste-related complaints in your area")

    tab_list, tab_new = st.tabs(["📋 My Complaints", f"➕ {t('comp_new')}"])

    # ── My Complaints ─────────────────────────────────────────────────────
    with tab_list:
        with st.spinner("Loading complaints..."):
            data = api_get("/complaints/")
        complaints = data["data"] if data else []

        if complaints:
            statuses = ["All"] + list({c.get("status", "open") for c in complaints})
            sel_status = st.selectbox("Filter by Status", statuses, key="comp_status_filter")
            filtered = complaints if sel_status == "All" else [
                c for c in complaints if c.get("status") == sel_status
            ]
            status_color = {"open": "🔴", "in_review": "🟡", "resolved": "🟢", "closed": "⚫"}
            for comp in filtered:
                status = comp.get("status", "open")
                icon   = status_color.get(status, "⚪")
                with st.expander(f"{icon} {comp.get('title','—')} — {status.replace('_',' ').title()}"):
                    col1, col2 = st.columns(2)
                    col1.markdown(f"**Ward:** {comp.get('ward_id','—')}")
                    col1.markdown(f"**Status:** {status.replace('_',' ').title()}")
                    if comp.get("location_text"):
                        col1.markdown(f"**📍 Location:** {comp['location_text']}")
                    submitted_at = comp.get("created_at", "")
                    col2.markdown(f"**Submitted:** {pd.to_datetime(submitted_at).strftime('%b %d, %Y') if submitted_at else '—'}")
                    if comp.get("resolved_at"):
                        col2.markdown(f"**Resolved:** {pd.to_datetime(comp['resolved_at']).strftime('%b %d, %Y')}")
                    st.write(f"**Description:** {comp.get('description','—')}")
                    if comp.get("resolution"):
                        st.success(f"**Resolution:** {comp['resolution']}")
        else:
            st.info("No complaints found. Submit your first complaint using the tab above.")

    # ── New Complaint ─────────────────────────────────────────────────────
    with tab_new:
        st.markdown("#### Submit a New Complaint")
        st.info("After submission you'll be awarded **+20 points** for helping improve your city! 🌱")

        with st.form("new_complaint_form"):
            title         = st.text_input(f"🏷️ {t('comp_title')}*", placeholder="e.g. Overflowing bin near bus stop")
            desc          = st.text_area(f"📝 {t('comp_desc')}*", placeholder="Describe the issue in detail...", height=120)
            ward_id       = st.text_input("🏙️ Ward ID*", value=st.session_state.get("ward_id") or "", placeholder="WARD_01")
            location_text = st.text_input("📍 Location / Landmark", placeholder="e.g. Near City Park Gate 3, MG Road")
            bin_id        = st.text_input("🗑️ Bin ID (optional)", placeholder="Leave blank if unsure")
            submitted     = st.form_submit_button(f"📤 {t('comp_submit')}", use_container_width=True)

        if submitted:
            if not title or not desc or not ward_id:
                st.error("Please fill in Title, Description, and Ward ID.")
            else:
                payload = {
                    "title":         title,
                    "description":   desc,
                    "ward_id":       ward_id,
                    "bin_id":        bin_id or None,
                    "location_text": location_text or None,
                }
                result = api_post("/complaints/", json_data=payload)
                if result and result.get("success"):
                    show_toast("Complaint submitted! +20 points earned 🎉", "success")
                    st.session_state.active_page = "complaints"
                    st.rerun()
                else:
                    show_toast("Failed to submit complaint. Please try again.", "error")
