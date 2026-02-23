"""WASTE IQ – Rewards Page"""

import streamlit as st
import pandas as pd
from utils import page_header, kpi_card, api_get, show_toast
from languages import t


def show():
    page_header("🏆 Rewards & Leaderboard", "Earn points, unlock badges, climb the leaderboard")

    with st.spinner("Loading rewards..."):
        gam_data  = api_get("/gamification/me")
        lb_data   = api_get("/gamification/leaderboard", params={"limit": 20})
        rew_data  = api_get("/gamification/rewards")

    gam       = gam_data["data"]  if gam_data  else {}
    lb        = lb_data["data"]   if lb_data   else []
    rewards   = rew_data["data"]  if rew_data  else {}

    total_pts  = gam.get("total_points", 0)
    weekly_pts = gam.get("weekly_points", 0)
    level      = gam.get("level", "Beginner")
    badges     = gam.get("badges", [])

    # ── KPI Row ───────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("⭐", total_pts,  "Total Points",  "#f59e0b")
    with c2: kpi_card("📅", weekly_pts, "This Week",     "#3b82f6")
    with c3: kpi_card("🏅", level,      "Your Level",    "#8b5cf6")
    with c4: kpi_card("🎖️", len(badges),"Badges Earned", "#22c55e")

    # Points to next level
    level_map = {"Beginner": 50, "Starter": 200, "Guardian": 500, "Warrior": 1000, "Champion": 2500, "Legend": None}
    next_pts  = level_map.get(level)
    if next_pts:
        progress = min(total_pts / next_pts, 1.0)
        st.progress(progress, text=f"{total_pts} / {next_pts} pts to next level")

    st.markdown("---")

    tab_badges, tab_lb, tab_rewards = st.tabs(["🎖️ My Badges", "🏆 Leaderboard", "🎁 Reward Catalog"])

    # ── Badges Tab ────────────────────────────────────────────────────────
    with tab_badges:
        ALL_BADGES = [
            {"name": "First Step",      "tier": "Bronze", "icon": "🥉", "description": "Classified first waste item",   "points": 5},
            {"name": "Eco Starter",     "tier": "Bronze", "icon": "🌱", "description": "Earned 50 points",              "points": 50},
            {"name": "Green Guardian",  "tier": "Silver", "icon": "🥈", "description": "Earned 200 points",             "points": 200},
            {"name": "Waste Warrior",   "tier": "Silver", "icon": "⚔️", "description": "Earned 500 points",            "points": 500},
            {"name": "Eco Champion",    "tier": "Gold",   "icon": "🏆", "description": "Earned 1000 points",           "points": 1000},
            {"name": "Planet Protector","tier": "Gold",   "icon": "🌍", "description": "Earned 2500 points",           "points": 2500},
        ]
        earned_names = {b["name"] for b in badges}
        cols = st.columns(3)
        for i, badge in enumerate(ALL_BADGES):
            is_earned = badge["name"] in earned_names
            tier_cls  = f"tier-{badge['tier'].lower()}"
            earned_cls = "earned" if is_earned else ""
            lock_icon  = "" if is_earned else "🔒"
            with cols[i % 3]:
                st.markdown(
                    f"""<div class="badge-card {earned_cls}" style="opacity:{'1' if is_earned else '0.55'};">
                      <div class="badge-icon">{badge['icon']} {lock_icon}</div>
                      <div class="badge-name">{badge['name']}</div>
                      <div class="badge-desc">{badge['description']}</div>
                      <div class="badge-tier {tier_cls}">{badge['tier']} · {badge['points']} pts</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ── Leaderboard Tab ───────────────────────────────────────────────────
    with tab_lb:
        if lb:
            uid = st.session_state.get("uid")
            for entry in lb:
                rank = entry["rank"]
                is_me = entry.get("uid") == uid

                if rank == 1:   rank_cls, rank_icon = "rank-1",     "🥇"
                elif rank == 2: rank_cls, rank_icon = "rank-2",     "🥈"
                elif rank == 3: rank_cls, rank_icon = "rank-3",     "🥉"
                else:           rank_cls, rank_icon = "rank-other", str(rank)

                highlight = "border:2px solid #1a7a4a;" if is_me else ""
                st.markdown(
                    f"""<div class="leaderboard-item" style="{highlight}">
                      <div class="leaderboard-rank {rank_cls}">{rank_icon}</div>
                      <div style="flex:1;">
                        <div style="font-weight:700;font-size:14px;">
                          {entry.get('name','—')} {'<span style="color:#1a7a4a;font-size:11px;">(You)</span>' if is_me else ''}
                        </div>
                        <div style="font-size:12px;color:#718096;">{entry.get('role','household').title()} · {entry.get('level','Beginner')}</div>
                      </div>
                      <div style="font-weight:800;font-size:18px;color:#f59e0b;">⭐ {entry.get('total_points',0)}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Leaderboard is empty. Start classifying waste to earn points!")

    # ── Reward Catalog Tab ────────────────────────────────────────────────
    with tab_rewards:
        catalog    = rewards.get("catalog", [])
        user_pts   = rewards.get("user_points", total_pts)

        st.info(f"💰 You have **{user_pts} points**. Redeem them for eco rewards!")

        if catalog:
            cols = st.columns(3)
            for i, item in enumerate(catalog):
                can_redeem = item.get("can_redeem", False)
                with cols[i % 3]:
                    border = "2px solid #1a7a4a" if can_redeem else "1px solid #e2e8f0"
                    opacity = "1" if can_redeem else "0.6"
                    btn_label = "✅ Redeem" if can_redeem else f"🔒 Need {item['points_required']} pts"
                    st.markdown(
                        f"""<div style="padding:1.25rem;border:{border};border-radius:12px;
                             text-align:center;margin-bottom:12px;opacity:{opacity};
                             background:#fff;">
                          <div style="font-size:36px;">{item['icon']}</div>
                          <div style="font-weight:700;margin-top:8px;">{item['name']}</div>
                          <div style="font-size:12px;color:#718096;margin:4px 0 8px;">{item['description']}</div>
                          <div style="font-weight:800;color:#f59e0b;">⭐ {item['points_required']} pts</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    if st.button(btn_label, key=f"redeem_{item['id']}", disabled=not can_redeem, use_container_width=True):
                        show_toast(f"🎉 {item['name']} redeemed! (Simulated)", "success")
