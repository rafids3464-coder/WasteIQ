"""
WASTE IQ – Driver Routing Service
Uses OpenRouteService API for real route optimization.
Falls back to simple Haversine distance ordering if ORS is unavailable.
"""

import os
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
ORS_API_KEY  = os.getenv("ORS_API_KEY", "")
ORS_BASE_URL = "https://api.openrouteservice.org/v2"


# ── Haversine distance (fallback) ─────────────────────────────────────────────
def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in kilometres between two lat/lng points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl   = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Nearest-neighbour TSP (fallback ordering) ──────────────────────────────────
def _nn_tsp(depot: Tuple, bins: List[Dict]) -> List[Dict]:
    """Order bins using greedy nearest-neighbour from depot."""
    remaining = bins[:]
    ordered   = []
    current   = depot
    while remaining:
        nearest = min(remaining, key=lambda b: _haversine(
            current[0], current[1],
            b["location"]["lat"], b["location"]["lng"]
        ))
        ordered.append(nearest)
        current = (nearest["location"]["lat"], nearest["location"]["lng"])
        remaining.remove(nearest)
    return ordered


# ── ORS Client ────────────────────────────────────────────────────────────────
def _ors_directions(coordinates: List[List[float]]) -> Optional[Dict]:
    """
    Call ORS Directions API.
    coordinates: [[lng, lat], ...] (ORS uses [lng, lat] order)
    Returns the full ORS response JSON or None on failure.
    """
    if not ORS_API_KEY or ORS_API_KEY == "your-ors-api-key":
        return None

    url = f"{ORS_BASE_URL}/directions/driving-car/geojson"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates":     coordinates,
        "instructions":    False,
        "geometry":        True,
        "geometry_simplify": False,
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"⚠️ ORS API error: {e}. Falling back to Haversine routing.")
        return None


def _ors_matrix(sources: List[List[float]], destinations: List[List[float]]) -> Optional[Dict]:
    """Call ORS Matrix API (for optimization)."""
    if not ORS_API_KEY or ORS_API_KEY == "your-ors-api-key":
        return None

    url = f"{ORS_BASE_URL}/matrix/driving-car"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json",
    }
    all_coords = sources + destinations
    body = {
        "locations":     all_coords,
        "sources":       list(range(len(sources))),
        "destinations":  list(range(len(sources), len(all_coords))),
        "metrics":       ["distance", "duration"],
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ── Main Routing Service ──────────────────────────────────────────────────────
class RoutingService:
    def __init__(self, firestore_client):
        self.fc = firestore_client

    def get_driver_bins(self, driver_uid: str) -> List[Dict]:
        """Fetch all active bins assigned to this driver."""
        bins = self.fc.query_collection(
            "bins",
            filters=[
                ("assigned_driver", "==", driver_uid),
                ("status", "in", ["active", "overflow"]),
            ]
        )
        return bins

    def optimize_route(self, driver_uid: str, depot: Dict = None) -> Dict:
        """
        Build optimized route for driver.
        depot: {"lat": float, "lng": float} — driver's start location.
        Returns route dict with waypoints, distance, ETA, GeoJSON.
        """
        bins = self.get_driver_bins(driver_uid)
        if not bins:
            return {
                "driver_uid":         driver_uid,
                "waypoints":          [],
                "total_distance_km":  0.0,
                "eta_minutes":        0.0,
                "geojson":            None,
                "fallback":           False,
            }

        # Default depot (can be overridden by driver's GPS location)
        if depot is None:
            # Use first bin location as proxy depot
            first_bin = bins[0]
            depot = {
                "lat": first_bin["location"]["lat"] - 0.01,
                "lng": first_bin["location"]["lng"] - 0.01,
            }

        depot_ll = (depot["lat"], depot["lng"])

        # Sort bins by priority: overflow first, then by fill_level desc
        bins_sorted = sorted(
            bins,
            key=lambda b: (b.get("status", "") != "overflow", -b.get("fill_level", 0))
        )

        # Try ORS route optimization
        # Coordinates format: [lng, lat]
        all_coords_ors = [
            [depot["lng"], depot["lat"]],
            *[[b["location"]["lng"], b["location"]["lat"]] for b in bins_sorted],
            [depot["lng"], depot["lat"]],   # return to depot
        ]

        ors_response = _ors_directions(all_coords_ors) if len(all_coords_ors) > 2 else None
        fallback = False
        geojson  = None
        total_km = 0.0
        eta_min  = 0.0

        if ors_response:
            try:
                feature  = ors_response["features"][0]
                geojson  = feature["geometry"]
                summary  = feature["properties"]["summary"]
                total_km = round(summary["distance"] / 1000, 2)
                eta_min  = round(summary["duration"] / 60, 1)
            except Exception:
                fallback = True
        else:
            fallback = True

        if fallback:
            # Haversine fallback: greedy nearest-neighbour, total distance estimate
            ordered_bins = _nn_tsp(depot_ll, bins_sorted)
            prev = depot_ll
            for b in ordered_bins:
                d = _haversine(prev[0], prev[1],
                               b["location"]["lat"], b["location"]["lng"])
                total_km += d
                prev = (b["location"]["lat"], b["location"]["lng"])
            total_km += _haversine(prev[0], prev[1], depot_ll[0], depot_ll[1])
            total_km  = round(total_km, 2)
            eta_min   = round(total_km / 25 * 60, 1)  # avg 25 km/h in city
            bins_sorted = ordered_bins

            # Build simple LineString GeoJSON from waypoints
            coords = [[depot["lng"], depot["lat"]]]
            coords += [[b["location"]["lng"], b["location"]["lat"]] for b in bins_sorted]
            coords += [[depot["lng"], depot["lat"]]]
            geojson = {"type": "LineString", "coordinates": coords}

        # Build waypoints list
        waypoints = []
        for i, b in enumerate(bins_sorted):
            waypoints.append({
                "order":       i + 1,
                "bin_id":      b.get("_id", b.get("bin_id", "")),
                "location":    b["location"],
                "fill_level":  b.get("fill_level", 0),
                "status":      b.get("status", "active"),
                "ward_id":     b.get("ward_id", ""),
            })

        return {
            "driver_uid":        driver_uid,
            "waypoints":         waypoints,
            "total_distance_km": total_km,
            "eta_minutes":       eta_min,
            "geojson":           geojson,
            "fallback":          fallback,
            "generated_at":      datetime.now(timezone.utc).isoformat(),
        }

    def mark_collected(self, bin_id: str, driver_uid: str, notes: str = "") -> Dict:
        """
        Mark a bin as collected:
        - Update Firestore bin document
        - Award driver +5 points
        - Return updated bin data
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        update = {
            "fill_level":     0.0,
            "status":         "collected",
            "last_collected": now_iso,
            "driver_uid":     driver_uid,
        }
        self.fc.update_doc("bins", bin_id, update)

        # Log collection event
        self.fc.add_doc("collection_logs", {
            "bin_id":     bin_id,
            "driver_uid": driver_uid,
            "collected_at": now_iso,
            "notes":      notes,
        })

        # Award points (+5 per collection)
        try:
            _award_driver_points(driver_uid, 5, self.fc)
        except Exception:
            pass

        return {"bin_id": bin_id, "status": "collected", "collected_at": now_iso}

    def get_driver_stats(self, driver_uid: str, date_str: str = None) -> Dict:
        """Return today's collection stats for driver."""
        from datetime import date
        today = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        logs = self.fc.query_collection(
            "collection_logs",
            filters=[("driver_uid", "==", driver_uid)],
            order_by="collected_at",
            order_desc=True,
            limit=100,
        )

        today_logs  = [l for l in logs if l.get("collected_at", "").startswith(today)]
        total_today = len(today_logs)

        gamification = self.fc.get_doc("gamification", driver_uid) or {}
        points       = gamification.get("total_points", 0)

        return {
            "driver_uid":        driver_uid,
            "date":              today,
            "bins_collected_today": total_today,
            "total_collections": len(logs),
            "total_points":      points,
        }


def _award_driver_points(uid: str, points: int, fc) -> None:
    existing = fc.get_doc("gamification", uid)
    if not existing:
        fc.set_doc("gamification", uid, {
            "uid":          uid,
            "total_points": points,
            "weekly_points": points,
            "badges":       [],
            "level":        "Beginner",
        })
    else:
        fc.increment_field("gamification", uid, "total_points", points)
        fc.increment_field("gamification", uid, "weekly_points", points)
