"""
Authentication, RBAC & Forensic Audit Router.
Provides JWT authentication, user profile retrieval, user administration,
and security audit log querying.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field

from hamsa.core.database import GLOBAL_DB
from hamsa.core.auth import PasswordHasher, GLOBAL_TOKEN_MANAGER

router = APIRouter(prefix="/api/auth", tags=["Authentication & Audit"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field(default="investigator", pattern="^(admin|investigator)$")


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_auth_token: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Dependency that extracts and validates JWT access token from request headers."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif x_auth_token:
        token = x_auth_token.strip()

    if not token:
        # For open local testing, allow fallback if no auth is sent, but identify as anonymous
        return {"id": "usr_anonymous", "username": "investigator_local", "role": "investigator"}

    payload = GLOBAL_TOKEN_MANAGER.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")

    return {
        "id": payload.get("sub"),
        "username": payload.get("username"),
        "role": payload.get("role", "investigator")
    }


async def require_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency enforcing administrator privilege."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator privilege required.")
    return current_user


@router.post("/login")
async def login(payload: LoginRequest):
    """Authenticates investigator credentials and generates a signed JWT access token."""
    user = await GLOBAL_DB.get_user(payload.username)
    if not user or not PasswordHasher.verify_password(payload.password, user["password_hash"]):
        await GLOBAL_DB.log_audit(
            user_id=None,
            action="LOGIN_FAILED",
            target=payload.username,
            metadata={"status": "invalid_credentials"}
        )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Generate token
    token = GLOBAL_TOKEN_MANAGER.create_access_token(
        user_id=user["id"],
        username=user["username"],
        role=user.get("role", "investigator")
    )

    await GLOBAL_DB.log_audit(
        user_id=user["id"],
        action="USER_LOGIN",
        target=user["username"],
        metadata={"role": user.get("role", "investigator")}
    )

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user.get("role", "investigator")
        }
    }


@router.get("/me")
async def get_current_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the authenticated investigator's identity and privileges."""
    return {"user": current_user}


@router.get("/audit")
async def get_audit_trail(limit: int = 50, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves immutable forensic audit trail records (Chain of Custody)."""
    logs = await GLOBAL_DB.list_audit_logs(limit=limit)
    return {"logs": logs, "count": len(logs)}


@router.get("/users")
async def list_investigators(admin: Dict[str, Any] = Depends(require_admin_user)):
    """Lists all registered investigators and admins (Admin only)."""
    users = await GLOBAL_DB.list_users()
    return {"users": users}


@router.post("/users")
async def create_investigator(payload: UserCreateRequest, admin: Dict[str, Any] = Depends(require_admin_user)):
    """Registers a new investigator account (Admin only)."""
    existing = await GLOBAL_DB.get_user(payload.username)
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' is already registered.")

    hashed = PasswordHasher.hash_password(payload.password)
    user = await GLOBAL_DB.create_user(username=payload.username, password_hash=hashed, role=payload.role)

    await GLOBAL_DB.log_audit(
        user_id=admin["id"],
        action="CREATE_USER",
        target=payload.username,
        metadata={"role": payload.role}
    )

    return {"success": True, "user": user}
