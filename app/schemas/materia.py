from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any


class PeriodoEnum(str, Enum):
    BISEMESTRAL = "bisemestral"
    PAR = "par"
    IMPAR = "impar"


class TipoPreviaEnum(str, Enum):
    aprobado = "aprobado"
    exonerado = "exonerado"


# -------------------------
# BASE
# -------------------------


class MateriaBase(BaseModel):
    name: str
    codigo: Optional[str] = None
    periodo: PeriodoEnum
    creditos: int = 0
    min_creditos: Optional[int] = None
    instituto_id: int


# -------------------------
# CREATE
# -------------------------


class MateriaCreate(MateriaBase):
    previas_aprobado: str = ""
    previas_exonerado: str = ""


# -------------------------
# UPDATE
# -------------------------


class MateriaUpdate(MateriaBase):
    previas_aprobado: str = ""
    previas_exonerado: str = ""
    instituto_id: int


# -------------------------
# READ
# -------------------------


class MateriaRead(MateriaBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# -------------------------
# DELETE
# -------------------------


class MateriaDelete(BaseModel):
    pass


# -------------------------
# CARRERA
# -------------------------


class CarreraBase(BaseModel):
    name: str


class CarreraCreate(CarreraBase):
    materias_opcionales: str = ""
    materias_obligatorias: str = ""


class CarreraUpdate(CarreraBase):
    pass


class CarreraRead(CarreraBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# PERFIL
# -------------------------


class PerfilBase(BaseModel):
    name: str
    carrera_id: int


class PerfilCreate(PerfilBase):
    materias_obligatorias: str = ""


class PerfilUpdate(PerfilBase):
    pass


class PerfilRead(PerfilBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# INSTITUTO
# -------------------------


class InstitutoBase(BaseModel):
    name: str


class InstitutoCreate(InstitutoBase):
    pass


class InstitutoUpdate(InstitutoBase):
    pass


class InstitutoRead(InstitutoBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
