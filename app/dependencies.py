from fastapi import Depends, HTTPException, Header
from app.core.config import API_KEY


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(401, "Invalid API key")
    return x_api_key
