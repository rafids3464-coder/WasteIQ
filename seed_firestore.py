"""
WASTE IQ – Firestore Seed Script
Run once to populate demo data. Requires firebase_service_account.json.
Usage: python seed_firestore.py
"""

import os, uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth

# ── Init ──────────────────────────────────────────────────────────────────────
SA_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./firebase_service_account.json")
if not firebase_admin._apps:
    cred = credentials.Certificate(SA_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ── Demo Users ────────────────────────────────────────────────────────────────
DEMO_USERS = [
    {"email": "household@wasteiq.demo", "password": "demo1234", "name": "Aisha Kumar",   "role": "household", "ward_id": "WARD_01"},
    {"email": "municipal@wasteiq.demo", "password": "demo1234", "name": "Ravi Nair",    "role": "municipal", "ward_id": "WARD_01"},
    {"email": "driver@wasteiq.demo",    "password": "demo1234", "name": "Suresh Thomas","role": "driver",    "ward_id": "WARD_01"},
    {"email": "admin@wasteiq.demo",     "password": "demo1234", "name": "Priya Admin",  "role": "admin",     "ward_id": None},
]

# ── Kozhikode bin locations ────────────────────────────────────────────────────
BINS_DATA = [
    {"ward_id": "WARD_01", "lat": 11.2588, "lng": 75.7804, "address": "Mananchira Square",        "fill": 85.0},
    {"ward_id": "WARD_01", "lat": 11.2612, "lng": 75.7812, "address": "SM Street Junction",       "fill": 60.0},
    {"ward_id": "WARD_01", "lat": 11.2550, "lng": 75.7789, "address": "Kottabayam Bus Stop",      "fill": 45.0},
    {"ward_id": "WARD_01", "lat": 11.2630, "lng": 75.7850, "address": "Palayam Market",           "fill": 90.0},
    {"ward_id": "WARD_01", "lat": 11.2575, "lng": 75.7830, "address": "Beach Road Junction",      "fill": 30.0},
    {"ward_id": "WARD_02", "lat": 11.2490, "lng": 75.7720, "address": "Nadakkavu Junction",       "fill": 72.0},
    {"ward_id": "WARD_02", "lat": 11.2510, "lng": 75.7740, "address": "Park Avenue",              "fill": 55.0},
    {"ward_id": "WARD_02", "lat": 11.2540, "lng": 75.7760, "address": "Medical College Road",     "fill": 88.0},
]

# ── Ward docs ─────────────────────────────────────────────────────────────────
WARDS = [
    {"ward_id": "WARD_01", "name": "Mananchira Ward", "city": "Kozhikode", "population": 12000, "population_density": 8500},
    {"ward_id": "WARD_02", "name": "Nadakkavu Ward",  "city": "Kozhikode", "population": 9500,  "population_density": 7200},
]


def create_user_if_not_exists(email, password, name, role, ward_id):
    try:
        user = firebase_auth.get_user_by_email(email)
        print(f"  ✓ User already exists: {email}")
        uid = user.uid
    except firebase_auth.UserNotFoundError:
        user = firebase_auth.create_user(email=email, password=password, display_name=name)
        uid  = user.uid
        print(f"  + Created user: {email}")

    # Set custom role claim
    firebase_auth.set_custom_user_claims(uid, {"role": role})

    # Firestore profile
    db.collection("users").document(uid).set({
        "uid":        uid,
        "email":      email,
        "name":       name,
        "role":       role,
        "ward_id":    ward_id,
        "phone":      None,
        "address":    "Kozhikode, Kerala",
        "language":   "en",
        "avatar_url": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, merge=True)

    # Gamification
    db.collection("gamification").document(uid).set({
        "uid":          uid,
        "total_points": 0,
        "weekly_points": 0,
        "badges":       [],
        "level":        "Beginner",
    }, merge=True)

    return uid


def seed_bins(driver_uid):
    print("\n📦 Seeding bins...")
    bin_ids = []
    for b in BINS_DATA:
        bid = str(uuid.uuid4())
        status = "overflow" if b["fill"] >= 80 else "active"
        db.collection("bins").document(bid).set({
            "bin_id":          bid,
            "ward_id":         b["ward_id"],
            "location":        {"lat": b["lat"], "lng": b["lng"], "address": b["address"]},
            "fill_level":      b["fill"],
            "capacity_liters": 200.0,
            "status":          status,
            "assigned_driver": driver_uid,
            "last_collected":  (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat(),
            "population_density": 8500.0,
            "avg_daily_waste_kg": 3.0,
            "created_at":      datetime.now(timezone.utc).isoformat(),
        })
        bin_ids.append(bid)
        print(f"  + Bin {bid[:8]} at {b['address']} ({b['fill']:.0f}%)")
    return bin_ids


def seed_waste_logs(household_uid, bin_ids):
    print("\n🔍 Seeding waste classification logs...")
    SAMPLES = [
        ("Banana Peel",     "Wet Waste",       92.3),
        ("Plastic Bottle",  "Recyclable",      88.7),
        ("Newspaper",       "Recyclable",      79.4),
        ("Old Phone",       "E-Waste",         65.2),
        ("Dead Battery",    "Hazardous Waste", 71.0),
        ("Vegetable Scraps","Wet Waste",       85.6),
        ("Cardboard Box",   "Recyclable",      91.1),
        ("Tissue Paper",    "Dry Waste",       60.3),
    ]
    for i, (obj, cat, conf) in enumerate(SAMPLES):
        ts = (datetime.now(timezone.utc) - timedelta(days=i, hours=i*2)).isoformat()
        db.collection("waste_logs").add({
            "uid":            household_uid,
            "object_name":    obj,
            "waste_category": cat,
            "confidence":     conf,
            "disposal_instructions": f"Place in the appropriate bin for {cat}.",
            "recycling_tip":  f"♻️ Tip: Properly segregate {cat} to increase recycling rates.",
            "image_url":      None,
            "timestamp":      ts,
        })
    print(f"  + {len(SAMPLES)} waste logs created")


def seed_complaints(household_uid):
    print("\n📢 Seeding complaints...")
    COMPLAINTS = [
        {"title": "Overflowing bin at SM Street",  "desc": "The big green bin near SM Street is overflowing onto the road.", "status": "open"},
        {"title": "Missed collection on Monday",   "desc": "Waste was not collected on Monday morning in our area.",         "status": "resolved"},
        {"title": "Illegal dumping near canal",    "desc": "Someone is dumping bags of waste near the canal.",              "status": "in_review"},
    ]
    for c in COMPLAINTS:
        cid = str(uuid.uuid4())
        db.collection("complaints").add({
            "complaint_id": cid,
            "title":        c["title"],
            "description":  c["desc"],
            "ward_id":      "WARD_01",
            "bin_id":       None,
            "location":     None,
            "submitted_by": household_uid,
            "status":       c["status"],
            "created_at":   (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "resolved_at":  datetime.now(timezone.utc).isoformat() if c["status"] == "resolved" else None,
            "resolution":   "Collection team notified and dispatched." if c["status"] == "resolved" else None,
        })
    print(f"  + {len(COMPLAINTS)} complaints created")


def seed_wards():
    print("\n🏙️ Seeding wards...")
    for w in WARDS:
        db.collection("wards").document(w["ward_id"]).set(w)
        print(f"  + Ward {w['ward_id']}: {w['name']}")


def seed_gamification_points(uids_by_role):
    """Give each demo user some starter points."""
    print("\n⭐ Seeding gamification points...")
    starter_pts = {"household": 145, "municipal": 320, "driver": 215, "admin": 500}
    for role, uid in uids_by_role.items():
        pts = starter_pts.get(role, 50)
        db.collection("gamification").document(uid).set({
            "uid":           uid,
            "total_points":  pts,
            "weekly_points": pts // 3,
            "badges":        [],
            "level":         "Starter" if pts >= 50 else "Beginner",
        }, merge=True)
    print("  ✓ Points seeded")


if __name__ == "__main__":
    print("🌱 WASTE IQ – Seeding Firestore Demo Data")
    print("=" * 50)

    # Create users
    print("\n👥 Creating demo users...")
    uids = {}
    for u in DEMO_USERS:
        uid = create_user_if_not_exists(u["email"], u["password"], u["name"], u["role"], u["ward_id"])
        uids[u["role"]] = uid

    driver_uid    = uids.get("driver")
    household_uid = uids.get("household")

    # Seed other collections
    seed_wards()
    bin_ids = seed_bins(driver_uid)
    seed_waste_logs(household_uid, bin_ids)
    seed_complaints(household_uid)
    seed_gamification_points(uids)

    print("\n" + "=" * 50)
    print("✅ Seeding complete!\n")
    print("Demo login credentials:")
    print("  Household : household@wasteiq.demo / demo1234")
    print("  Municipal : municipal@wasteiq.demo / demo1234")
    print("  Driver    : driver@wasteiq.demo    / demo1234")
    print("  Admin     : admin@wasteiq.demo     / demo1234")
