"""WASTE IQ – Notifications Page"""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from utils import page_header, api_get


def show():
    page_header("🔔 Notifications", "Real-time updates and system alerts")

    # Pull overflow + complaints data to build notifications
    with st.spinner("Loading notifications..."):
        overflow  = api_get("/overflow/high-risk")
        comp_data = api_get("/complaints/")

    high_risk  = overflow["data"]   if overflow   else []
    complaints = comp_data["data"]  if comp_data  else []
    uid        = st.session_state.get("uid")
    role       = st.session_state.get("role","household")

    notifications = []

    # System alerts for high-risk bins
    if role in ("admin","municipal","driver"):
        for hr in high_risk[:5]:
            notifications.append({
                "type":    "danger",
                "icon":    "🔴",
                "title":   f"High-Risk Bin Detected",
                "body":    f"Bin {hr.get('bin_id','')[:12]} has overflow probability {hr.get('overflow_probability',0)*100:.0f}%",
                "time":    hr.get("predicted_at",""),
                "read":    False,
            })

    # Complaint status updates for household
    if role == "household":
        for c in [c for c in complaints if c.get("status") == "resolved"][:5]:
            notifications.append({
                "type":  "success",
                "icon":  "✅",
                "title": "Complaint Resolved",
                "body":  f"Your complaint '{c.get('title','')[:40]}' has been resolved.",
                "time":  c.get("resolved_at",""),
                "read":  False,
            })

    # Points milestones
    gam_data = api_get("/gamification/me")
    if gam_data:
        gam = gam_data["data"]
        pts = gam.get("total_points",0)
        if pts > 0:
            notifications.append({
                "type":  "info",
                "icon":  "⭐",
                "title": "Points Update",
                "body":  f"You have earned {pts} total points! Keep classifying waste to level up.",
                "time":  "",
                "read":  True,
            })
        for badge in gam.get("badges",[])[:2]:
            notifications.append({
                "type":  "success",
                "icon":  badge["icon"],
                "title": f"Badge Unlocked: {badge['name']}",
                "body":  badge["description"],
                "time":  badge.get("earned_at",""),
                "read":  False,
            })

    if not notifications:
        notifications.append({
            "type":  "info",
            "icon":  "ℹ️",
            "title": "Welcome to WASTE IQ!",
            "body":  "Start classifying waste items to earn points and unlock badges.",
            "time":  "",
            "read":  True,
        })

    # Filter
    col_filter, _ = st.columns([2, 4])
    show_unread = col_filter.toggle("Show unread only", value=False)
    to_show = [n for n in notifications if not n["read"]] if show_unread else notifications

    st.markdown(f"**{len(to_show)} notification(s)**")
    st.markdown("---")

    color_map = {
        "danger":  ("#f8d7da","#721c24","#dc3545"),
        "success": ("#d4edda","#155724","#28a745"),
        "info":    ("#cce5ff","#004085","#0d6efd"),
        "warning": ("#fff3cd","#856404","#ffc107"),
    }

    for n in to_show:
        bg, text, border = color_map.get(n["type"], ("#f0f4f8","#4a5568","#94a3b8"))
        unread_dot = '<span style="width:8px;height:8px;border-radius:50%;background:#ef4444;display:inline-block;margin-left:8px;"></span>' if not n["read"] else ""
        time_str = ""
        if n.get("time"):
            try:
                time_str = pd.to_datetime(n["time"]).strftime("%b %d, %H:%M")
            except Exception:
                pass

        st.markdown(
            f"""<div style="background:{bg};border-left:4px solid {border};border-radius:8px;
                 padding:14px 16px;margin-bottom:10px;color:{text};">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="font-weight:700;font-size:14px;">{n['icon']} {n['title']}{unread_dot}</div>
                <div style="font-size:11px;opacity:0.7;">{time_str}</div>
              </div>
              <div style="font-size:13px;margin-top:4px;">{n['body']}</div>
            </div>""",
            unsafe_allow_html=True,
        )
