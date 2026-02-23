"""WASTE IQ – Auth Router"""
from fastapi import APIRouter, Depends, HTTPException, Body
from auth import get_current_user, set_user_role, create_user, list_all_users, require_admin, UserInfo
from firestore_client import get_doc, set_doc, update_doc
from models import SignupRequest, UserProfile, UserUpdate, APIResponse
from datetime import datetime, timezone

router = APIRouter()

@router.post("/signup", response_model=APIResponse)
async def signup(payload: SignupRequest):
    """Create a new Firebase Auth user + Firestore user profile."""
    try:
        uid = create_user(payload.email, payload.password, payload.name)
        set_user_role(uid, payload.role.value)
        set_doc("users", uid, {
            "uid":        uid,
            "email":      payload.email,
            "name":       payload.name,
            "role":       payload.role.value,
            "ward_id":    payload.ward_id,
            "phone":      None,
            "address":    None,
            "language":   "en",
            "avatar_url": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        # Init gamification
        set_doc("gamification", uid, {
            "uid": uid, "total_points": 0, "weekly_points": 0,
            "badges": [], "level": "Beginner",
        })
        return APIResponse(success=True, message="User created successfully", data={"uid": uid})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me", response_model=APIResponse)
async def get_me(user: UserInfo = Depends(get_current_user)):
    """Return the current user's profile from Firestore."""
    profile = get_doc("users", user.uid)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return APIResponse(success=True, message="OK", data=profile)

@router.patch("/me", response_model=APIResponse)
async def update_me(payload: UserUpdate, user: UserInfo = Depends(get_current_user)):
    """Update editable profile fields."""
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if updates:
        update_doc("users", user.uid, updates)
    return APIResponse(success=True, message="Profile updated", data=updates)

@router.get("/users", response_model=APIResponse)
async def list_users(admin: UserInfo = Depends(require_admin)):
    """Admin: list all Firebase Auth users."""
    users = list_all_users()
    return APIResponse(success=True, message=f"{len(users)} users", data=users)

@router.patch("/users/{uid}/role", response_model=APIResponse)
async def set_role(uid: str, role: str = Body(..., embed=True), admin: UserInfo = Depends(require_admin)):
    """Admin: change a user's role."""
    set_user_role(uid, role)
    update_doc("users", uid, {"role": role})
    return APIResponse(success=True, message=f"Role updated to {role}")
