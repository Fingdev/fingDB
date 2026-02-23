from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastcrud import FastCRUD
from pydantic import BaseModel

from app.core.database import get_session
from app.models.materia import (
    Materia,
    TipoPreviaEnum,
    MateriaPrevia,
    Carrera,
    CarreraMateria,
    Perfil,
    PerfilMateria,
    Instituto,
)
from app.schemas.materia import PeriodoEnum, MateriaRead
from app.dependencies import verify_token_dep, get_current_user_or_none


def parse_ids(s: Optional[str]) -> List[int]:
    if not s or not s.strip():
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip().isdigit()]


materia_crud = FastCRUD(Materia)

materia_router = APIRouter(prefix="/materias", tags=["Materias"])


class MateriaConPrevias(BaseModel):
    id: int
    name: str
    codigo: Optional[str] = None
    periodo: PeriodoEnum
    creditos: int = 0
    active: bool
    created_at: str
    updated_at: Optional[str]
    previas_aprobado: List[dict]
    previas_exonerado: List[dict]

    class Config:
        from_attributes = True


async def get_form_data(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        return await request.json()
    else:
        form = await request.form()
        return {k: v for k, v in form.items()}


@materia_router.post("", response_model=MateriaRead, status_code=201)
async def create_materia(
    request: Request,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    data = await get_form_data(request)

    name = data.get("name")
    codigo = data.get("codigo") or None
    periodo = data.get("periodo")
    creditos = int(data.get("creditos", 0) or 0)
    min_creditos = int(data.get("min_creditos", 0) or 0) or None
    instituto_id = int(data.get("instituto_id", 0) or 0)
    previas_aprobado = str(data.get("previas_aprobado", "")) or ""
    previas_exonerado = str(data.get("previas_exonerado", "")) or ""

    if not instituto_id:
        raise HTTPException(400, "instituto_id is required")

    nueva = Materia(
        name=name,
        codigo=codigo,
        periodo=periodo,
        creditos=creditos,
        min_creditos=min_creditos,
        instituto_id=instituto_id,
    )
    db.add(nueva)
    await db.flush()

    aprobado_ids = parse_ids(previas_aprobado)
    exonerado_ids = parse_ids(previas_exonerado)

    nuevas_previas = []

    if aprobado_ids:
        result = await db.execute(select(Materia).where(Materia.id.in_(aprobado_ids)))
        for m in result.scalars():
            nuevas_previas.append(
                MateriaPrevia(
                    materia_id=nueva.id, previa_id=m.id, tipo=TipoPreviaEnum.aprobado
                )
            )

    if exonerado_ids:
        result = await db.execute(select(Materia).where(Materia.id.in_(exonerado_ids)))
        for m in result.scalars():
            nuevas_previas.append(
                MateriaPrevia(
                    materia_id=nueva.id, previa_id=m.id, tipo=TipoPreviaEnum.exonerado
                )
            )

    for prev in nuevas_previas:
        db.add(prev)

    await db.commit()
    await db.refresh(nueva)
    return nueva


@materia_router.patch("/{id}", response_model=MateriaRead)
async def update_materia(
    id: int,
    request: Request,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    data = await get_form_data(request)

    name: str = data.get("name") or ""
    codigo: str = data.get("codigo") or None
    periodo: str = data.get("periodo") or "bisemestral"
    creditos: int = int(data.get("creditos", 0) or 0)
    min_creditos: int = int(data.get("min_creditos", 0) or 0) or None
    instituto_id: int = int(data.get("instituto_id", 0) or 0)
    previas_aprobado: str = data.get("previas_aprobado") or ""
    previas_exonerado: str = data.get("previas_exonerado") or ""

    result = await db.execute(select(Materia).where(Materia.id == id))
    materia = result.scalar_one_or_none()

    if not materia:
        raise HTTPException(404, "Materia not found")

    if name:
        materia.name = name
    materia.codigo = codigo
    if periodo:
        materia.periodo = periodo
    materia.creditos = creditos
    materia.min_creditos = min_creditos
    if instituto_id:
        materia.instituto_id = instituto_id

    await db.flush()

    aprobado_ids = parse_ids(previas_aprobado)
    exonerado_ids = parse_ids(previas_exonerado)

    result = await db.execute(
        select(MateriaPrevia).where(MateriaPrevia.materia_id == id)
    )
    existing_previas = result.scalars().all()
    for prev in existing_previas:
        await db.delete(prev)

    if aprobado_ids:
        result = await db.execute(select(Materia).where(Materia.id.in_(aprobado_ids)))
        for m in result.scalars():
            db.add(
                MateriaPrevia(
                    materia_id=id, previa_id=m.id, tipo=TipoPreviaEnum.aprobado
                )
            )

    if exonerado_ids:
        result = await db.execute(select(Materia).where(Materia.id.in_(exonerado_ids)))
        for m in result.scalars():
            db.add(
                MateriaPrevia(
                    materia_id=id, previa_id=m.id, tipo=TipoPreviaEnum.exonerado
                )
            )

    await db.commit()
    await db.refresh(materia)
    return materia


@materia_router.get("/{id}", response_model=MateriaRead)
async def get_materia(
    id: int,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Materia).where(Materia.id == id))
    materia = result.scalar_one_or_none()
    if not materia:
        raise HTTPException(404, "Materia not found")
    return materia


@materia_router.get("")
async def get_materias(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    result = await materia_crud.get_multi(
        db,
        limit=limit,
        offset=offset,
    )
    return result


@materia_router.get("/all/con-previas")
async def get_all_materias_con_previas(
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(Materia).where(Materia.active == True).order_by(Materia.name)
    )
    materias = result.scalars().all()

    response = []
    for m in materias:
        result_prev = await db.execute(
            select(MateriaPrevia).where(MateriaPrevia.materia_id == m.id)
        )
        previas = result_prev.scalars().all()

        prev_aprobado = []
        prev_exonerado = []

        for p in previas:
            result_previa = await db.execute(
                select(Materia).where(Materia.id == p.previa_id)
            )
            previa = result_previa.scalar_one_or_none()
            if previa:
                prev_data = {"id": previa.id, "name": previa.name}
                if p.tipo == TipoPreviaEnum.aprobado:
                    prev_aprobado.append(prev_data)
                else:
                    prev_exonerado.append(prev_data)

        response.append(
            {
                "id": m.id,
                "name": m.name,
                "codigo": m.codigo,
                "periodo": m.periodo.value,
                "creditos": m.creditos,
                "min_creditos": m.min_creditos,
                "instituto_id": m.instituto_id,
                "active": m.active,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                "previas_aprobado": prev_aprobado,
                "previas_exonerado": prev_exonerado,
            }
        )

    return response


@materia_router.delete("/{id}", status_code=204)
async def delete_materia(
    id: int,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Materia).where(Materia.id == id))
    materia = result.scalar_one_or_none()
    if not materia:
        raise HTTPException(404, "Materia not found")
    await db.delete(materia)
    await db.commit()
    return None


@materia_router.get("/options")
async def get_options(
    q: str = "",
    db: AsyncSession = Depends(get_session),
):
    query = select(Materia.id, Materia.name)
    if q:
        query = query.where(Materia.name.ilike(f"%{q}%"))
    result = await db.execute(query.limit(50))
    return [{"value": r.id, "label": r.name} for r in result]


# -------------------------
# CARRERAS
# -------------------------

carrera_router = APIRouter(prefix="/carreras", tags=["Carreras"])


@carrera_router.post("", status_code=201)
async def create_carrera(
    request: Request,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    data = await get_form_data(request)

    name = data.get("name")
    materias_opcionales = str(data.get("materias_opcionales", "")) or ""
    materias_obligatorias = str(data.get("materias_obligatorias", "")) or ""

    nueva = Carrera(name=name)
    db.add(nueva)
    await db.flush()

    opcional_ids = parse_ids(materias_opcionales)
    obligatoria_ids = parse_ids(materias_obligatorias)

    if opcional_ids:
        result = await db.execute(select(Materia).where(Materia.id.in_(opcional_ids)))
        for m in result.scalars():
            db.add(
                CarreraMateria(carrera_id=nueva.id, materia_id=m.id, tipo="opcional")
            )

    if obligatoria_ids:
        result = await db.execute(
            select(Materia).where(Materia.id.in_(obligatoria_ids))
        )
        for m in result.scalars():
            db.add(
                CarreraMateria(carrera_id=nueva.id, materia_id=m.id, tipo="obligatoria")
            )

    await db.commit()
    await db.refresh(nueva)
    return {"id": nueva.id, "name": nueva.name}


@carrera_router.get("")
async def get_carreras(
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Carrera).order_by(Carrera.name))
    carreras = result.scalars().all()

    response = []
    for c in carreras:
        result_materias = await db.execute(
            select(CarreraMateria).where(CarreraMateria.carrera_id == c.id)
        )
        materias = result_materias.scalars().all()

        obligatorias = []
        opcionales = []

        for mat in materias:
            result_m = await db.execute(
                select(Materia).where(Materia.id == mat.materia_id)
            )
            materia = result_m.scalar_one_or_none()
            if materia:
                mat_data = {"id": materia.id, "name": materia.name}
                if mat.tipo == "obligatoria":
                    obligatorias.append(mat_data)
                else:
                    opcionales.append(mat_data)

        result_perfiles = await db.execute(
            select(Perfil).where(Perfil.carrera_id == c.id)
        )
        perfiles = result_perfiles.scalars().all()

        response.append(
            {
                "id": c.id,
                "name": c.name,
                "materias_obligatorias": obligatorias,
                "materias_opcionales": opcionales,
                "perfiles": [{"id": p.id, "name": p.name} for p in perfiles],
            }
        )

    return response


@carrera_router.get("/{id}")
async def get_carrera(
    id: int,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Carrera).where(Carrera.id == id))
    carrera = result.scalar_one_or_none()
    if not carrera:
        raise HTTPException(404, "Carrera not found")

    result_materias = await db.execute(
        select(CarreraMateria).where(CarreraMateria.carrera_id == id)
    )
    materias = result_materias.scalars().all()

    obligatorias = []
    opcionales = []

    for mat in materias:
        result_m = await db.execute(select(Materia).where(Materia.id == mat.materia_id))
        materia = result_m.scalar_one_or_none()
        if materia:
            mat_data = {"id": materia.id, "name": materia.name}
            if mat.tipo == "obligatoria":
                obligatorias.append(mat_data)
            else:
                opcionales.append(mat_data)

    result_perfiles = await db.execute(select(Perfil).where(Perfil.carrera_id == id))
    perfiles = result_perfiles.scalars().all()

    return {
        "id": carrera.id,
        "name": carrera.name,
        "materias_obligatorias": obligatorias,
        "materias_opcionales": opcionales,
        "perfiles": [{"id": p.id, "name": p.name} for p in perfiles],
    }


@carrera_router.patch("/{id}")
async def update_carrera(
    id: int,
    request: Request,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Carrera).where(Carrera.id == id))
    carrera = result.scalar_one_or_none()
    if not carrera:
        raise HTTPException(404, "Carrera not found")

    data = await get_form_data(request)

    if "name" in data and data["name"]:
        carrera.name = data["name"]

    # Update materias
    if "materias_obligatorias" in data or "materias_opcionales" in data:
        # Delete existing relaciones
        result_del = await db.execute(
            select(CarreraMateria).where(CarreraMateria.carrera_id == id)
        )
        existing = result_del.scalars().all()
        for e in existing:
            await db.delete(e)

        # Add new obligatorias
        obligatorias = str(data.get("materias_obligatorias", "")) or ""
        if obligatorias:
            ids = [
                int(x.strip()) for x in obligatorias.split(",") if x.strip().isdigit()
            ]
            result_m = await db.execute(select(Materia).where(Materia.id.in_(ids)))
            for m in result_m.scalars():
                db.add(
                    CarreraMateria(carrera_id=id, materia_id=m.id, tipo="obligatoria")
                )

        # Add new opcionales
        opcionales = str(data.get("materias_opcionales", "")) or ""
        if opcionales:
            ids = [int(x.strip()) for x in opcionales.split(",") if x.strip().isdigit()]
            result_m = await db.execute(select(Materia).where(Materia.id.in_(ids)))
            for m in result_m.scalars():
                db.add(CarreraMateria(carrera_id=id, materia_id=m.id, tipo="opcional"))

    await db.commit()
    await db.refresh(carrera)
    return {"id": carrera.id, "name": carrera.name}


@carrera_router.delete("/{id}", status_code=204)
async def delete_carrera(
    id: int,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Carrera).where(Carrera.id == id))
    carrera = result.scalar_one_or_none()
    if not carrera:
        raise HTTPException(404, "Carrera not found")
    await db.delete(carrera)
    await db.commit()
    return None


# -------------------------
# PERFILES
# -------------------------

perfil_router = APIRouter(prefix="/perfiles", tags=["Perfiles"])


@perfil_router.post("", status_code=201)
async def create_perfil(
    request: Request,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    data = await get_form_data(request)

    name = data.get("name")
    carrera_id = int(data.get("carrera_id") or 0)
    materias_obligatorias = str(data.get("materias_obligatorias", "")) or ""

    if not carrera_id:
        raise HTTPException(400, "carrera_id is required")

    result = await db.execute(select(Carrera).where(Carrera.id == carrera_id))
    carrera = result.scalar_one_or_none()
    if not carrera:
        raise HTTPException(404, "Carrera not found")

    nuevo = Perfil(name=name, carrera_id=carrera_id)
    db.add(nuevo)
    await db.flush()

    obligatoria_ids = parse_ids(materias_obligatorias)

    if obligatoria_ids:
        result = await db.execute(
            select(Materia).where(Materia.id.in_(obligatoria_ids))
        )
        for m in result.scalars():
            db.add(
                PerfilMateria(perfil_id=nuevo.id, materia_id=m.id, tipo="obligatoria")
            )

    await db.commit()
    await db.refresh(nuevo)
    return {"id": nuevo.id, "name": nuevo.name, "carrera_id": nuevo.carrera_id}


@perfil_router.get("/by-carrera/{carrera_id}")
async def get_perfiles_by_carrera(
    carrera_id: int,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Perfil).where(Perfil.carrera_id == carrera_id))
    perfiles = result.scalars().all()

    response = []
    for p in perfiles:
        result_materias = await db.execute(
            select(PerfilMateria).where(PerfilMateria.perfil_id == p.id)
        )
        materias = result_materias.scalars().all()

        obligatorias = []
        for mat in materias:
            result_m = await db.execute(
                select(Materia).where(Materia.id == mat.materia_id)
            )
            materia = result_m.scalar_one_or_none()
            if materia:
                obligatorias.append({"id": materia.id, "name": materia.name})

        response.append(
            {
                "id": p.id,
                "name": p.name,
                "carrera_id": p.carrera_id,
                "materias_obligatorias": obligatorias,
            }
        )

    return response


@perfil_router.patch("/{id}")
async def update_perfil(
    id: int,
    request: Request,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Perfil).where(Perfil.id == id))
    perfil = result.scalar_one_or_none()
    if not perfil:
        raise HTTPException(404, "Perfil not found")

    data = await get_form_data(request)

    if "name" in data and data["name"]:
        perfil.name = data["name"]

    # Update materias
    if "materias_obligatorias" in data:
        # Delete existing relaciones
        result_del = await db.execute(
            select(PerfilMateria).where(PerfilMateria.perfil_id == id)
        )
        existing = result_del.scalars().all()
        for e in existing:
            await db.delete(e)

        # Add new obligatorias
        obligatorias = str(data.get("materias_obligatorias", "")) or ""
        if obligatorias:
            ids = [
                int(x.strip()) for x in obligatorias.split(",") if x.strip().isdigit()
            ]
            result_m = await db.execute(select(Materia).where(Materia.id.in_(ids)))
            for m in result_m.scalars():
                db.add(PerfilMateria(perfil_id=id, materia_id=m.id, tipo="obligatoria"))

    await db.commit()
    await db.refresh(perfil)
    return {"id": perfil.id, "name": perfil.name, "carrera_id": perfil.carrera_id}


@perfil_router.delete("/{id}", status_code=204)
async def delete_perfil(
    id: int,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Perfil).where(Perfil.id == id))
    perfil = result.scalar_one_or_none()
    if not perfil:
        raise HTTPException(404, "Perfil not found")

    # Delete related PerfilMateria
    result_materias = await db.execute(
        select(PerfilMateria).where(PerfilMateria.perfil_id == id)
    )
    materias = result_materias.scalars().all()
    for m in materias:
        await db.delete(m)

    await db.delete(perfil)
    await db.commit()
    return None


# -------------------------
# INSTITUTOS
# -------------------------

instituto_router = APIRouter(prefix="/institutos", tags=["Institutos"])


@instituto_router.post("", status_code=201)
async def create_instituto(
    request: Request,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    data = await get_form_data(request)

    name = data.get("name")
    if not name:
        raise HTTPException(400, "name is required")

    nuevo = Instituto(name=name)
    db.add(nuevo)
    await db.commit()
    await db.refresh(nuevo)
    return {"id": nuevo.id, "name": nuevo.name}


@instituto_router.get("")
async def get_institutos(
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Instituto).order_by(Instituto.name))
    institutos = result.scalars().all()
    return [{"id": i.id, "name": i.name} for i in institutos]


@instituto_router.get("/{id}")
async def get_instituto(
    id: int,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Instituto).where(Instituto.id == id))
    instituto = result.scalar_one_or_none()
    if not instituto:
        raise HTTPException(404, "Instituto not found")
    return {"id": instituto.id, "name": instituto.name}


@instituto_router.patch("/{id}")
async def update_instituto(
    id: int,
    request: Request,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Instituto).where(Instituto.id == id))
    instituto = result.scalar_one_or_none()
    if not instituto:
        raise HTTPException(404, "Instituto not found")

    data = await get_form_data(request)

    if "name" in data and data["name"]:
        instituto.name = data["name"]

    await db.commit()
    await db.refresh(instituto)
    return {"id": instituto.id, "name": instituto.name}


@instituto_router.delete("/{id}", status_code=204)
async def delete_instituto(
    id: int,
    _: str = Depends(verify_token_dep),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Instituto).where(Instituto.id == id))
    instituto = result.scalar_one_or_none()
    if not instituto:
        raise HTTPException(404, "Instituto not found")
    await db.delete(instituto)
    await db.commit()
    return None
