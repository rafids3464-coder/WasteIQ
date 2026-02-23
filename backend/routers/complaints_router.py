"""WASTE IQ – Complaints Router"""
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user, require_municipal, UserInfo
from firestore_client import get_doc, add_doc, update_doc, query_collection, increment_field, get_doc
from models import ComplaintCreate, ComplaintResolve, APIResponse
from datetime import datetime, timezone
import uuid

router = APIRouter()

@router.post("/", response_model=APIResponse)
async def submit_complaint(payload: ComplaintCreate, user: UserInfo = Depends(get_current_user)):
    """Submit a new complaint."""
    complaint_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "complaint_id": complaint_id,
        "title":        payload.title,
        "description":  payload.description,
        "ward_id":      payload.ward_id,
        "bin_id":       payload.bin_id,
        "location":     payload.location.dict() if payload.location else None,
        "image_url":    payload.image_url,
        "submitted_by": user.uid,
        "status":       "open",
        "created_at":   now,
        "resolved_at":  None,
        "resolution":   None,
    }
    add_doc("complaints", doc)
    # Award +20 points for valid complaint
    try:
        _award_points(user.uid, 20)
    except Exception:
        pass
    return APIResponse(success=True, message="Complaint submitted", data=doc)

@router.get("/", response_model=APIResponse)
async def list_complaints(ward_id: str = None, status: str = None, user: UserInfo = Depends(get_current_user)):
    """List complaints filtered by role."""
    filters = []
    if user.role == "household":
        filters.append(("submitted_by", "==", user.uid))
    elif ward_id:
        filters.append(("ward_id", "==", ward_id))
    if status:
        filters.append(("status", "==", status))
    complaints = query_collection("complaints", filters=filters if filters else None,
                                  order_by="created_at", order_desc=True, limit=100)
    return APIResponse(success=True, message=f"{len(complaints)} complaints", data=complaints)

@router.patch("/{complaint_id}/resolve", response_model=APIResponse)
async def resolve_complaint(complaint_id: str, payload: ComplaintResolve,
                            user: UserInfo = Depends(require_municipal)):
    """Municipal/Admin: resolve a complaint."""
    complaint = query_collection("complaints", filters=[("complaint_id", "==", complaint_id)], limit=1)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    now = datetime.now(timezone.utc).isoformat()
    update_doc("complaints", complaint[0]["_id"], {
        "status":      "resolved",
        "resolved_at": now,
        "resolution":  payload.resolution,
        "resolved_by": user.uid,
    })
    # Award +10 points to municipal officer
    try:
        _award_points(user.uid, 10)
    except Exception:
        pass
    return APIResponse(success=True, message="Complaint resolved")

@router.get("/stats", response_model=APIResponse)
async def complaint_stats(ward_id: str = None, user: UserInfo = Depends(get_current_user)):
    """Return complaint statistics."""
    filters = []
    if ward_id:
        filters.append(("ward_id", "==", ward_id))
    elif user.role == "household":
        filters.append(("submitted_by", "==", user.uid))
    complaints = query_collection("complaints", filters=filters if filters else None)
    from collections import Counter
    by_status = Counter(c.get("status", "open") for c in complaints)
    return APIResponse(success=True, message="Stats", data={
        "total": len(complaints),
        "by_status": dict(by_status),
        "resolution_rate": round(by_status.get("resolved", 0) / max(len(complaints), 1) * 100, 1),
    })

def _award_points(uid: str, points: int):
    from firestore_client import get_doc, set_doc, increment_field
    existing = get_doc("gamification", uid)
    if not existing:
        set_doc("gamification", uid, {"uid": uid, "total_points": points, "weekly_points": points, "badges": [], "level": "Beginner"})
    else:
        increment_field("gamification", uid, "total_points", points)
        increment_field("gamification", uid, "weekly_points", points)
