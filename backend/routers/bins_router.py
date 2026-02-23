"""WASTE IQ – Bins Router"""
from fastapi import APIRouter, Depends, HTTPException, Request
from auth import get_current_user, require_municipal, require_admin, require_driver, UserInfo
from firestore_client import get_doc, set_doc, add_doc, update_doc, query_collection
from models import BinCreate, BinUpdate, BinCollectedUpdate, APIResponse
from datetime import datetime, timezone
import uuid

router = APIRouter()

@router.get("/", response_model=APIResponse)
async def list_bins(ward_id: str = None, user: UserInfo = Depends(get_current_user)):
    """List bins. Household/Driver see assigned bins; Municipal/Admin see ward or all."""
    filters = []
    if ward_id:
        filters.append(("ward_id", "==", ward_id))
    if user.role == "driver":
        filters.append(("assigned_driver", "==", user.uid))
    bins = query_collection("bins", filters=filters if filters else None)
    return APIResponse(success=True, message=f"{len(bins)} bins", data=bins)

@router.get("/{bin_id}", response_model=APIResponse)
async def get_bin(bin_id: str, user: UserInfo = Depends(get_current_user)):
    bin_doc = get_doc("bins", bin_id)
    if not bin_doc:
        raise HTTPException(status_code=404, detail="Bin not found")
    return APIResponse(success=True, message="OK", data=bin_doc)

@router.post("/", response_model=APIResponse)
async def create_bin(payload: BinCreate, user: UserInfo = Depends(require_municipal)):
    """Municipal/Admin: create a new bin."""
    bin_id = str(uuid.uuid4())
    doc = {
        "bin_id":          bin_id,
        "ward_id":         payload.ward_id,
        "location":        payload.location.dict(),
        "fill_level":      payload.fill_level,
        "capacity_liters": payload.capacity_liters,
        "status":          "active",
        "assigned_driver": payload.assigned_driver,
        "last_collected":  None,
        "created_at":      datetime.now(timezone.utc).isoformat(),
    }
    set_doc("bins", bin_id, doc)
    return APIResponse(success=True, message="Bin created", data=doc)

@router.patch("/{bin_id}", response_model=APIResponse)
async def update_bin(bin_id: str, payload: BinUpdate, user: UserInfo = Depends(require_municipal)):
    """Municipal/Admin: update bin fields."""
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_doc("bins", bin_id, updates)
    return APIResponse(success=True, message="Bin updated", data=updates)

@router.post("/{bin_id}/collected", response_model=APIResponse)
async def mark_collected(bin_id: str, payload: BinCollectedUpdate, user: UserInfo = Depends(get_current_user)):
    """Driver: mark a bin as collected."""
    if user.role not in ("driver", "admin"):
        raise HTTPException(status_code=403, detail="Only drivers can mark bins as collected")
    now = datetime.now(timezone.utc).isoformat()
    update_doc("bins", bin_id, {
        "fill_level":     0.0,
        "status":         "collected",
        "last_collected": now,
        "driver_uid":     user.uid,
    })
    add_doc("collection_logs", {
        "bin_id":       bin_id,
        "driver_uid":   user.uid,
        "collected_at": now,
        "notes":        payload.notes,
    })
    # Points
    try:
        _award_points(user.uid, 5)
    except Exception:
        pass
    return APIResponse(success=True, message="Bin marked as collected", data={"bin_id": bin_id, "collected_at": now})

@router.delete("/{bin_id}", response_model=APIResponse)
async def delete_bin(bin_id: str, user: UserInfo = Depends(require_admin)):
    from firestore_client import delete_doc
    delete_doc("bins", bin_id)
    return APIResponse(success=True, message="Bin deleted")

def _award_points(uid: str, points: int):
    from firestore_client import get_doc, set_doc, increment_field
    existing = get_doc("gamification", uid)
    if not existing:
        set_doc("gamification", uid, {"uid": uid, "total_points": points, "weekly_points": points, "badges": [], "level": "Beginner"})
    else:
        increment_field("gamification", uid, "total_points", points)
        increment_field("gamification", uid, "weekly_points", points)
