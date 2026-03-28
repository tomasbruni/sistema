from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from typing import Optional
from sqlmodel import Session, SQLModel, select, col
from sqlalchemy import exc

from app.db.session import get_session, SessionDep
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
                   #dependencies=[Depends(require_admin)],
                   responses = {404:{"message":"No encontrado"}})


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

    # ── Crear Excel ───────────────────────────────────────────────────────────
    wb = Workbook()
    ws = wb.active
    ws.title = "Accesorios"  # type: ignore

    header_font  = Font(bold=True, color="FFFFFF")
    header_fill  = PatternFill(fill_type="solid", fgColor="1A1A2E")
    header_align = Alignment(horizontal="center")

    columnas = ["ID", "SKU", "Nombre", "Tipo ID", "Subtipo ID", "Precio", "Activo"]
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
            a.precio,
            a.activo,
        ])

    anchos = {"A": 8, "B": 14, "C": 40, "D": 10, "E": 12, "F": 12, "G": 10}
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

@router.post("/sugerir-nombre")
def sugerir_nombre_accesorio(
    data: AccesorioCreate,
    session: Session = Depends(get_session)
):
    """
    Genera sugerencia de nombre para pre-completar en formulario.
    El usuario puede modificarlo para agregar detalles.
    """
    nombre_base = generar_nombre_accesorio(
        tipo_id=data.tipo_id,
        session=session,
        subtipo_id=data.subtipo_id,
        marca_id=data.marca_id,
        modelo_id=data.modelo_id
    )
    
    return {"nombre_sugerido": nombre_base}


@router.post("/verificar-duplicado")
def verificar_duplicado(
    data: AccesorioCreate,
    session: Session = Depends(get_session)
):
    """
    Verifica si ya existe un accesorio similar.
    Retorna información del duplicado si existe.
    """
    # SI ESTOY AGREGANDO FUNDA: 
        # HAY UNIQUE CONSTRAINT NOMBRE-TIPO-MODELO PARA CELULARES
    # Buscar productos idénticos (sin precio)
    #PRODUCTO IGUAL SIGNIFICARIA:
        # MISMO NOMBRE, TIPO
        # Y EXACTAMENTE IGUAL SIGNIFICARIA MISMO NOMBRE, TIPO, PRECIO 
    statement = select(Accesorio).where(
        #Accesorio.nombre == data.nombre, #type: ignore, quiero avisar al usuario
        #que existe un accesorio con las mismas caracteristicas, por si quiere
        #agregar un accesorio y se olvido que habia agregado con otro nombre
        Accesorio.nombre  == data.nombre,
        Accesorio.tipo_id == data.tipo_id, #type: ignore
        Accesorio.activo == True # type: ignore
    )
    
    # Agregar filtros opcionales
    # los else son para que se comparen tambien los campos donde hay NULL
    # osea se compara si el accesorio es exactamente igual
    if data.subtipo_id:
        statement = statement.where(Accesorio.subtipo_id == data.subtipo_id)
    else:
        statement = statement.where(Accesorio.subtipo_id == None)
    
    if data.modelo_id:
        statement = statement.where(Accesorio.modelo_id == data.modelo_id)
    else:
        statement = statement.where(Accesorio.modelo_id == None)
    
    if data.marca_id:
        statement = statement.where(Accesorio.marca_id == data.marca_id)
    else:
        statement = statement.where(Accesorio.marca_id == None)
    
    # Buscar todos los similares
    similares = session.exec(statement).all()
    
    if not similares:
        return {
            "tiene_duplicados": False,
            "duplicados": []
        }
    
    # Verificar si hay uno con el MISMO precio (duplicado exacto)
    duplicado_exacto = None
    for similar in similares:
        if similar.precio == data.precio:
            duplicado_exacto = similar # booleano global que indica si hay algun duplicado exacto
            break
    
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
    """Crea un nuevo accesorio con SKU generado automáticamente"""

    if accesorio_data.marca_id and accesorio_data.modelo_id:
        raise HTTPException(
            status_code=400,
            detail="No se puede especificar marca y modelo al mismo tiempo"
        )

    try:
        locales = session.exec(select(Local)).all()

        if not locales:
            raise HTTPException (
                status_code=400,
                detail= "No hay locales"
            )

        sku = generar_sku_accesorio(
            tipo_id=accesorio_data.tipo_id,
            session=session,
            subtipo_id=accesorio_data.subtipo_id,
            marca_id=accesorio_data.marca_id,
            modelo_id=accesorio_data.modelo_id
        )

        accesorio = Accesorio(
            **accesorio_data.model_dump(),
            sku=sku
        )

        session.add(accesorio)
        session.flush()  # obtenemos accesorio_id sin commit


        lista_stocks = [
            StockAccesorio(
                accesorio_id=accesorio.accesorio_id, #type: ignore
                local_id=local.local_id, #type: ignore
                cantidad=0
            )
            for local in locales
        ]

        session.add_all(lista_stocks)

        session.commit()

        session.refresh(accesorio)
        for stock in lista_stocks:
            session.refresh(stock)

        return {
            "accesorio": accesorio,
            "lista-stocks": lista_stocks
        }

    except ValueError as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    except exc.IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e.orig)
        )

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear accesorio: {str(e)}"
        )
    

@router.get("/{accesorio_id}")
def obtener_accesorio(
    accesorio_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Obtiene accesorio - incluye SKU en respuesta"""
    accesorio = session.get(Accesorio, accesorio_id)
    if not accesorio:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    return accesorio

#actualizacion
@router.patch("/{accesorio_id}")
def actualizar_accesorio(
    accesorio_id: int,
    accesorio_data: AccesorioUpdate,  # ← SIN sku
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """Actualiza accesorio - NO permite cambiar SKU"""
    accesorio = session.get(Accesorio, accesorio_id)
    if not accesorio:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    
    try:
        # Actualizar solo los campos permitidos
        for key, value in accesorio_data.model_dump(exclude_unset=True).items():
            setattr(accesorio, key, value)
        
        # SKU NO cambia
        #update de accesorio
        session.add(accesorio)
        session.commit()
        session.refresh(accesorio)
        
        return accesorio
    
    except exc.IntegrityError as e:
        session.rollback()
        # Mensaje genérico pero útil
        raise HTTPException(
            status_code=400,
            detail=(
                "No se pudo actualizar el accesorio. "
                "Verifique que los campos seleccionados existan."
            )
        )


@router.get("/", response_model=list[Accesorio])
def listar_accesorios(
    skip: int = 0,
    limit: int = 100,
    buscar: Optional[str] = "",
    tipo_id: Optional[int] = None,
    subtipo_id: Optional[int] = None,
    activo: Optional[bool] = True,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Lista accesorios - incluye SKU en respuesta"""
    
    statement = select(Accesorio).offset(skip).limit(limit)

    if not activo:
        statement = statement.where(Accesorio.activo == False)

    if activo:
        statement = statement.where(Accesorio.activo == True)

    if buscar:
        statement = statement.where(
            Accesorio.nombre.ilike(f"%{buscar}%")  # type: ignore
        )

    if tipo_id is not None:
        statement = statement.where(Accesorio.tipo_id == tipo_id)

    if subtipo_id is not None:
        statement = statement.where(Accesorio.subtipo_id == subtipo_id)

    accesorios = session.exec(statement).all()
    return accesorios


@router.delete("/{accesorio_id}")
def eliminar_accesorio(
    accesorio_id: int,
    session: Session = Depends(get_session),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Elimina físicamente un accesorio si nunca tuvo ventas ni movimientos.
    Si tiene ventas o movimientos, lo desactiva.
    """
    try:
        accesorio = session.get(Accesorio, accesorio_id)

        if not accesorio:
            raise HTTPException(status_code=404, detail="Accesorio no encontrado")

        # Verificar ventas asociadas (si tiene ventas => tiene movimientos, medio al pedo)
        tiene_ventas = session.exec(
            select(DetalleVentaAccesorio)
            .where(DetalleVentaAccesorio.accesorio_id == accesorio_id)
        ).first() is not None

    
        # Verificar movimientos de stock
        tiene_movimientos = session.exec(
            select(MovimientoStock)
            .where(MovimientoStock.accesorio_id == accesorio_id)
        ).first() is not None

        if tiene_ventas or tiene_movimientos:
            # Si tiene ventas o movimientos → desactivar
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
            # Borrar primero el stock asociado
            stocks = session.exec(
                select(StockAccesorio)
                .where(StockAccesorio.accesorio_id == accesorio_id) #
            ).all()

            #borra por primary key
            for stock in stocks:
                session.delete(stock)

            # fuerza a ejecutar estos DELETE antes de continuar
            session.flush()

            # Luego borrar el accesorio
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
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar accesorio: {str(e)}"
        )