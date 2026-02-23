"""
WASTE IQ — Strict 2-Phase Vision Pipeline
Phase 1: Gemini object detection (with retry on 429) OR HuggingFace CLIP fallback
Phase 2: Deterministic Python waste mapping
"""

import io
import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

from PIL import Image

_ENV_FILE = Path(__file__).parent.parent / ".env"
_YOLO_MODEL = None  # Lazy-loaded


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

BIN_COLORS = {
    "Wet Waste":       "#22c55e",
    "Dry Waste":       "#3b82f6",
    "Recyclable":      "#f59e0b",
    "Hazardous Waste": "#ef4444",
    "E-Waste":         "#a855f7",
    "General Waste":   "#6b7280",
}
VALID_CATEGORIES = set(BIN_COLORS.keys())

DISPOSAL = {
    "Wet Waste": (
        "Place in the GREEN bin. Organic waste composts in 45–90 days.",
        "♻️ Start a compost bin — food scraps make excellent free garden fertilizer!"
    ),
    "Dry Waste": (
        "Place in the BLUE bin. Ensure items are clean and dry before disposal.",
        "💡 Switch to reusable bags and containers to reduce dry waste generation."
    ),
    "Recyclable": (
        "Place in the YELLOW bin. Rinse items before placing — flatten cardboard.",
        "🌍 One recycled aluminium can saves enough energy to power a TV for 3 hours."
    ),
    "Hazardous Waste": (
        "⚠️ Do NOT use regular bins. Take to a designated Hazardous Waste Collection Centre.",
        "⚠️ Never pour chemicals or medicines down the drain — contact your municipal office."
    ),
    "E-Waste": (
        "Take to an authorized E-Waste collection point or manufacturer take-back programme.",
        "📱 Donate working devices to schools or charities before discarding."
    ),
    "General Waste": (
        "Place in the BLACK bin. Try to further segregate into wet, dry or recyclable.",
        "🗑️ When in doubt, segregate! Proper sorting significantly increases recycling rates."
    ),
}


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — DETERMINISTIC WASTE MAPPING (Python only, NO AI)
# ══════════════════════════════════════════════════════════════════════════════

WASTE_MAP: Dict[str, str] = {
    # ── E-Waste ───────────────────────────────────────────────────────────────
    "smartphone": "E-Waste", "mobile phone": "E-Waste", "cell phone": "E-Waste",
    "phone": "E-Waste", "iphone": "E-Waste", "android": "E-Waste",
    "samsung": "E-Waste", "tablet": "E-Waste", "ipad": "E-Waste",
    "laptop": "E-Waste", "notebook": "E-Waste", "computer": "E-Waste",
    "desktop": "E-Waste", "monitor": "E-Waste", "screen": "E-Waste",
    "television": "E-Waste", "tv": "E-Waste", "keyboard": "E-Waste",
    "mouse": "E-Waste", "remote control": "E-Waste", "remote": "E-Waste",
    "camera": "E-Waste", "printer": "E-Waste", "charger": "E-Waste",
    "cable": "E-Waste", "earphones": "E-Waste", "earbuds": "E-Waste",
    "headphones": "E-Waste", "headset": "E-Waste", "speaker": "E-Waste",
    "circuit board": "E-Waste", "pcb": "E-Waste", "radio": "E-Waste",
    "calculator": "E-Waste", "smartwatch": "E-Waste", "watch": "E-Waste",
    "power bank": "E-Waste", "hard drive": "E-Waste", "usb drive": "E-Waste",
    "router": "E-Waste", "modem": "E-Waste", "game console": "E-Waste",
    "microwave": "E-Waste", "washing machine": "E-Waste", "refrigerator": "E-Waste",
    "fridge": "E-Waste", "air conditioner": "E-Waste", "electric fan": "E-Waste",
    "electric kettle": "E-Waste", "toaster": "E-Waste", "blender": "E-Waste",
    "iron": "E-Waste", "hair dryer": "E-Waste", "electric razor": "E-Waste",
    "led bulb": "E-Waste", "light bulb": "E-Waste",
    # ImageNet class names for electronics
    "cellular telephone": "E-Waste", "dial telephone": "E-Waste",
    "hand-held computer": "E-Waste", "notebook computer": "E-Waste",
    "desktop computer": "E-Waste", "laptop computer": "E-Waste",
    "space bar": "E-Waste", "computer keyboard": "E-Waste",
    "optical disk": "E-Waste", "cd player": "E-Waste",
    "loudspeaker": "E-Waste", "ipod": "E-Waste",

    # ── Hazardous Waste ───────────────────────────────────────────────────────
    "battery": "Hazardous Waste", "batteries": "Hazardous Waste",
    "aa battery": "Hazardous Waste", "lithium battery": "Hazardous Waste",
    "paint": "Hazardous Waste", "paint can": "Hazardous Waste",
    "medicine": "Hazardous Waste", "pills": "Hazardous Waste",
    "syringe": "Hazardous Waste", "needle": "Hazardous Waste",
    "chemical": "Hazardous Waste", "pesticide": "Hazardous Waste",
    "bleach": "Hazardous Waste", "lighter": "Hazardous Waste",
    "fluorescent bulb": "Hazardous Waste", "thermometer": "Hazardous Waste",
    "motor oil": "Hazardous Waste", "fire extinguisher": "Hazardous Waste",

    # ── Wet Waste ─────────────────────────────────────────────────────────────
    "banana": "Wet Waste", "banana peel": "Wet Waste", "apple": "Wet Waste",
    "apple core": "Wet Waste", "orange": "Wet Waste", "orange peel": "Wet Waste",
    "fruit": "Wet Waste", "fruit peel": "Wet Waste", "vegetable": "Wet Waste",
    "food": "Wet Waste", "food waste": "Wet Waste", "cooked food": "Wet Waste",
    "rice": "Wet Waste", "bread": "Wet Waste", "egg shell": "Wet Waste",
    "leaves": "Wet Waste", "leaf": "Wet Waste", "grass": "Wet Waste",
    "plant": "Wet Waste", "flower": "Wet Waste", "compost": "Wet Waste",
    "tea bag": "Wet Waste", "coffee grounds": "Wet Waste", "fish": "Wet Waste",
    "meat": "Wet Waste", "potato": "Wet Waste", "carrot": "Wet Waste",
    # ImageNet class names for food
    "lemon": "Wet Waste", "orange (fruit)": "Wet Waste", "strawberry": "Wet Waste",
    "mushroom": "Wet Waste", "artichoke": "Wet Waste", "broccoli": "Wet Waste",
    "cauliflower": "Wet Waste", "corn": "Wet Waste", "acorn": "Wet Waste",

    # ── Recyclable ────────────────────────────────────────────────────────────
    "plastic bottle": "Recyclable", "water bottle": "Recyclable",
    "glass bottle": "Recyclable", "glass jar": "Recyclable", "jar": "Recyclable",
    "tin can": "Recyclable", "aluminium can": "Recyclable", "soda can": "Recyclable",
    "beer can": "Recyclable", "metal can": "Recyclable", "cardboard": "Recyclable",
    "cardboard box": "Recyclable", "newspaper": "Recyclable", "magazine": "Recyclable",
    "book": "Recyclable", "paper": "Recyclable", "envelope": "Recyclable",
    "milk carton": "Recyclable", "juice carton": "Recyclable",
    # ImageNet
    "pop bottle": "Recyclable", "wine bottle": "Recyclable",
    "beer bottle": "Recyclable", "water jug": "Recyclable",
    "carton": "Recyclable", "packet": "Recyclable",

    # ── Dry Waste ─────────────────────────────────────────────────────────────
    "styrofoam": "Dry Waste", "foam": "Dry Waste", "chip bag": "Dry Waste",
    "straw": "Dry Waste", "plastic bag": "Dry Waste", "diaper": "Dry Waste",
    "tissue": "Dry Waste", "napkin": "Dry Waste", "sanitary pad": "Dry Waste",
    "cigarette": "Dry Waste", "rubber": "Dry Waste", "cloth": "Dry Waste",
    "textile": "Dry Waste", "clothing": "Dry Waste", "shoe": "Dry Waste",
    "toothbrush": "Dry Waste", "pen": "Dry Waste", "pencil": "Dry Waste",
}

# Material/texture words → indicates bad detection response
_MATERIAL_WORDS = {
    "material", "surface", "texture", "flat", "colored", "colour", "coloured",
    "color", "white", "black", "grey", "gray", "object", "item", "thing",
    "stuff", "substance", "background", "layer", "sheet", "piece", "dark",
    "light", "bright", "smooth", "rough", "plastic", "metal", "wood",
}


def _read_key() -> str:
    try:
        from dotenv import dotenv_values
        return dotenv_values(_ENV_FILE).get("GEMINI_API_KEY", "").strip()
    except Exception:
        return os.getenv("GEMINI_API_KEY", "").strip()


def _resize_image(img_bytes: bytes, max_px: int = 1024) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img.thumbnail((max_px, max_px), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _is_material_response(name: str) -> bool:
    name_lower = name.lower()
    words = set(name_lower.split())
    if len(words & _MATERIAL_WORDS) >= 2:
        return True
    reject = ["light-colored", "dark-colored", "flat object", "plain surface",
              "colored material", "dark surface", "smooth surface"]
    return any(p in name_lower for p in reject)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — OBJECT DETECTION
# ══════════════════════════════════════════════════════════════════════════════

_DETECT_PROMPT = """You are a high-precision computer vision system.

Identify the single most dominant real-world object in this image.

Rules:
- Name the SPECIFIC OBJECT (e.g. "smartphone", "plastic bottle", "banana peel")
- Do NOT describe materials, colors, textures, or surfaces
- Do NOT mention waste, recycling, or disposal
- Do NOT say "object", "item", "material", "thing", "device" (be more specific)
- Electronic device → name the exact device type
- Food/organic → name the specific food item

Return ONLY valid JSON:
{"object_name": "<specific name>", "confidence": <0-100>}"""

_RETRY_PROMPT = """Previous attempt returned a vague description. Be more specific.

Look at the SHAPE and PURPOSE of the main object. What is it called?

Good: smartphone, laptop, banana peel, plastic bottle, newspaper
Bad: flat object, dark material, electronic device, organic matter

Return ONLY JSON: {"object_name": "<specific name>", "confidence": <0-100>}"""


def _gemini_detect(img_data: bytes, api_key: str, prompt: str) -> dict:
    """Detect object via Gemini with exponential backoff on 429."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.05,
                ),
            )
            text = resp.text.strip()
            if "```" in text:
                for part in text.split("```"):
                    p = part.strip().lstrip("json").strip()
                    if p.startswith("{"):
                        text = p
                        break
            return json.loads(text)

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Resource exhausted" in err_str.lower():
                # For a live web UI, we can't wait 45 seconds.
                # Just wait 1s, 2s. If it still fails, fall back to YOLO immediately.
                wait = attempt + 1  # 1s, 2s
                print(f"⏳ Gemini rate limited (attempt {attempt+1}/3) — waiting {wait}s...")
                time.sleep(wait)
                continue
            raise  # Non-429 error → raise immediately

    raise RuntimeError("Gemini rate limit exceeded after 3 retries. Please wait 1 minute.")


# ══════════════════════════════════════════════════════════════════════════════
# YOLO LOCAL FALLBACK (YOLOv8-nano cls — 1000 ImageNet classes, CPU, no API)
# ══════════════════════════════════════════════════════════════════════════════

# Map common ImageNet class names → (display_name, waste_category)
_IMAGENET_WASTE: Dict[str, tuple] = {
    # Electronics → E-Waste
    "cellular telephone": ("Smartphone", "E-Waste"),
    "dial telephone": ("Telephone", "E-Waste"),
    "hand-held computer": ("Handheld Device", "E-Waste"),
    "notebook computer": ("Laptop", "E-Waste"),
    "laptop": ("Laptop", "E-Waste"),
    "desktop computer": ("Desktop Computer", "E-Waste"),
    "screen": ("Monitor", "E-Waste"),
    "television": ("Television", "E-Waste"),
    "remote control": ("Remote Control", "E-Waste"),
    "loudspeaker": ("Speaker", "E-Waste"),
    "ipod": ("iPod", "E-Waste"),
    "computer keyboard": ("Keyboard", "E-Waste"),
    "space heater": ("Space Heater", "E-Waste"),
    "printer": ("Printer", "E-Waste"),
    "radio": ("Radio", "E-Waste"),
    "digital clock": ("Digital Clock", "E-Waste"),
    "modem": ("Modem", "E-Waste"),
    "mouse": ("Computer Mouse", "E-Waste"),
    "hair dryer": ("Hair Dryer", "E-Waste"),
    "iron": ("Clothes Iron", "E-Waste"),
    "microwave": ("Microwave", "E-Waste"),
    "washing machine": ("Washing Machine", "E-Waste"),
    "refrigerator": ("Refrigerator", "E-Waste"),
    "electric fan": ("Electric Fan", "E-Waste"),
    "dishwasher": ("Dishwasher", "E-Waste"),
    # Bottles/Recyclable
    "pop bottle": ("Plastic Bottle", "Recyclable"),
    "water bottle": ("Water Bottle", "Recyclable"),
    "wine bottle": ("Glass Bottle", "Recyclable"),
    "beer bottle": ("Beer Bottle", "Recyclable"),
    "glass": ("Glass Container", "Recyclable"),
    "jar": ("Glass Jar", "Recyclable"),
    "vase": ("Glass Vase", "Recyclable"),
    "jug": ("Container", "Recyclable"),
    "pitcher": ("Container", "Recyclable"),
    "tin can": ("Tin Can", "Recyclable"),
    "can opener": ("Metal Can", "Recyclable"),
    "envelope": ("Paper Envelope", "Recyclable"),
    "book jacket": ("Book", "Recyclable"),
    "carton": ("Carton", "Recyclable"),
    "newspaper": ("Newspaper", "Recyclable"),
    # Food → Wet Waste
    "banana": ("Banana", "Wet Waste"),
    "lemon": ("Lemon", "Wet Waste"),
    "orange": ("Orange", "Wet Waste"),
    "strawberry": ("Strawberry", "Wet Waste"),
    "apple": ("Apple", "Wet Waste"),
    "mushroom": ("Mushroom", "Wet Waste"),
    "broccoli": ("Broccoli", "Wet Waste"),
    "cauliflower": ("Cauliflower", "Wet Waste"),
    "corn": ("Corn", "Wet Waste"),
    "acorn": ("Organic Matter", "Wet Waste"),
    "artichoke": ("Artichoke", "Wet Waste"),
    "fig": ("Fruit", "Wet Waste"),
    "jackfruit": ("Fruit", "Wet Waste"),
    "pomegranate": ("Fruit", "Wet Waste"),
    "pineapple": ("Pineapple", "Wet Waste"),
    "mango": ("Mango", "Wet Waste"),
    "guacamole": ("Food Waste", "Wet Waste"),
    "pizza": ("Food Waste", "Wet Waste"),
    "cheeseburger": ("Food Waste", "Wet Waste"),
    "hotdog": ("Food Waste", "Wet Waste"),
    "french loaf": ("Bread", "Wet Waste"),
    "pretzel": ("Food Waste", "Wet Waste"),
    "bagel": ("Food Waste", "Wet Waste"),
    "cup cake": ("Food Waste", "Wet Waste"),
    "ice cream": ("Food Waste", "Wet Waste"),
    "pot": ("Plant", "Wet Waste"),
    "flower pot": ("Plant", "Wet Waste"),
    # Dry Waste
    "plastic bag": ("Plastic Bag", "Dry Waste"),
    "shoe shop": ("Shoes", "Dry Waste"),
    "toothbrush": ("Toothbrush", "Dry Waste"),
    "pencil box": ("Stationery", "Dry Waste"),
    "pencil sharpener": ("Stationery", "Dry Waste"),
    # Hazardous
    "lighter": ("Lighter", "Hazardous Waste"),
    "fire extinguisher": ("Fire Extinguisher", "Hazardous Waste"),
    "syringe": ("Syringe", "Hazardous Waste"),
    "pill bottle": ("Medicine", "Hazardous Waste"),
    "medicine cabinet": ("Medicine", "Hazardous Waste"),
}


def _get_yolo_model():
    """Lazy-load YOLOv8-nano classification model (cached after first load)."""
    global _YOLO_MODEL
    if _YOLO_MODEL is None:
        try:
            from ultralytics import YOLO
            _YOLO_MODEL = YOLO("yolov8n-cls.pt")  # 6MB, downloads once
            print("🤖 YOLOv8-nano classification model loaded")
        except Exception as e:
            print(f"❌ Failed to load YOLO model: {e}")
            _YOLO_MODEL = False  # Mark as failed
    return _YOLO_MODEL if _YOLO_MODEL else None


def _yolo_classify(img_bytes: bytes) -> dict:
    """
    Local YOLOv8-nano (1000 ImageNet classes) as offline fallback.
    No API call, no internet needed after first model download.
    """
    model = _get_yolo_model()
    if not model:
        raise RuntimeError("YOLO model unavailable")

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    results = model(img, verbose=False)
    result = results[0]

    # Get top-5 predictions
    probs = result.probs
    names = model.names

    top5_idx   = probs.top5
    top5_conf  = probs.top5conf.tolist()

    top_label = names[top5_idx[0]].lower()
    top_conf  = round(top5_conf[0] * 100, 1)

    alternatives = [
        {"name": names[top5_idx[i]].replace("-", " ").title(), "confidence": round(top5_conf[i] * 100, 1)}
        for i in range(1, min(4, len(top5_idx)))
    ]

    # 1. Check ImageNet→waste map
    for key, (display, cat) in _IMAGENET_WASTE.items():
        if key in top_label or top_label in key:
            instructions, tip = DISPOSAL[cat]
            return {
                "object_name":           display,
                "waste_category":        cat,
                "confidence":            top_conf,
                "disposal_instructions": instructions,
                "recycling_tip":         tip,
                "alternatives":          alternatives,
                "mode":                  "yolo_local",
            }

    # 2. Keyword scan using waste map
    for keyword, cat in WASTE_MAP.items():
        if keyword in top_label:
            instructions, tip = DISPOSAL[cat]
            display = top_label.replace("-", " ").replace(",", "").title()
            return {
                "object_name":           display,
                "waste_category":        cat,
                "confidence":            top_conf,
                "disposal_instructions": instructions,
                "recycling_tip":         tip,
                "alternatives":          alternatives,
                "mode":                  "yolo_local",
            }

    # 3. Use top label as-is → General Waste
    display = top_label.split(",")[0].replace("-", " ").title()
    instructions, tip = DISPOSAL["General Waste"]
    return {
        "object_name":           display,
        "waste_category":        "General Waste",
        "confidence":            top_conf,
        "disposal_instructions": instructions,
        "recycling_tip":         tip,
        "alternatives":          alternatives,
        "mode":                  "yolo_local",
    }



# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — DETERMINISTIC WASTE MAPPING
# ══════════════════════════════════════════════════════════════════════════════

def _map_to_category(object_name: str, api_key: str = "") -> str:
    """Map object name → waste category. Python-first, Gemini only for unknowns."""
    from rapidfuzz import process, fuzz

    obj_lower = object_name.lower().strip()

    if obj_lower in WASTE_MAP:
        return WASTE_MAP[obj_lower]

    match = process.extractOne(obj_lower, list(WASTE_MAP.keys()),
                               scorer=fuzz.WRatio, score_cutoff=75)
    if match:
        return WASTE_MAP[match[0]]

    for keyword, category in WASTE_MAP.items():
        if keyword in obj_lower:
            return category

    for keyword, category in WASTE_MAP.items():
        if obj_lower in keyword:
            return category

    if api_key:
        return _gemini_category_step(object_name, api_key)

    return "General Waste"


def _gemini_category_step(object_name: str, api_key: str) -> str:
    """Text-only Gemini call — classify unknown object into waste category."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = (
        f'Object: "{object_name}"\n'
        "Classify into exactly one: Wet Waste | Dry Waste | Recyclable | Hazardous Waste | E-Waste | General Waste\n"
        'Return JSON only: {"category": "<category>"}'
    )
    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", temperature=0.0),
            )
            cat = json.loads(resp.text.strip()).get("category", "General Waste")
            return cat if cat in VALID_CATEGORIES else "General Waste"
        except Exception as e:
            if "429" in str(e) and attempt == 0:
                print("⏳ Gemini category rate limited — waiting 1s...")
                time.sleep(1)
                continue
            return "General Waste"
    return "General Waste"


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CLASSIFY
# ══════════════════════════════════════════════════════════════════════════════

def _classify_gemini(img_bytes: bytes, api_key: str) -> Dict:
    """Phase 1: Gemini detect → Phase 2: Python mapping."""
    img_data = _resize_image(img_bytes)

    detected = _gemini_detect(img_data, api_key, _DETECT_PROMPT)
    obj = detected.get("object_name", "").strip()
    conf = float(detected.get("confidence", 0))

    if _is_material_response(obj) or conf < 60:
        print(f"⚠️  Vague result '{obj}' — retrying...")
        retry = _gemini_detect(img_data, api_key, _RETRY_PROMPT)
        new_obj  = retry.get("object_name", "").strip()
        new_conf = float(retry.get("confidence", 0))
        if new_obj and not _is_material_response(new_obj):
            obj, conf = new_obj, new_conf

    if conf < 40:
        instructions, tip = DISPOSAL["General Waste"]
        return {"object_name": "Unable to identify object",
                "waste_category": "General Waste", "confidence": round(conf, 1),
                "disposal_instructions": instructions, "recycling_tip": tip,
                "alternatives": [], "mode": "gemini"}

    category = _map_to_category(obj, api_key)
    instructions, tip = DISPOSAL[category]
    return {"object_name": obj, "waste_category": category,
            "confidence": round(conf, 1), "disposal_instructions": instructions,
            "recycling_tip": tip, "alternatives": [], "mode": "gemini"}


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC CLASSIFIER CLASS
# ══════════════════════════════════════════════════════════════════════════════

class WasteClassifier:
    def __init__(self):
        key = _read_key()
        status = f"Gemini active (...{key[-6:]})" if key else "No Gemini key → HuggingFace fallback"
        print(f"✅ WasteClassifier — {status}")

    def predict(self, img_bytes: bytes) -> Dict:
        key = _read_key()

        # Primary: Gemini 2-phase pipeline
        if key:
            try:
                return _classify_gemini(img_bytes, key)
            except RuntimeError as e:
                print(f"⚠️  Gemini rate-limited: {e} — falling back to local YOLO")
            except Exception as e:
                print(f"⚠️  Gemini error: {e} — falling back to local YOLO")

        # Fallback: Local YOLOv8-nano (offline, no API, 1000 ImageNet classes)
        try:
            print("🤖 Using YOLOv8-nano local classifier (Gemini unavailable)...")
            return _yolo_classify(img_bytes)
        except Exception as e:
            print(f"❌ YOLO also failed: {e}")
            instructions, tip = DISPOSAL["General Waste"]
            return {
                "object_name": "Classification unavailable",
                "waste_category": "General Waste",
                "confidence": 0.0,
                "disposal_instructions": instructions,
                "recycling_tip": tip,
                "alternatives": [],
                "mode": "error",
                "error": str(e)[:120],
            }


    def classify_and_save(self, img_bytes: bytes, uid: str,
                          firestore_client, image_url: str = None) -> Dict:
        result = self.predict(img_bytes)
        log_doc = {
            "uid":                   uid,
            "object_name":           result["object_name"],
            "waste_category":        result["waste_category"],
            "confidence":            result["confidence"],
            "disposal_instructions": result["disposal_instructions"],
            "recycling_tip":         result["recycling_tip"],
            "image_url":             image_url,
            "timestamp":             datetime.now(timezone.utc).isoformat(),
            "mode":                  result.get("mode", "error"),
        }
        try:
            log_id = firestore_client.add_doc("waste_logs", log_doc)
            log_doc["log_id"] = log_id
            print(f"✅ DB: Saved classification log {log_id}")
        except Exception as db_err:
            print(f"❌ DB Write Error for waste_logs: {db_err}")
            log_doc["log_id"] = None
        if result.get("mode") != "error":
            try:
                _award_points(uid, 5, "Waste classification", firestore_client)
            except Exception:
                pass
        return log_doc


def _award_points(uid: str, points: int, reason: str, fc) -> None:
    existing = fc.get_doc("gamification", uid)
    if not existing:
        fc.set_doc("gamification", uid, {
            "uid": uid, "total_points": points,
            "weekly_points": points, "badges": [], "level": "Beginner"
        })
    else:
        fc.increment_field("gamification", uid, "total_points", points)
        fc.increment_field("gamification", uid, "weekly_points", points)
