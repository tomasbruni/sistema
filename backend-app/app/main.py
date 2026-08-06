import os
from fastapi import FastAPI, Depends, HTTPException, status
# from api.routers.accesorios import
from typing import Annotated
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.api.routers import (
    router_accesorios,
    router_tipoaccesorios,
    router_subtipoaccesorios,
    router_celulares,
    router_chips,
    router_marcas,
    router_modeloscelulares,
    router_marcascelulares,
    router_stock,
    router_ventas,
    router_locales,
    router_movimientos,
    router_comisiones,
    router_usuarios,
    router_reportes,
    router_auth,
    router_detalles,
    router_ingresos,
    router_egresos_caja,
    router_caja_diaria,
    router_transferencias,
    router_pedidos_online,
    router_gastos,
    router_reparaciones,
    router_sobrantes_faltantes,
    router_ecommerce,
    router_cloudinary)

from app.db.models import *
from app.db.session import get_session, SessionDep
# si quisiera q todas las operaciones de la aplicacion dependan de algun callable
#app = FastAPI(dependencies=[Depends(verify_token), Depends(verify_key)])

from fastapi.middleware.cors import CORSMiddleware

mainapp = FastAPI()
mainapp.include_router(router_accesorios.router)
mainapp.include_router(router_tipoaccesorios.router)
mainapp.include_router(router_subtipoaccesorios.router)
mainapp.include_router(router_celulares.router)
mainapp.include_router(router_chips.router)
mainapp.include_router(router_marcas.router)
mainapp.include_router(router_modeloscelulares.router)
mainapp.include_router(router_marcascelulares.router)
mainapp.include_router(router_stock.router)
mainapp.include_router(router_ventas.router)
mainapp.include_router(router_locales.router)
mainapp.include_router(router_movimientos.router)
mainapp.include_router(router_comisiones.router)
mainapp.include_router(router_usuarios.router)
mainapp.include_router(router_reportes.router)
mainapp.include_router(router_auth.router)
mainapp.include_router(router_detalles.router)
mainapp.include_router(router_ingresos.router)
mainapp.include_router(router_egresos_caja.router)
mainapp.include_router(router_caja_diaria.router)
mainapp.include_router(router_transferencias.router)
#mainapp.include_router(router_pedidos_online.router) por ahora no
mainapp.include_router(router_gastos.router)
mainapp.include_router(router_reparaciones.router)
mainapp.include_router(router_sobrantes_faltantes.router)
mainapp.include_router(router_ecommerce.router)
mainapp.include_router(router_cloudinary.router)

origins = os.environ.get("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500,http://localhost:5173")

mainapp.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
