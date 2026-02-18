from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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


@app.get("/")
async def root():
    return FileResponse("app/templates/index.html")
