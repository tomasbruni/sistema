from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel

from typing import Optional, List
from sqlmodel import Session, SQLModel, select, col
from sqlalchemy import exc

from app.db.session import get_session
from app.db.models import *

from app.api.modelscreate import *
from app.api.modelsupdate import *
from app.api.funciones.accesorios_funciones import normalizar_texto, generar_sku_accesorio, generar_nombre_accesorio
from app.api.deps import get_current_user, require_admin, UsuarioActual

from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from io import BytesIO
from openpyxl.styles import Font, PatternFill, Alignment

router = APIRouter(prefix="/accesorios",
                   tags=["ACCESORIOS"],
                   responses={404: {"message": "No encontrado"}})


class SeedAccesorioItem(BaseModel):
    tipo: str
    subtipo: Optional[str] = None
    nombre: str
    precio: int


class SeedAccesoriosRequest(BaseModel):
    data: List[SeedAccesorioItem]


@router.post("/seed")
def seed_accesorios(
    request: SeedAccesoriosRequest,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Carga masiva de accesorios referenciando tipo y subtipo por nombre.
    Es idempotente: si ya existe un accesorio con el mismo nombre+tipo+subtipo lo omite.
    Crea entradas de stock en 0 para cada local.
    """
    locales = session.exec(select(Local)).all()
    if not locales:
        raise HTTPException(status_code=400, detail="No hay locales registrados")

    creados = []
    omitidos = []
    errores = []

    for item in request.data:
        # Resolver tipo por nombre
        tipo = session.exec(
            select(TipoAccesorio).where(TipoAccesorio.nombre == item.tipo)
        ).first()
        if not tipo:
            errores.append({"item": item.nombre, "motivo": f"Tipo '{item.tipo}' no encontrado"})
            continue

        # Resolver subtipo por nombre (opcional)
        subtipo_id = None
        if item.subtipo:
            subtipo = session.exec(
                select(SubtipoAccesorio).where(
                    SubtipoAccesorio.tipo_id == tipo.tipo_id,
                    SubtipoAccesorio.nombre == item.subtipo
                )
            ).first()
            if not subtipo:
                errores.append({"item": item.nombre, "motivo": f"Subtipo '{item.subtipo}' no encontrado para tipo '{item.tipo}'"})
                continue
            subtipo_id = subtipo.subtipo_id

        # Verificar duplicado
        stmt = select(Accesorio).where(
            Accesorio.nombre == item.nombre,
            Accesorio.tipo_id == tipo.tipo_id,
            Accesorio.activo == True,  # type: ignore
        )
        stmt = stmt.where(Accesorio.subtipo_id == subtipo_id)
        if session.exec(stmt).first():
            omitidos.append(item.nombre)
            continue

        try:
            sku = generar_sku_accesorio(tipo_id=tipo.tipo_id, session=session, subtipo_id=subtipo_id)  # type: ignore
            accesorio = Accesorio(
                nombre=item.nombre,
                precio=item.precio,
                tipo_id=tipo.tipo_id,
                subtipo_id=subtipo_id,
                sku=sku,
            )
            session.add(accesorio)
            session.flush()

            session.add_all([
                StockAccesorio(accesorio_id=accesorio.accesorio_id, local_id=local.local_id, cantidad=0)  # type: ignore
                for local in locales
            ])
            creados.append({"nombre": item.nombre, "sku": sku, "tipo": item.tipo, "subtipo": item.subtipo})
        except Exception as e:
            session.rollback()
            errores.append({"item": item.nombre, "motivo": str(e)})
            continue

    session.commit()

    return {
        "creados": creados,
        "omitidos": omitidos,
        "errores": errores,
    }


@router.get("/export")
def exportar_accesorios(
    buscar: Optional[str] = "",
    tipo_id: Optional[int] = None,
    subtipo_id: Optional[int] = None,
    activo: Optional[bool] = True,
    session: Session = Depends(get_session)
):
    statement = select(Accesorio)
    if activo is not None:
        statement = statement.where(Accesorio.activo == activo)
    if buscar:
        statement = statement.where(Accesorio.nombre.ilike(f"%{buscar}%"))  # type: ignore
    if tipo_id is not None:
        statement = statement.where(Accesorio.tipo_id == tipo_id)
    if subtipo_id is not None:
        statement = statement.where(Accesorio.subtipo_id == subtipo_id)

    accesorios = session.exec(statement).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Accesorios"  # type: ignore

    header_font  = Font(bold=True, color="FFFFFF")
    header_fill  = PatternFill(fill_type="solid", fgColor="1A1A2E")
    header_align = Alignment(horizontal="center")

    columnas = ["ID", "SKU", "Nombre", "Tipo ID", "Subtipo ID", "Marca Celular ID", "Modelo Celular ID", "Precio", "Activo"]
    for col_idx, titulo in enumerate(columnas, start=1):
        cell = ws.cell(row=1, column=col_idx, value=titulo)  # type: ignore
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align

    for a in accesorios:
        ws.append([  # type: ignore
            a.accesorio_id,
            a.sku,
            a.nombre,
            a.tipo_id,
            a.subtipo_id,
            a.marca_celular_id,
            a.modelo_celular_id,
            a.precio,
            a.activo,
        ])

    anchos = {"A": 8, "B": 14, "C": 40, "D": 10, "E": 12, "F": 16, "G": 18, "H": 12, "I": 10}
    for col_letra, ancho in anchos.items():
        ws.column_dimensions[col_letra].width = ancho  # type: ignore

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=accesorios.xlsx"}
    )


# @router.post("/sugerir-nombre")
# def sugerir_nombre_accesorio(
#     data: AccesorioCreate,
#     session: Session = Depends(get_session)
# ):
#     nombre_base = generar_nombre_accesorio(
#         tipo_id=data.tipo_id,
#         session=session,
#         subtipo_id=data.subtipo_id,
#         marca_id=data.marca_id,
#         marca_celular_id=data.marca_celular_id,
#         modelo_celular_id=data.modelo_celular_id
#     )
#     return {"nombre_sugerido": nombre_base}


@router.post("/verificar-duplicado")
def verificar_duplicado(
    data: AccesorioCreate,
    session: Session = Depends(get_session)
):
    statement = select(Accesorio).where(
        Accesorio.nombre  == data.nombre,
        Accesorio.tipo_id == data.tipo_id,  # type: ignore
        Accesorio.activo  == True           # type: ignore
    )

    if data.subtipo_id:
        statement = statement.where(Accesorio.subtipo_id == data.subtipo_id)
    else:
        statement = statement.where(Accesorio.subtipo_id == None)

    if data.marca_celular_id:
        statement = statement.where(Accesorio.marca_celular_id == data.marca_celular_id)
    else:
        statement = statement.where(Accesorio.marca_celular_id == None)

    if data.modelo_celular_id:
        statement = statement.where(Accesorio.modelo_celular_id == data.modelo_celular_id)
    else:
        statement = statement.where(Accesorio.modelo_celular_id == None)

    if data.marca_id:
        statement = statement.where(Accesorio.marca_id == data.marca_id)
    else:
        statement = statement.where(Accesorio.marca_id == None)

    similares = session.exec(statement).all()

    if not similares:
        return {"tiene_duplicados": False, "duplicados": []}

    duplicado_exacto = next((s for s in similares if s.precio == data.precio), None)

    return {
        "tiene_duplicados": True,
        "es_duplicado_exacto": duplicado_exacto is not None,
        "duplicados": [
            {
                "sku": s.sku,
                "nombre": s.nombre,
                "precio": s.precio,
                "es_mismo_precio": s.precio == data.precio
            }
            for s in similares
        ]
    }


@router.post("/")
def crear_accesorio(
    accesorio_data: AccesorioCreate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    # No se puede especificar marca_celular sola sin modelo, ni modelo sin marca_celular
    if accesorio_data.modelo_celular_id and not accesorio_data.marca_celular_id:
        raise HTTPException(
            status_code=400,
            detail="Si se especifica un modelo de celular, se debe especificar también la marca"
        )

    # Validar que el modelo pertenece a la marca si ambos vienen
    if accesorio_data.marca_celular_id and accesorio_data.modelo_celular_id:
        modelo = session.get(ModeloCelular, accesorio_data.modelo_celular_id)
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo de celular no encontrado")
        if modelo.marca_celular_id != accesorio_data.marca_celular_id:
            raise HTTPException(status_code=400, detail="El modelo no pertenece a la marca indicada")

    try:
        locales = session.exec(select(Local)).all()
        if not locales:
            raise HTTPException(status_code=400, detail="No hay locales")

        sku = generar_sku_accesorio(
            tipo_id=accesorio_data.tipo_id,
            session=session,
            subtipo_id=accesorio_data.subtipo_id,
            marca_id=accesorio_data.marca_id,
            marca_celular_id=accesorio_data.marca_celular_id,
            modelo_celular_id=accesorio_data.modelo_celular_id
        )

        accesorio = Accesorio(**accesorio_data.model_dump(), sku=sku)
        session.add(accesorio)
        session.flush()

        lista_stocks = [
            StockAccesorio(
                accesorio_id=accesorio.accesorio_id,  # type: ignore
                local_id=local.local_id,              # type: ignore
                cantidad=0
            )
            for local in locales
        ]
        session.add_all(lista_stocks)
        session.commit()
        session.refresh(accesorio)
        for stock in lista_stocks:
            session.refresh(stock)

        return {"accesorio": accesorio, "lista-stocks": lista_stocks}

    except ValueError as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig))
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear accesorio: {str(e)}")


@router.get("/{accesorio_id}")
def obtener_accesorio(
    accesorio_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    accesorio = session.get(Accesorio, accesorio_id)
    if not accesorio:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    return accesorio


@router.patch("/{accesorio_id}")
def actualizar_accesorio(
    accesorio_id: int,
    accesorio_data: AccesorioUpdate,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    accesorio = session.get(Accesorio, accesorio_id)
    if not accesorio:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")

    try:
        update_data = accesorio_data.model_dump(exclude_unset=True)

        # Validar consistencia marca/modelo si alguno de los dos viene en el update
        marca_celular_id = update_data.get("marca_celular_id", accesorio.marca_celular_id)
        modelo_celular_id = update_data.get("modelo_celular_id", accesorio.modelo_celular_id)

        if modelo_celular_id and not marca_celular_id:
            raise HTTPException(status_code=400, detail="Si se especifica un modelo, se debe especificar también la marca")

        if marca_celular_id and modelo_celular_id:
            modelo = session.get(ModeloCelular, modelo_celular_id)
            if not modelo:
                raise HTTPException(status_code=404, detail="Modelo de celular no encontrado")
            if modelo.marca_celular_id != marca_celular_id:
                raise HTTPException(status_code=400, detail="El modelo no pertenece a la marca indicada")

        for key, value in update_data.items():
            setattr(accesorio, key, value)

        session.add(accesorio)
        session.commit()
        session.refresh(accesorio)
        return accesorio

    except HTTPException:
        session.rollback()
        raise
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo actualizar el accesorio. Verifique que los campos seleccionados existan."
        )


@router.get("/", response_model=list[Accesorio])
def listar_accesorios(
    skip: int = 0,
    limit: int = 100,
    buscar: Optional[str] = "",
    tipo_id: Optional[int] = None,
    subtipo_id: Optional[int] = None,
    marca_celular_id: Optional[int] = None,
    modelo_celular_id: Optional[int] = None,
    activo: Optional[bool] = True,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    statement = select(Accesorio).offset(skip).limit(limit)

    if activo is not None:
        statement = statement.where(Accesorio.activo == activo)
    if buscar:
        statement = statement.where(Accesorio.nombre.ilike(f"%{buscar}%"))  # type: ignore
    if tipo_id is not None:
        statement = statement.where(Accesorio.tipo_id == tipo_id)
    if subtipo_id is not None:
        statement = statement.where(Accesorio.subtipo_id == subtipo_id)
    if marca_celular_id is not None:
        statement = statement.where(Accesorio.marca_celular_id == marca_celular_id)
    if modelo_celular_id is not None:
        statement = statement.where(Accesorio.modelo_celular_id == modelo_celular_id)

    return session.exec(statement).all()


@router.delete("/{accesorio_id}")
def eliminar_accesorio(
    accesorio_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Elimina físicamente si nunca tuvo ventas ni movimientos.
    Si tiene ventas o movimientos, lo desactiva.
    """
    try:
        accesorio = session.get(Accesorio, accesorio_id)
        if not accesorio:
            raise HTTPException(status_code=404, detail="Accesorio no encontrado")

        tiene_ventas = session.exec(
            select(DetalleVentaAccesorio).where(DetalleVentaAccesorio.accesorio_id == accesorio_id)
        ).first() is not None

        tiene_movimientos = session.exec(
            select(MovimientoStock).where(MovimientoStock.accesorio_id == accesorio_id)
        ).first() is not None

        if tiene_ventas or tiene_movimientos:
            accesorio.activo = False
            session.commit()

            razones = []
            if tiene_ventas:
                razones.append("ventas asociadas")
            if tiene_movimientos:
                razones.append("movimientos de stock")

            return {
                "mensaje": f"Accesorio desactivado ({', '.join(razones)})",
                "accion": "desactivado",
                "accesorio_id": accesorio_id,
                "razones": razones
            }

        else:
            stocks = session.exec(
                select(StockAccesorio).where(StockAccesorio.accesorio_id == accesorio_id)
            ).all()
            for stock in stocks:
                session.delete(stock)
            session.flush()
            session.delete(accesorio)
            session.commit()

            return {
                "mensaje": "Accesorio eliminado correctamente",
                "accion": "eliminado",
                "accesorio_id": accesorio_id
            }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar accesorio: {str(e)}")