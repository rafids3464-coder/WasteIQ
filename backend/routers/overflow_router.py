"""WASTE IQ – Overflow Router"""
from fastapi import APIRouter, Depends, HTTPException, Request
from auth import get_current_user, require_municipal, UserInfo
from firestore_client import query_collection
from models import OverflowInput, APIResponse

router = APIRouter()

@router.post("/predict", response_model=APIResponse)
async def predict_overflow(payload: OverflowInput, request: Request, user: UserInfo = Depends(get_current_user)):
    """Predict overflow probability for a single bin."""
    model = request.app.state.overflow_model
    import firestore_client as fc
    result = model.predict_and_save(
        bin_id=payload.bin_id,
        fill_level=payload.fill_level,
        hours_since_last=payload.hours_since_last,
        population_density=payload.population_density,
        avg_daily_waste_kg=payload.avg_daily_waste_kg or 2.5,
        firestore_client=fc,
    )
    return APIResponse(success=True, message="Prediction complete", data=result)

@router.post("/predict-batch", response_model=APIResponse)
async def predict_overflow_batch(ward_id: str = None, request: Request = None, user: UserInfo = Depends(require_municipal)):
    """Municipal/Admin: run predictions for all bins in a ward (or all bins)."""
    filters = [("ward_id", "==", ward_id)] if ward_id else None
    bins = query_collection("bins", filters=filters)
    if not bins:
        return APIResponse(success=True, message="No bins found", data=[])

    model = request.app.state.overflow_model
    import firestore_client as fc
    results = model.batch_predict(bins, fc)
    return APIResponse(success=True, message=f"Predicted {len(results)} bins", data=results)

@router.get("/history", response_model=APIResponse)
async def overflow_history(bin_id: str = None, limit: int = 50, user: UserInfo = Depends(get_current_user)):
    """Get overflow prediction history."""
    filters = [("bin_id", "==", bin_id)] if bin_id else None
    preds = query_collection("overflow_predictions", filters=filters,
                             order_by="predicted_at", order_desc=True, limit=limit)
    return APIResponse(success=True, message=f"{len(preds)} predictions", data=preds)

@router.get("/high-risk", response_model=APIResponse)
async def high_risk_bins(user: UserInfo = Depends(require_municipal)):
    """Return bins with High risk level from latest predictions."""
    high_risk = query_collection("overflow_predictions",
                                  filters=[("risk_level", "==", "High")],
                                  order_by="predicted_at", order_desc=True, limit=50)
    # Deduplicate by bin_id (latest prediction per bin)
    seen = set()
    unique = []
    for p in high_risk:
        if p["bin_id"] not in seen:
            seen.add(p["bin_id"])
            unique.append(p)
    return APIResponse(success=True, message=f"{len(unique)} high-risk bins", data=unique)
