import time
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.config import ADMIN_USER, ADMIN_PSWD, SECRET_KEY

security = HTTPBearer(auto_error=False)

login_attempts: dict[str, dict] = {}

MAX_ATTEMPTS = 3
LOCKOUT_DURATION = 24 * 60 * 60

tokens: dict[str, dict] = {}


class TokenData(BaseModel):
    username: str
    expires_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request) -> None:
    client_ip = get_client_ip(request)
    current_time = time.time()

    if client_ip in login_attempts:
        attempt_data = login_attempts[client_ip]

        if attempt_data.get("locked_until"):
            lock_time = attempt_data["locked_until"]
            if current_time < lock_time:
                remaining = int(lock_time - current_time)
                raise HTTPException(
                    429,
                    f"Too many failed attempts. Try again in {remaining // 3600}h {(remaining % 3600) // 60}m",
                )
            else:
                del login_attempts[client_ip]

        attempts = attempt_data.get("attempts", 0)
        if attempts >= MAX_ATTEMPTS:
            login_attempts[client_ip] = {
                "attempts": attempts,
                "locked_until": current_time + LOCKOUT_DURATION,
                "first_attempt": attempt_data.get("first_attempt", current_time),
            }
            raise HTTPException(429, "Too many failed attempts. Locked for 24 hours.")

        if (
            current_time - attempt_data.get("first_attempt", current_time)
            > LOCKOUT_DURATION
        ):
            del login_attempts[client_ip]


def record_failed_attempt(request: Request) -> None:
    client_ip = get_client_ip(request)
    current_time = time.time()

    if client_ip not in login_attempts:
        login_attempts[client_ip] = {"attempts": 1, "first_attempt": current_time}
    else:
        login_attempts[client_ip]["attempts"] += 1


def record_successful_attempt(request: Request) -> None:
    client_ip = get_client_ip(request)
    if client_ip in login_attempts:
        del login_attempts[client_ip]


def create_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=24)
    tokens[token] = {"username": username, "expires_at": expires_at}
    return token


def verify_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None

    token_data = tokens.get(token)
    if not token_data:
        return None

    if datetime.now() > token_data["expires_at"]:
        del tokens[token]
        return None

    return token_data["username"]


async def login(request: Request, login_data: LoginRequest) -> dict:
    check_rate_limit(request)

    if login_data.username == ADMIN_USER and login_data.password == ADMIN_PSWD:
        record_successful_attempt(request)
        token = create_token(login_data.username)
        return {"access_token": token, "token_type": "bearer"}

    record_failed_attempt(request)

    client_ip = get_client_ip(request)
    attempts = login_attempts.get(client_ip, {}).get("attempts", 0)
    remaining = MAX_ATTEMPTS - attempts

    raise HTTPException(401, f"Invalid credentials. {remaining} attempts remaining.")


async def verify_token_dependency(request: Request) -> str:
    credentials = await security(request)

    if not credentials:
        raise HTTPException(401, "Not authenticated")

    token = credentials.credentials
    username = verify_token(token)

    if not username:
        raise HTTPException(401, "Invalid or expired token")

    return username


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    if not credentials:
        raise HTTPException(401, "Not authenticated")

    token = credentials.credentials
    username = verify_token(token)

    if not username:
        raise HTTPException(401, "Invalid or expired token")

    return username


def logout(token: Optional[str]) -> dict:
    if token and token in tokens:
        del tokens[token]
    return {"message": "Logged out successfully"}
