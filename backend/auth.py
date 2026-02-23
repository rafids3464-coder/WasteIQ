"""
WASTE IQ – Firebase Authentication & Authorization
Verifies Firebase ID tokens and enforces role-based access.
"""

import os
from pathlib import Path
from functools import wraps
from typing import Optional, List
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Load .env from project root (waste_iq/) regardless of launch directory
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

# ── Firebase Admin SDK Init ───────────────────────────────────────────────────
def _init_firebase():
    if not firebase_admin._apps:
        sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./firebase_service_account.json")
        sa_resolved = (
            Path(sa_path) if Path(sa_path).is_absolute()
            else _ROOT / sa_path.lstrip("./")
        )
        if sa_resolved.exists():
            cred = credentials.Certificate(str(sa_resolved))
        else:
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

_init_firebase()

# ── HTTP Bearer auth scheme ───────────────────────────────────────────────────
security = HTTPBearer(auto_error=False)

# ── Token Verification ────────────────────────────────────────────────────────
class UserInfo:
    def __init__(self, uid: str, email: str, role: str, name: str = ""):
        self.uid   = uid
        self.email = email
        self.role  = role
        self.name  = name

    def __repr__(self):
        return f"<UserInfo uid={self.uid} role={self.role}>"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserInfo:
    """Verify Firebase ID token and return UserInfo."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        decoded = firebase_auth.verify_id_token(token)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expired")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth error: {str(e)}")

    uid   = decoded.get("uid", "")
    email = decoded.get("email", "")
    role  = decoded.get("role", "household")   # custom claim
    name  = decoded.get("name", "")

    return UserInfo(uid=uid, email=email, role=role, name=name)


# ── Role Dependency Factories ─────────────────────────────────────────────────
def require_roles(allowed_roles: List[str]):
    """Return a FastAPI dependency that enforces role membership."""
    async def _check(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized for this action. "
                       f"Allowed roles: {allowed_roles}"
            )
        return user
    return _check

# Convenience role guards
require_admin      = require_roles(["admin"])
require_municipal  = require_roles(["admin", "municipal"])
require_driver     = require_roles(["admin", "driver"])
require_any_auth   = require_roles(["admin", "municipal", "driver", "household"])


# ── Set Custom Role Claim ─────────────────────────────────────────────────────
def set_user_role(uid: str, role: str) -> None:
    """Set Firebase custom claims for a user (called after signup)."""
    valid_roles = {"household", "municipal", "driver", "admin"}
    if role not in valid_roles:
        raise ValueError(f"Invalid role: {role}")
    firebase_auth.set_custom_user_claims(uid, {"role": role})


# ── Admin: Create User ────────────────────────────────────────────────────────
def create_user(email: str, password: str, display_name: str) -> str:
    """Create a Firebase Auth user and return UID."""
    user = firebase_auth.create_user(
        email=email,
        password=password,
        display_name=display_name,
        email_verified=False
    )
    return user.uid


# ── Admin: List Users ─────────────────────────────────────────────────────────
def list_all_users():
    """List all Firebase Auth users (admin only)."""
    users = []
    page = firebase_auth.list_users()
    while page:
        for u in page.users:
            claims = u.custom_claims or {}
            users.append({
                "uid":          u.uid,
                "email":        u.email,
                "display_name": u.display_name,
                "role":         claims.get("role", "household"),
                "disabled":     u.disabled,
                "created_at":   u.user_metadata.creation_timestamp,
            })
        page = page.get_next_page()
    return users


# ── Admin: Disable/Enable User ────────────────────────────────────────────────
def set_user_disabled(uid: str, disabled: bool) -> None:
    firebase_auth.update_user(uid, disabled=disabled)
