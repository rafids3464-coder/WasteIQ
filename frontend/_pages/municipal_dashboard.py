"""WASTE IQ – Municipal Officer Dashboard"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import page_header, kpi_card, api_get, show_toast, time_greeting
from languages import t


def show():
    page_header(
        f"{time_greeting()}, {st.session_state.name} 🏛️",
        "Municipal officer overview — ward health and compliance"
    )

    ward_id = st.session_state.get("ward_id")

    with st.spinner("Loading ward data..."):
        bins_data      = api_get("/bins/",       params={"ward_id": ward_id})
        comp_data      = api_get("/complaints/", params={"ward_id": ward_id})
        overflow_data  = api_get("/overflow/high-risk")
        city_data      = api_get("/reports/city-summary")

    bins       = bins_data["data"]   if bins_data      else []
    complaints = comp_data["data"]   if comp_data      else []
    high_risk  = overflow_data["data"] if overflow_data else []
    city       = city_data["data"]   if city_data      else {}

    open_comp      = sum(1 for c in complaints if c.get("status") == "open")
    resolved_comp  = sum(1 for c in complaints if c.get("status") == "resolved")
    total_comp     = len(complaints)
    overflow_bins  = sum(1 for b in bins if b.get("status") == "overflow")
    res_rate       = round(resolved_comp / max(total_comp, 1) * 100, 1)

    # ── KPI Row ───────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("🗑️", len(bins),      "Total Bins",          "#1a7a4a")
    with c2: kpi_card("🔴", overflow_bins,  t("dash_bins_at_risk"), "#ef4444" if overflow_bins > 0 else "#22c55e")
    with c3: kpi_card("📢", open_comp,      "Open Complaints",      "#f59e0b" if open_comp > 0 else "#22c55e")
    with c4: kpi_card("✅", f"{res_rate}%", "Resolution Rate",      "#22c55e" if res_rate > 70 else "#f59e0b")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts Row ────────────────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown("#### 📊 Bin Fill Levels by Ward")
        if bins:
            df = pd.DataFrame(bins)
            df = df.sort_values("fill_level", ascending=False)
            fig = px.bar(
                df.head(20), x="_id", y="fill_level",
                color="fill_level",
                color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444"],
                range_color=[0, 100],
                labels={"_id": "Bin ID", "fill_level": "Fill Level (%)"},
                title="Top 20 Bins by Fill Level",
            )
            fig.add_hline(y=80, line_dash="dash", line_color="#ef4444",
                          annotation_text="Overflow threshold (80%)")
            fig.update_layout(
                height=280, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_family="Inter", coloraxis_showscale=False,
                margin=dict(l=0,r=0,t=40,b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No bin data available for this ward.")

    with right:
        st.markdown("#### 📢 Complaints by Status")
        if complaints:
            from collections import Counter
            status_counts = Counter(c.get("status", "open") for c in complaints)
            colors_map = {"open": "#ef4444", "in_review": "#f59e0b",
                          "resolved": "#22c55e", "closed": "#94a3b8"}
            fig2 = px.pie(
                names=list(status_counts.keys()),
                values=list(status_counts.values()),
                color=list(status_counts.keys()),
                color_discrete_map=colors_map,
                hole=0.5,
            )
            fig2.update_layout(
                height=280, margin=dict(l=0,r=0,t=20,b=0),
                paper_bgcolor="rgba(0,0,0,0)", font_family="Inter",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.caption("No complaint data.")

    st.markdown("---")

    # ── High Risk Bins + Complaints Table ─────────────────────────────────
    hr_col, comp_col = st.columns([1, 1])

    with hr_col:
        st.markdown("#### ⚠️ High-Risk Bins")
        if high_risk:
            risk_rows = [{
                "Bin ID":       h.get("bin_id", "—")[:12],
                "Probability":  f"{h.get('overflow_probability', 0)*100:.0f}%",
                "Risk":         h.get("risk_level", "—"),
                "Predicted At": pd.to_datetime(h.get("predicted_at","")).strftime("%b %d %H:%M") if h.get("predicted_at") else "—",
            } for h in high_risk[:10]]
            st.dataframe(pd.DataFrame(risk_rows), use_container_width=True, hide_index=True)
        else:
            st.success("✅ No high-risk bins detected.")

    with comp_col:
        st.markdown("#### 📋 Recent Complaints")
        if complaints:
            comp_rows = [{
                "Title":    c.get("title","—")[:30],
                "Ward":     c.get("ward_id","—"),
                "Status":   c.get("status","open").replace("_"," ").title(),
                "Date":     pd.to_datetime(c.get("created_at","")).strftime("%b %d") if c.get("created_at") else "—",
            } for c in complaints[:10]]
            st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)
        else:
            st.success("✅ No complaints found.")

    # ── Resolve a Complaint ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ✅ Resolve a Complaint")
    open_complaints = [c for c in complaints if c.get("status") == "open"]
    if open_complaints:
        options = {f"{c.get('title','...')} ({c.get('complaint_id','')[:8]})": c.get("complaint_id") 
                   for c in open_complaints}
        selected_label = st.selectbox("Select complaint to resolve", list(options.keys()))
        complaint_id   = options.get(selected_label)
        resolution     = st.text_area("Resolution notes", placeholder="Describe how it was resolved...")
        if st.button("✅ Mark as Resolved — +10 pts", use_container_width=True):
            if resolution:
                result = api_get(f"/complaints/{complaint_id}/resolve")  # placeholder
                import requests, os
                from utils import BACKEND_URL, get_headers
                resp = requests.patch(
                    f"{BACKEND_URL}/complaints/{complaint_id}/resolve",
                    headers=get_headers(),
                    json={"resolution": resolution},
                    timeout=10,
                )
                if resp.ok:
                    show_toast("Complaint resolved! +10 points 🎉", "success")
                    st.rerun()
                else:
                    show_toast("Failed to resolve complaint.", "error")
            else:
                st.warning("Please provide resolution notes.")
    else:
        st.success("✅ All complaints resolved!")

    # ── Batch overflow prediction ──────────────────────────────────────────
    with st.expander("🤖 Run Overflow Predictions for Ward"):
        if st.button("Run Predictions Now", use_container_width=True):
            with st.spinner("Running ML overflow model..."):
                import requests, os
                from utils import BACKEND_URL, get_headers
                resp = requests.post(
                    f"{BACKEND_URL}/overflow/predict-batch",
                    headers=get_headers(),
                    params={"ward_id": ward_id},
                    timeout=60,
                )
                if resp.ok:
                    results = resp.json().get("data", [])
                    show_toast(f"Predicted {len(results)} bins! Results saved.", "success")
                    st.rerun()
                else:
                    show_toast("Prediction failed.", "error")
