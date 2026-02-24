"""
WASTE IQ – Firestore Client
Production-safe Firebase Admin initialization (Render compatible)
"""

import os
from typing import Any, Dict, List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter


# ─────────────────────────────────────────────────────────────
# Initialize Firebase Admin ONCE at import time
# ─────────────────────────────────────────────────────────────

if not firebase_admin._apps:
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")

    if not all([project_id, private_key, client_email]):
        raise RuntimeError(
            "Firebase environment variables missing. "
            "Set FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL in Render."
        )

    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": project_id,
        "private_key": private_key.replace("\\n", "\n"),
        "client_email": client_email,
    })

    firebase_admin.initialize_app(cred)


# Create Firestore client once
_db = firestore.client()


# ─────────────────────────────────────────────────────────────
# Core Helpers
# ─────────────────────────────────────────────────────────────

def get_doc(collection: str, doc_id: str) -> Optional[Dict]:
    ref = _db.collection(collection).document(doc_id)
    snap = ref.get()
    if snap.exists:
        data = snap.to_dict()
        data["_id"] = snap.id
        return data
    return None


def set_doc(collection: str, doc_id: str, data: Dict) -> str:
    _db.collection(collection).document(doc_id).set(data)
    return doc_id


def add_doc(collection: str, data: Dict) -> str:
    ref = _db.collection(collection).add(data)
    return ref[1].id


def update_doc(collection: str, doc_id: str, data: Dict) -> None:
    _db.collection(collection).document(doc_id).update(data)


def delete_doc(collection: str, doc_id: str) -> None:
    _db.collection(collection).document(doc_id).delete()


def query_collection(
    collection: str,
    filters: Optional[List[tuple]] = None,
    order_by: Optional[str] = None,
    order_desc: bool = False,
    limit: Optional[int] = None,
) -> List[Dict]:

    ref = _db.collection(collection)

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
    _db.collection(collection).document(doc_id).update(
        {field: firestore.Increment(amount)}
    )


def server_timestamp():
    return firestore.SERVER_TIMESTAMP
