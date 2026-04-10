from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, SQLModel, select
from sqlalchemy import exc
from typing import Optional

from app.db.session import get_session
from app.db.models import ConfigComision
from app.api.modelscreate import ConfigComisionCreate
from app.api.modelsupdate import ConfigComisionUpdate

from app.api.deps import get_current_user, require_admin

router = APIRouter(
    prefix="/comisiones",
    tags=["COMISIONES"],
    dependencies=[Depends(require_admin)],
)


TIPOS_PRODUCTO_VALIDOS = {"ACCESORIO", "CELULAR", "CHIP", "REPARACION"}
TIPOS_CALCULO_VALIDOS  = {"PORCENTAJE", "FIJO"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _validar_campos(tipo_producto: Optional[str], tipo_calculo: Optional[str], valor: Optional[int]):
    if tipo_producto and tipo_producto not in TIPOS_PRODUCTO_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"tipo_producto inválido. Debe ser uno de: {TIPOS_PRODUCTO_VALIDOS}",
        )
    if tipo_calculo and tipo_calculo not in TIPOS_CALCULO_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"tipo_calculo inválido. Debe ser uno de: {TIPOS_CALCULO_VALIDOS}",
        )
    if valor is not None and valor < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El valor de comisión no puede ser negativo.",
        )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ConfigComision])
def listar_comisiones(
    session: Session = Depends(get_session),
):
    """Lista todas las configuraciones de comisión."""
    return session.exec(select(ConfigComision)).all()


@router.get("/{config_comision_id}", response_model=ConfigComision)
def obtener_comision(
    config_comision_id: int,
    session: Session = Depends(get_session),
):
    """Obtiene una configuración de comisión por ID."""
    config = session.get(ConfigComision, config_comision_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comisión con ID {config_comision_id} no encontrada.",
        )
    return config


@router.post("/", response_model=ConfigComision, status_code=status.HTTP_201_CREATED)
def crear_comision(
    data: ConfigComisionCreate,
    session: Session = Depends(get_session),
):
    """Crea una nueva configuración de comisión."""
    _validar_campos(data.tipo_producto, data.tipo_calculo, data.valor)
    try:
        config = ConfigComision(
            tipo_producto=data.tipo_producto,
            tipo_calculo=data.tipo_calculo,
            valor=data.valor,
        )
        session.add(config)
        session.commit()
        session.refresh(config)
        return config
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una comisión para el tipo de producto '{data.tipo_producto}'.",
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}",
        )


@router.put("/{config_comision_id}", response_model=ConfigComision)
def actualizar_comision(
    config_comision_id: int,
    data: ConfigComisionUpdate,
    session: Session = Depends(get_session),
):
    """Actualiza una configuración de comisión existente."""
    config = session.get(ConfigComision, config_comision_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comisión con ID {config_comision_id} no encontrada.",
        )

    _validar_campos(None, data.tipo_calculo, data.valor)

    try:
        if data.tipo_calculo is not None:
            config.tipo_calculo = data.tipo_calculo
        if data.valor is not None:
            config.valor = data.valor

        session.add(config)
        session.commit()
        session.refresh(config)
        return config
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}",
        )


@router.delete("/{config_comision_id}")
def eliminar_comision(
    config_comision_id: int,
    session: Session = Depends(get_session),
):
    """Elimina una configuración de comisión."""
    config = session.get(ConfigComision, config_comision_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comisión con ID {config_comision_id} no encontrada.",
        )
    try:
        session.delete(config)
        session.commit()
        return {"detail": f"Comisión para '{config.tipo_producto}' eliminada correctamente."}
    except exc.IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la comisión está referenciada en ventas existentes.",
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}",
        )