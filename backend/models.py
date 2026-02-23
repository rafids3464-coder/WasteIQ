"""
WASTE IQ – Pydantic Models
All request/response schemas for the REST API.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
#  ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class UserRole(str, Enum):
    HOUSEHOLD = "household"
    MUNICIPAL = "municipal"
    DRIVER    = "driver"
    ADMIN     = "admin"

class WasteCategory(str, Enum):
    WET         = "Wet Waste"
    DRY         = "Dry Waste"
    HAZARDOUS   = "Hazardous Waste"
    RECYCLABLE  = "Recyclable"
    EWASTE      = "E-Waste"
    GENERAL     = "General Waste"

class RiskLevel(str, Enum):
    LOW    = "Low"
    MEDIUM = "Medium"
    HIGH   = "High"

class BinStatus(str, Enum):
    ACTIVE    = "active"
    COLLECTED = "collected"
    OVERFLOW  = "overflow"
    OFFLINE   = "offline"

class ComplaintStatus(str, Enum):
    OPEN       = "open"
    IN_REVIEW  = "in_review"
    RESOLVED   = "resolved"
    CLOSED     = "closed"

class BadgeTier(str, Enum):
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD   = "Gold"


# ═══════════════════════════════════════════════════════════════════════════════
#  USER MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class UserProfile(BaseModel):
    uid:          str
    email:        str
    name:         str
    role:         UserRole
    phone:        Optional[str] = None
    address:      Optional[str] = None
    ward_id:      Optional[str] = None
    language:     str = "en"
    avatar_url:   Optional[str] = None
    created_at:   Optional[str] = None

class UserUpdate(BaseModel):
    name:     Optional[str] = None
    phone:    Optional[str] = None
    address:  Optional[str] = None
    language: Optional[str] = None

class SignupRequest(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=6)
    name:     str
    role:     UserRole = UserRole.HOUSEHOLD
    ward_id:  Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  BIN MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class BinLocation(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = None

class BinDocument(BaseModel):
    bin_id:          str
    ward_id:         str
    location:        BinLocation
    fill_level:      float = Field(ge=0, le=100)  # percentage
    capacity_liters: float = 200.0
    status:          BinStatus = BinStatus.ACTIVE
    assigned_driver: Optional[str] = None
    last_collected:  Optional[str] = None
    sensor_id:       Optional[str] = None

class BinCreate(BaseModel):
    ward_id:         str
    location:        BinLocation
    fill_level:      float = 0.0
    capacity_liters: float = 200.0
    assigned_driver: Optional[str] = None

class BinUpdate(BaseModel):
    fill_level:      Optional[float] = None
    status:          Optional[BinStatus] = None
    assigned_driver: Optional[str] = None

class BinCollectedUpdate(BaseModel):
    driver_uid: str
    notes:      Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  CLASSIFICATION MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ClassificationResult(BaseModel):
    log_id:               str
    uid:                  str
    object_name:          str
    waste_category:       WasteCategory
    confidence:           float
    disposal_instructions: str
    recycling_tip:        str
    image_url:            Optional[str] = None
    timestamp:            str


# ═══════════════════════════════════════════════════════════════════════════════
#  OVERFLOW MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class OverflowInput(BaseModel):
    bin_id:             str
    fill_level:         float = Field(ge=0, le=100)
    hours_since_last:   float  # hours since last collection
    population_density: float  # people per sq km
    avg_daily_waste_kg: Optional[float] = 2.5

class OverflowPrediction(BaseModel):
    bin_id:              str
    overflow_probability: float
    risk_level:          RiskLevel
    predicted_at:        str
    hours_to_overflow:   Optional[float] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  COMPLAINT MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ComplaintCreate(BaseModel):
    title:       str
    description: str
    ward_id:     str
    bin_id:      Optional[str] = None
    location:    Optional[BinLocation] = None
    image_url:   Optional[str] = None

class ComplaintResponse(BaseModel):
    complaint_id: str
    title:        str
    description:  str
    ward_id:      str
    bin_id:       Optional[str] = None
    submitted_by: str
    status:       ComplaintStatus
    created_at:   str
    resolved_at:  Optional[str] = None
    resolution:   Optional[str] = None

class ComplaintResolve(BaseModel):
    resolution: str


# ═══════════════════════════════════════════════════════════════════════════════
#  GAMIFICATION MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Badge(BaseModel):
    name:        str
    tier:        BadgeTier
    description: str
    icon:        str
    earned_at:   Optional[str] = None

class GamificationProfile(BaseModel):
    uid:          str
    total_points: int = 0
    weekly_points: int = 0
    badges:       List[Badge] = []
    level:        str = "Beginner"

class LeaderboardEntry(BaseModel):
    rank:         int
    uid:          str
    name:         str
    role:         UserRole
    total_points: int
    badges_count: int


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTING MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class RouteWaypoint(BaseModel):
    bin_id:   str
    location: BinLocation
    fill_level: float
    order:    int

class DriverRoute(BaseModel):
    driver_uid:     str
    waypoints:      List[RouteWaypoint]
    total_distance_km: float
    eta_minutes:    float
    geojson:        Optional[Dict] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  RESPONSE WRAPPERS
# ═══════════════════════════════════════════════════════════════════════════════

class APIResponse(BaseModel):
    success: bool
    message: str
    data:    Optional[Any] = None

class PaginatedResponse(BaseModel):
    items:   List[Any]
    total:   int
    page:    int
    per_page: int
