import os
from sqlmodel import Session, select
from app.db.session import engine
from app.db.models import Usuario
from app.api.routers.router_auth import hashear_password

def seed_admin():
    nombre = os.environ.get("ADMIN_NOMBRE")
    password = os.environ.get("ADMIN_PASSWORD")

    if not nombre or not password:
        print("ADMIN_NOMBRE y ADMIN_PASSWORD no configuradas, saltando seed.")
        return

    with Session(engine) as session:
        existente = session.exec(
            select(Usuario).where(Usuario.nombre == nombre)
        ).first()

        if existente:
            print(f"Usuario '{nombre}' ya existe, saltando.")
            return

        admin = Usuario(
            nombre=nombre,
            password=hashear_password(password),
            rol="admin",
        )
        session.add(admin)
        session.commit()
        print(f"Usuario admin '{nombre}' creado.")

if __name__ == "__main__":
    seed_admin()
