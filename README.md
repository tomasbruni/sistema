# Sistema de Gestión y Ventas — Celular Store

Sistema web full-stack desarrollado de forma independiente para la gestión integral de una tienda de celulares y accesorios. Incluye ventas, inventario, reparaciones, caja diaria y reportes.

---

## Tecnologías

**Backend:** Python · FastAPI · SQLModel · SQLAlchemy 2.0 · PostgreSQL · Alembic · JWT · ReportLab · Pandas 
**Frontend:** React 19 · Vite · React Router 7 
**Deploy:** Render (backend) · Vercel (frontend)

---

## Funcionalidades

- **Ventas** — registro de ventas con múltiples productos por tipo (accesorios, celulares, chips), múltiples métodos de pago (efectivo, débito, crédito, QR, transferencia) y devoluciones
- **Inventario** — stock por sucursal con historial completo de movimientos (entrada, salida, ajuste, venta), transferencias entre locales
- **Celulares** — seguimiento individual por IMEI con estado (disponible, vendido, etc.)
- **Chips** — gestión por número de serie con estado
- **Reparaciones** — flujo completo: presupuesto → aceptado → entregado, con pagos parciales
- **Caja diaria** — cierre de caja por fecha y sucursal
- **Reportes** — exportación a PDF y Excel (ventas, stock, movimientos)
- **Pedidos online** — gestión de órdenes externas (esto todavia no está siendo usado en producción, está hecho para cuando el negocio implemente la venta online)
- **Usuarios y roles** — autenticación JWT, roles admin/usuario con rutas protegidas

---

## Correr localmente

### Backend

```bash
cd backend-app
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:mainapp --reload --port 8000
```

> Requiere PostgreSQL. Configurar credenciales en `backend-app/app/db/session.py`.

### Frontend

```bash
cd frontend-app
npm install
npm run dev   # http://localhost:5173
```
