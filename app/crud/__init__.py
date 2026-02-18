from fastapi import APIRouter
from app.crud.materia import materia_router

crud_router = APIRouter()

crud_router.include_router(materia_router)