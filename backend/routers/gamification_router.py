"""WASTE IQ – Gamification Router"""
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user, require_admin, UserInfo
from firestore_client import get_doc, set_doc, query_collection
from models import APIResponse
from datetime import datetime, timezone

router = APIRouter()

BADGE_THRESHOLDS = [
    {"name": "First Step",     "tier": "Bronze", "description": "Classified first waste item",   "icon": "🥉", "points": 5},
    {"name": "Eco Starter",    "tier": "Bronze", "description": "Earned 50 points",              "icon": "🌱", "points": 50},
    {"name": "Green Guardian", "tier": "Silver", "description": "Earned 200 points",             "icon": "🥈", "points": 200},
    {"name": "Waste Warrior",  "tier": "Silver", "description": "Earned 500 points",             "icon": "⚔️", "points": 500},
    {"name": "Eco Champion",   "tier": "Gold",   "description": "Earned 1000 points",            "icon": "🏆", "points": 1000},
    {"name": "Planet Protector","tier": "Gold",  "description": "Earned 2500 points",            "icon": "🌍", "points": 2500},
]

LEVEL_THRESHOLDS = [
    (2500, "Legend"),
    (1000, "Champion"),
    (500,  "Warrior"),
    (200,  "Guardian"),
    (50,   "Starter"),
    (0,    "Beginner"),
]

def compute_level(total_points: int) -> str:
    for threshold, level in LEVEL_THRESHOLDS:
        if total_points >= threshold:
            return level
    return "Beginner"

@router.get("/me", response_model=APIResponse)
async def my_gamification(user: UserInfo = Depends(get_current_user)):
    """Get current user's gamification profile."""
    gam = get_doc("gamification", user.uid)
    if not gam:
        gam = {"uid": user.uid, "total_points": 0, "weekly_points": 0, "badges": [], "level": "Beginner"}
        set_doc("gamification", user.uid, gam)

    # Check and award new badges
    total = gam.get("total_points", 0)
    earned_names = {b["name"] for b in gam.get("badges", [])}
    new_badges = []
    for badge in BADGE_THRESHOLDS:
        if badge["name"] not in earned_names and total >= badge["points"]:
            b = {**badge, "earned_at": datetime.now(timezone.utc).isoformat()}
            new_badges.append(b)

    if new_badges:
        all_badges = gam.get("badges", []) + new_badges
        level = compute_level(total)
        from firestore_client import update_doc
        update_doc("gamification", user.uid, {"badges": all_badges, "level": level})
        gam["badges"] = all_badges
        gam["level"]  = level

    return APIResponse(success=True, message="Gamification profile", data=gam)

@router.get("/leaderboard", response_model=APIResponse)
async def leaderboard(limit: int = 20, user: UserInfo = Depends(get_current_user)):
    """Return top-N users by points."""
    entries = query_collection("gamification", order_by="total_points", order_desc=True, limit=limit)
    result = []
    for i, e in enumerate(entries):
        user_profile = get_doc("users", e.get("uid", "")) or {}
        result.append({
            "rank":         i + 1,
            "uid":          e.get("uid"),
            "name":         user_profile.get("name", "Anonymous"),
            "role":         user_profile.get("role", "household"),
            "total_points": e.get("total_points", 0),
            "level":        e.get("level", "Beginner"),
            "badges_count": len(e.get("badges", [])),
        })
    return APIResponse(success=True, message=f"Top {len(result)} users", data=result)

@router.get("/rewards", response_model=APIResponse)
async def reward_catalog(user: UserInfo = Depends(get_current_user)):
    """Simulated reward catalog."""
    catalog = [
        {"id": "r1", "name": "Eco Bag",          "points_required": 100,  "description": "Reusable shopping bag",          "icon": "👜"},
        {"id": "r2", "name": "Plant Sapling",     "points_required": 250,  "description": "Free sapling from city nursery", "icon": "🌱"},
        {"id": "r3", "name": "Bus Pass (1 day)",  "points_required": 500,  "description": "City bus day pass",             "icon": "🚌"},
        {"id": "r4", "name": "Solar Lamp",        "points_required": 1000, "description": "Solar-powered garden lamp",      "icon": "💡"},
        {"id": "r5", "name": "Composting Kit",    "points_required": 1500, "description": "Home composting starter kit",   "icon": "♻️"},
        {"id": "r6", "name": "Recycling Award",   "points_required": 2500, "description": "Official city recycling award", "icon": "🏆"},
    ]
    gam = get_doc("gamification", user.uid) or {"total_points": 0}
    user_points = gam.get("total_points", 0)
    for item in catalog:
        item["can_redeem"] = user_points >= item["points_required"]
    return APIResponse(success=True, message="Reward catalog", data={"catalog": catalog, "user_points": user_points})
