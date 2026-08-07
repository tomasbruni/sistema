from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, SQLModel, select, func

from app.db.session import get_session
from app.db.models import Gasto, TipoGasto, TipoFactura, Usuario
from app.api.deps import get_current_user, require_admin, UsuarioActual
from app.api.funciones.fechas import start_of_day, end_of_day


router = APIRouter(prefix="/gastos", tags=["Gastos reales y facturados"])

CERO = Decimal("0.00")
DOS_DECIMALES = Decimal("0.01")


# ── Schemas ──────────────────────────────────────────────────────────────────

class GastoCreate(SQLModel):
    tipo: TipoGasto
    descripcion: str
    total: Optional[Decimal] = None   # requerido para REAL y factura C; en factura A se calcula (neto + iva)
    fecha: Optional[date] = None
    usuario_id: Optional[int] = None
    # Solo facturas:
    tipo_factura: Optional[TipoFactura] = None
    comprada: bool = False             # aplica solo a factura A
    porcentaje_real: Optional[int] = None  # n%, solo factura A comprada
    neto: Optional[Decimal] = None     # total productos (factura A)
    iva: Optional[Decimal] = None      # total IVA (factura A)


class GastoUpdate(SQLModel):
    descripcion: Optional[str] = None
    total: Optional[Decimal] = None
    fecha: Optional[date] = None
    tipo: Optional[TipoGasto] = None
    tipo_factura: Optional[TipoFactura] = None
    comprada: Optional[bool] = None
    porcentaje_real: Optional[int] = None
    neto: Optional[Decimal] = None
    iva: Optional[Decimal] = None


class GastoRead(SQLModel):
    id: int
    tipo: TipoGasto
    descripcion: str
    total: Decimal
    fecha: Optional[datetime]
    usuario_id: int
    tipo_factura: Optional[TipoFactura]
    comprada: bool
    porcentaje_real: Optional[int]
    neto: Optional[Decimal]
    iva: Optional[Decimal]
    aporte_real: Decimal
    aporte_blanco: Decimal
    aporte_iva: Decimal


class GastoTotales(SQLModel):
    total_real: Decimal
    total_blanco: Decimal
    iva_a_favor: Decimal
    cantidad: int


# ── Logica de negocio ─────────────────────────────────────────────────────────

def _normalizar_y_calcular(data: dict, total_declarado: Optional[Decimal] = None) -> dict:
    """Valida un estado logico completo de gasto y devuelve los campos a persistir
    (montos normalizados + los 3 aportes calculados). Sirve tanto para crear como
    para actualizar (mergeando el payload sobre el registro existente).

    `total_declarado` es el total que el cliente mando EXPLICITAMENTE en este request
    (None si no lo mando). En factura A el total se calcula solo (neto + IVA); este
    parametro solo se usa como defensa: si el cliente igual manda un total, tiene que
    coincidir. Se pasa aparte del estado mergeado para no comparar contra el total
    viejo arrastrado del registro durante un PATCH."""
    tipo: TipoGasto = data["tipo"]

    campos = {
        "tipo": tipo,
        "descripcion": data.get("descripcion"),
        "tipo_factura": None,
        "comprada": False,
        "porcentaje_real": None,
        "neto": None,
        "iva": None,
    }

    if tipo == TipoGasto.REAL:
        total = data.get("total")
        if total is None:
            raise HTTPException(422, "Un gasto real necesita 'total'")
        total = Decimal(total)
        campos["total"] = total
        aporte_real, aporte_blanco, aporte_iva = total, CERO, CERO

    else:  # FACTURA
        tipo_factura = data.get("tipo_factura")
        if tipo_factura is None:
            raise HTTPException(422, "Una factura necesita 'tipo_factura' (A o C)")
        campos["tipo_factura"] = tipo_factura

        if tipo_factura == TipoFactura.A:
            neto = data.get("neto")
            iva = data.get("iva")
            if neto is None or iva is None:
                raise HTTPException(422, "La factura A necesita 'neto' e 'iva'")
            neto, iva = Decimal(neto), Decimal(iva)
            total = (neto + iva).quantize(DOS_DECIMALES, ROUND_HALF_UP)
            # Defensa: hoy el total de la factura A se calcula solo (el front no lo manda).
            # Si en el futuro se permite cargarlo, tiene que coincidir con neto + IVA.
            if total_declarado is not None and Decimal(total_declarado) != total:
                raise HTTPException(
                    422,
                    f"El total ({Decimal(total_declarado)}) no coincide con neto + IVA ({total})",
                )
            campos.update(neto=neto, iva=iva, total=total)

            comprada = bool(data.get("comprada"))
            campos["comprada"] = comprada
            aporte_blanco, aporte_iva = neto, iva
            if comprada:
                pct = data.get("porcentaje_real")
                if pct is None:
                    raise HTTPException(422, "La factura A comprada necesita 'porcentaje_real'")
                if pct < 0 or pct > 100:
                    raise HTTPException(422, "'porcentaje_real' debe estar entre 0 y 100")
                campos["porcentaje_real"] = pct
                aporte_real = (total * Decimal(pct) / Decimal(100)).quantize(DOS_DECIMALES, ROUND_HALF_UP)
            else:
                aporte_real = CERO

        elif tipo_factura == TipoFactura.C:
            total = data.get("total")
            if total is None:
                raise HTTPException(422, "La factura C necesita 'total'")
            total = Decimal(total)
            campos["total"] = total
            aporte_real, aporte_blanco, aporte_iva = CERO, total, CERO
        else:
            raise HTTPException(422, f"tipo_factura invalido: {tipo_factura}")

    campos["aporte_real"] = aporte_real
    campos["aporte_blanco"] = aporte_blanco
    campos["aporte_iva"] = aporte_iva
    return campos


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=GastoRead, status_code=status.HTTP_201_CREATED)
def crear_gasto(
    payload: GastoCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    if payload.descripcion is None or not payload.descripcion.strip():
        raise HTTPException(422, "'descripcion' es obligatoria")

    campos = _normalizar_y_calcular(payload.model_dump(), total_declarado=payload.total)

    usuario_id = payload.usuario_id or current_user.usuario_id
    if payload.usuario_id is not None and not session.get(Usuario, payload.usuario_id):
        raise HTTPException(404, "Usuario no existe")

    gasto = Gasto(**campos, usuario_id=usuario_id)
    if payload.fecha is not None:
        gasto.fecha = start_of_day(payload.fecha)

    session.add(gasto)
    session.commit()
    session.refresh(gasto)
    return gasto


@router.get("/", response_model=list[GastoRead])
def listar_gastos(
    fecha: Optional[date] = Query(default=None, description="Dia exacto (YYYY-MM-DD)"),
    fecha_desde: Optional[date] = Query(default=None),
    fecha_hasta: Optional[date] = Query(default=None),
    tipo: Optional[TipoGasto] = Query(default=None),
    tipo_factura: Optional[TipoFactura] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    query = select(Gasto)
    query = _aplicar_filtros(query, fecha, fecha_desde, fecha_hasta, tipo, tipo_factura)
    query = query.order_by(Gasto.fecha.desc(), Gasto.id.desc()).offset(offset).limit(limit)  # type: ignore
    return session.exec(query).all()


@router.get("/totales", response_model=GastoTotales)
def totales_gastos(
    fecha: Optional[date] = Query(default=None, description="Dia exacto (YYYY-MM-DD)"),
    fecha_desde: Optional[date] = Query(default=None),
    fecha_hasta: Optional[date] = Query(default=None),
    tipo: Optional[TipoGasto] = Query(default=None),
    tipo_factura: Optional[TipoFactura] = Query(default=None),
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    query = select(
        func.coalesce(func.sum(Gasto.aporte_real), 0),
        func.coalesce(func.sum(Gasto.aporte_blanco), 0),
        func.coalesce(func.sum(Gasto.aporte_iva), 0),
        func.count(Gasto.id), #type: ignore
    )
    query = _aplicar_filtros(query, fecha, fecha_desde, fecha_hasta, tipo, tipo_factura)
    total_real, total_blanco, iva_a_favor, cantidad = session.exec(query).one()
    return GastoTotales(
        total_real=Decimal(total_real),
        total_blanco=Decimal(total_blanco),
        iva_a_favor=Decimal(iva_a_favor),
        cantidad=cantidad,
    )


@router.get("/{gasto_id}", response_model=GastoRead)
def obtener_gasto(
    gasto_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    gasto = session.get(Gasto, gasto_id)
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return gasto


@router.patch("/{gasto_id}", response_model=GastoRead)
def actualizar_gasto(
    gasto_id: int,
    payload: GastoUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    gasto = session.get(Gasto, gasto_id)
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    cambios = payload.model_dump(exclude_unset=True)
    fecha = cambios.pop("fecha", None)

    # Merge del estado actual con los cambios y re-validacion / recalculo completo.
    estado = {
        "tipo": gasto.tipo,
        "descripcion": gasto.descripcion,
        "total": gasto.total,
        "tipo_factura": gasto.tipo_factura,
        "comprada": gasto.comprada,
        "porcentaje_real": gasto.porcentaje_real,
        "neto": gasto.neto,
        "iva": gasto.iva,
    }
    estado.update(cambios)

    if estado.get("descripcion") is None or not str(estado["descripcion"]).strip():
        raise HTTPException(422, "'descripcion' es obligatoria")

    campos = _normalizar_y_calcular(estado, total_declarado=cambios.get("total"))
    for campo, valor in campos.items():
        setattr(gasto, campo, valor)
    if fecha is not None:
        gasto.fecha = start_of_day(fecha)

    session.add(gasto)
    session.commit()
    session.refresh(gasto)
    return gasto


@router.delete("/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_gasto(
    gasto_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin),
):
    gasto = session.get(Gasto, gasto_id)
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    session.delete(gasto)
    session.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _aplicar_filtros(query, fecha, fecha_desde, fecha_hasta, tipo, tipo_factura):
    if fecha:
        query = query.where(
            Gasto.fecha >= start_of_day(fecha),  # type: ignore
            Gasto.fecha <= end_of_day(fecha),    # type: ignore
        )
    else:
        if fecha_desde:
            query = query.where(Gasto.fecha >= start_of_day(fecha_desde))  # type: ignore
        if fecha_hasta:
            query = query.where(Gasto.fecha <= end_of_day(fecha_hasta))    # type: ignore
    if tipo is not None:
        query = query.where(Gasto.tipo == tipo)
    if tipo_factura is not None:
        query = query.where(Gasto.tipo_factura == tipo_factura)
    return query
