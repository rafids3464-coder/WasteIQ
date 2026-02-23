"""WASTE IQ – Routing Router (Driver Routes)"""
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user, require_driver, require_municipal, UserInfo
from routing import RoutingService
import firestore_client as fc
from models import APIResponse

router = APIRouter()

def _get_routing():
    return RoutingService(fc)

@router.get("/optimize", response_model=APIResponse)
async def optimize_route(
    lat: float = None,
    lng: float = None,
    user: UserInfo = Depends(get_current_user)
):
    """Get optimized route for the current driver."""
    if user.role not in ("driver", "admin"):
        raise HTTPException(status_code=403, detail="Only drivers can access routes")

    svc   = _get_routing()
    depot = {"lat": lat, "lng": lng} if lat and lng else None
    route = svc.optimize_route(driver_uid=user.uid, depot=depot)
    return APIResponse(success=True, message="Route optimized", data=route)

@router.get("/optimize/{driver_uid}", response_model=APIResponse)
async def optimize_route_for_driver(driver_uid: str, user: UserInfo = Depends(require_municipal)):
    """Municipal/Admin: optimize route for a specific driver."""
    svc   = _get_routing()
    route = svc.optimize_route(driver_uid=driver_uid)
    return APIResponse(success=True, message="Route optimized", data=route)

@router.post("/collect/{bin_id}", response_model=APIResponse)
async def collect_bin(bin_id: str, notes: str = "", user: UserInfo = Depends(get_current_user)):
    """Mark a bin as collected and recalculate route."""
    if user.role not in ("driver", "admin"):
        raise HTTPException(status_code=403, detail="Only drivers can collect bins")

    svc       = _get_routing()
    collect   = svc.mark_collected(bin_id=bin_id, driver_uid=user.uid, notes=notes)
    new_route = svc.optimize_route(driver_uid=user.uid)
    return APIResponse(success=True, message="Bin collected, route updated", data={
        "collection":  collect,
        "updated_route": new_route,
    })

@router.get("/stats", response_model=APIResponse)
async def driver_stats(user: UserInfo = Depends(get_current_user)):
    """Driver's collection statistics."""
    if user.role not in ("driver", "admin"):
        raise HTTPException(status_code=403, detail="Only drivers can view stats")
    svc   = _get_routing()
    stats = svc.get_driver_stats(driver_uid=user.uid)
    return APIResponse(success=True, message="Stats", data=stats)
