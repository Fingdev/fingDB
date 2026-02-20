from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.crud.materia import (
    materia_router,
    carrera_router,
    perfil_router,
    instituto_router,
)
from app.core.database import engine, Base
from app.auth import login, logout, verify_token, LoginRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="FingDB API",
    description="API para gestionar materias y sus previas",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(materia_router)
app.include_router(carrera_router)
app.include_router(perfil_router)
app.include_router(instituto_router)


@app.post("/auth/login")
async def auth_login(request: Request, login_data: LoginRequest):
    return await login(request, login_data)


@app.post("/auth/logout")
async def auth_logout(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = (
        auth_header.replace("Bearer ", "")
        if auth_header.startswith("Bearer ")
        else None
    )
    return logout(token)


@app.get("/auth/verify")
async def auth_verify(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = (
        auth_header.replace("Bearer ", "")
        if auth_header.startswith("Bearer ")
        else None
    )
    username = verify_token(token)
    if username:
        return {"valid": True, "username": username}
    return {"valid": False}


@app.get("/")
async def root(request: Request):
    path = request.url.path

    if path == "/" or path == "" or path.startswith("/index") or path == "/graph":
        return FileResponse("app/templates/graph.html")
    elif path == "/admin":
        return FileResponse("app/templates/index.html")
    elif path.startswith("/admin/"):
        return FileResponse("app/templates/index.html")
    elif path.endswith(".js"):
        return FileResponse(f"app/templates/{path}")
    else:
        return FileResponse("app/templates/graph.html")


@app.get("/{full_path:path}")
async def catch_all(full_path: str, request: Request):
    path = request.url.path

    if path == "/" or path == "" or path.startswith("/index") or path == "/graph":
        return FileResponse("app/templates/graph.html")
    elif path == "/admin" or path.startswith("/admin/"):
        return FileResponse("app/templates/index.html")
    elif path.endswith(".js"):
        return FileResponse(f"app/templates/{path}")
    elif path.startswith("/static/"):
        return FileResponse("app/templates/graph.html")
    else:
        return FileResponse("app/templates/graph.html")
