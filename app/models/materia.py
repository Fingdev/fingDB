from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.schemas.materia import PeriodoEnum


class TipoPreviaEnum(str, Enum):
    aprobado = "aprobado"
    exonerado = "exonerado"


class MateriaPrevia(Base):
    __tablename__ = "materia_previas"
    __table_args__ = (
        PrimaryKeyConstraint("materia_id", "previa_id", "tipo"),
        UniqueConstraint("materia_id", "previa_id", "tipo"),
    )

    materia_id: Mapped[int] = mapped_column(
        ForeignKey("materias.id", ondelete="CASCADE"),
    )

    previa_id: Mapped[int] = mapped_column(
        ForeignKey("materias.id", ondelete="CASCADE"),
    )

    tipo: Mapped[TipoPreviaEnum] = mapped_column(
        SAEnum(TipoPreviaEnum, name="tipo_previa_enum"),
    )

    materia: Mapped["Materia"] = relationship(
        "Materia",
        foreign_keys=[materia_id],
        back_populates="previas_rel",
    )

    previa: Mapped["Materia"] = relationship(
        "Materia",
        foreign_keys=[previa_id],
    )


class Materia(Base):
    __tablename__ = "materias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    periodo: Mapped[PeriodoEnum] = mapped_column(
        SAEnum(PeriodoEnum, name="periodo_enum"),
        nullable=False,
    )
    creditos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_creditos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=None, nullable=True
    )

    instituto_id: Mapped[int] = mapped_column(
        ForeignKey("institutos.id", ondelete="CASCADE"),
        nullable=False,
    )

    instituto: Mapped["Instituto"] = relationship(
        "Instituto",
        back_populates="materias",
    )

    previas_rel: Mapped[List["MateriaPrevia"]] = relationship(
        "MateriaPrevia",
        foreign_keys="[MateriaPrevia.materia_id]",
        back_populates="materia",
        cascade="all, delete-orphan",
    )

    @property
    def prev_aprobado(self) -> List["Materia"]:
        return [
            rel.previa
            for rel in self.previas_rel
            if rel.tipo == TipoPreviaEnum.aprobado
        ]

    @property
    def prev_exonerado(self) -> List["Materia"]:
        return [
            rel.previa
            for rel in self.previas_rel
            if rel.tipo == TipoPreviaEnum.exonerado
        ]


class Perfil(Base):
    __tablename__ = "perfiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    carrera_id: Mapped[int] = mapped_column(
        ForeignKey("carreras.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    carrera: Mapped["Carrera"] = relationship(
        "Carrera",
        back_populates="perfiles",
    )

    materias_rel: Mapped[List["PerfilMateria"]] = relationship(
        "PerfilMateria",
        back_populates="perfil",
        cascade="all, delete-orphan",
    )

    @property
    def materias_obligatorias(self) -> List["Materia"]:
        return [rel.materia for rel in self.materias_rel if rel.tipo == "obligatoria"]


class Instituto(Base):
    __tablename__ = "institutos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    materias: Mapped[List["Materia"]] = relationship(
        "Materia",
        back_populates="instituto",
        cascade="all, delete-orphan",
    )


class CarreraMateria(Base):
    __tablename__ = "carrera_materias"
    __table_args__ = (UniqueConstraint("carrera_id", "materia_id", "tipo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    carrera_id: Mapped[int] = mapped_column(
        ForeignKey("carreras.id", ondelete="CASCADE"),
        nullable=False,
    )
    materia_id: Mapped[int] = mapped_column(
        ForeignKey("materias.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)

    carrera: Mapped["Carrera"] = relationship("Carrera", back_populates="materias_rel")
    materia: Mapped["Materia"] = relationship("Materia")


class PerfilMateria(Base):
    __tablename__ = "perfil_materias"
    __table_args__ = (UniqueConstraint("perfil_id", "materia_id", "tipo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    perfil_id: Mapped[int] = mapped_column(
        ForeignKey("perfiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    materia_id: Mapped[int] = mapped_column(
        ForeignKey("materias.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)

    perfil: Mapped["Perfil"] = relationship("Perfil", back_populates="materias_rel")
    materia: Mapped["Materia"] = relationship("Materia")


class Carrera(Base):
    __tablename__ = "carreras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    materias_rel: Mapped[List["CarreraMateria"]] = relationship(
        "CarreraMateria",
        back_populates="carrera",
        cascade="all, delete-orphan",
    )

    perfiles: Mapped[List["Perfil"]] = relationship(
        "Perfil",
        back_populates="carrera",
        cascade="all, delete-orphan",
    )

    @property
    def materias_opcionales(self) -> List["Materia"]:
        return [rel.materia for rel in self.materias_rel if rel.tipo == "opcional"]

    @property
    def materias_obligatorias(self) -> List["Materia"]:
        return [rel.materia for rel in self.materias_rel if rel.tipo == "obligatoria"]
