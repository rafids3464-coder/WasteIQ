"""WASTE IQ – User Profile Page"""

import streamlit as st
from utils import page_header, api_get, api_patch, show_toast, BACKEND_URL, get_headers
from languages import t, LANGUAGE_NAMES
import requests


def show():
    page_header("👤 My Profile", "Manage your account settings and preferences")

    with st.spinner("Loading profile..."):
        data = api_get("/auth/me")
    profile = data["data"] if data else {}

    col_info, col_settings = st.columns([3, 2])

    # ── Profile Info ──────────────────────────────────────────────────────
    with col_info:
        st.markdown("#### Personal Information")
        with st.form("profile_form"):
            name    = st.text_input("Full Name", value=profile.get("name",""))
            email   = st.text_input("Email", value=profile.get("email",""), disabled=True,
                                    help="Email cannot be changed here")
            phone   = st.text_input("Phone Number", value=profile.get("phone") or "",
                                    placeholder="+91 98765 43210")
            address = st.text_area("Address", value=profile.get("address") or "",
                                   placeholder="Your home/office address", height=80)
            ward_id = st.text_input("Ward ID", value=profile.get("ward_id") or "",
                                    placeholder="e.g. WARD_01")

            save = st.form_submit_button("💾 Save Changes", use_container_width=True)

        if save:
            payload = {"name": name, "phone": phone or None, "address": address or None}
            result  = api_patch("/auth/me", json_data=payload)
            if result and result.get("success"):
                st.session_state.name = name
                if ward_id:
                    st.session_state.ward_id = ward_id
                show_toast("Profile updated ✅", "success")
                st.rerun()
            else:
                show_toast("Failed to update profile.", "error")

    # ── Settings ──────────────────────────────────────────────────────────
    with col_settings:
        st.markdown("#### Preferences")

        # Language preference
        lang_options = list(LANGUAGE_NAMES.keys())
        current_lang = st.session_state.get("language","en")
        sel_lang = st.selectbox(
            f"🌐 {t('lbl_language')}",
            options=lang_options,
            format_func=lambda x: LANGUAGE_NAMES[x],
            index=lang_options.index(current_lang) if current_lang in lang_options else 0,
        )
        if st.button("Save Language Preference", use_container_width=True):
            st.session_state.language = sel_lang
            result = api_patch("/auth/me", json_data={"language": sel_lang})
            if result:
                show_toast(f"Language set to {LANGUAGE_NAMES[sel_lang]}", "success")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Account Info")
        st.markdown(f"**Role:** {profile.get('role','household').title()}")
        st.markdown(f"**UID:** `{profile.get('uid','—')[:16]}...`")
        if profile.get("created_at"):
            import pandas as pd
            st.markdown(f"**Member since:** {pd.to_datetime(profile['created_at']).strftime('%B %d, %Y')}")

        # Gamification summary
        st.markdown("---")
        gam_data = api_get("/gamification/me")
        if gam_data:
            gam = gam_data["data"]
            st.markdown("#### My Stats")
            st.metric("Total Points", gam.get("total_points",0))
            st.metric("Level",        gam.get("level","Beginner"))
            st.metric("Badges Earned",len(gam.get("badges",[])))
