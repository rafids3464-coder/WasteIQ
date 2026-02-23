"""
WASTE IQ – Firestore Client
Singleton wrapper around firebase-admin Firestore SDK.
Lazy initialization — does NOT connect at import time.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from dotenv import load_dotenv

# Load .env from project root (waste_iq/) regardless of launch directory
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

# Module-level lazy references — populated on first use
_app = None
_db  = None


def _get_db():
    """Return the Firestore client, initialising Firebase Admin on first call."""
    global _app, _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./firebase_service_account.json")
        # Resolve relative paths from project root, not cwd
        sa_resolved = (
            Path(sa_path) if Path(sa_path).is_absolute()
            else _ROOT / sa_path.lstrip("./")
        )
        if sa_resolved.exists():
            print(f"🔑  Using service account: {sa_resolved}")
            cred = credentials.Certificate(str(sa_resolved))
        else:
            print(f"⚠️   Service account not found at {sa_resolved}, falling back to ApplicationDefault")
            cred = credentials.ApplicationDefault()
        _app = firebase_admin.initialize_app(cred)
    else:
        _app = firebase_admin.get_app()

    _db = firestore.client()
    return _db


# ── Core helpers ───────────────────────────────────────────────────────────────
def get_doc(collection: str, doc_id: str) -> Optional[Dict]:
    """Fetch a single document. Returns None if not found."""
    ref = _get_db().collection(collection).document(doc_id)
    snap = ref.get()
    if snap.exists:
        data = snap.to_dict()
        data["_id"] = snap.id
        return data
    return None


def set_doc(collection: str, doc_id: str, data: Dict) -> str:
    """Create or overwrite a document. Returns doc_id."""
    _get_db().collection(collection).document(doc_id).set(data)
    return doc_id


def add_doc(collection: str, data: Dict) -> str:
    """Add a document with auto-generated ID. Returns new doc_id."""
    ref = _get_db().collection(collection).add(data)
    return ref[1].id


def update_doc(collection: str, doc_id: str, data: Dict) -> None:
    """Merge-update fields in a document."""
    _get_db().collection(collection).document(doc_id).update(data)


def delete_doc(collection: str, doc_id: str) -> None:
    """Delete a document."""
    _get_db().collection(collection).document(doc_id).delete()


def query_collection(
    collection: str,
    filters: Optional[List[tuple]] = None,
    order_by: Optional[str] = None,
    order_desc: bool = False,
    limit: Optional[int] = None,
) -> List[Dict]:
    """
    Query a collection with optional filters, ordering, and limit.
    filters example: [("uid", "==", "abc123"), ("fill_level", ">", 80)]
    """
    ref = _get_db().collection(collection)
    if filters:
        for field, op, value in filters:
            ref = ref.where(filter=FieldFilter(field, op, value))
    if order_by:
        direction = firestore.Query.DESCENDING if order_desc else firestore.Query.ASCENDING
        ref = ref.order_by(order_by, direction=direction)
    if limit:
        ref = ref.limit(limit)

    docs = []
    for snap in ref.stream():
        d = snap.to_dict()
        d["_id"] = snap.id
        docs.append(d)
    return docs


def increment_field(collection: str, doc_id: str, field: str, amount: int = 1) -> None:
    """Atomically increment a numeric field."""
    _get_db().collection(collection).document(doc_id).update(
        {field: firestore.Increment(amount)}
    )


def server_timestamp():
    """Return a Firestore server timestamp sentinel."""
    return firestore.SERVER_TIMESTAMP
