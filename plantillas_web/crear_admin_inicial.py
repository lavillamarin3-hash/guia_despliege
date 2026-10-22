#!/usr/bin/env python3
"""Crea el primer administrador únicamente cuando la tabla users está vacía.

Requiere un terminal interactivo y el esquema ya preparado. No crea tablas,
no cambia cuentas existentes y no crea usuarios de Guacamole.
"""

import asyncio
from getpass import getpass
import os
import re
import sys

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import hash_password
from app.models import AuditEvent, Role, User


class BootstrapError(Exception):
    """Mensaje seguro, escrito por este programa, sin datos de conexión."""


async def comprobar_vacia(session):
    total = await session.scalar(select(func.count(User.id)))
    if total != 0:
        raise BootstrapError("La tabla users ya contiene usuarios. Use el administrador existente; no se creó ni cambió ninguna cuenta.")
    if await session.scalar(select(Role.id).where(Role.name == "admin")) is None:
        raise BootstrapError("Falta la etiqueta de rol admin. Solicite aplicar la sección de roles de la guía de bases; no se creó ninguna cuenta.")


async def main():
    if not sys.stdin.isatty():
        print("ERROR: ejecute este programa en un terminal interactivo, sin -T ni redirección de entrada.")
        return 2
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("ERROR: falta DATABASE_URL en el entorno del contenedor.")
        return 2
    engine = create_async_engine(url, pool_pre_ping=True)
    sesiones = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sesiones() as session:
            async with session.begin():
                await session.execute(text("SET TRANSACTION READ ONLY"))
                await comprobar_vacia(session)
        print("La base está vacía de usuarios. Se creará una sola cuenta administradora web.")
        print("Este procedimiento no configura una cuenta de PostgreSQL, Redis ni Guacamole.")
        usuario = input("Nombre de usuario web (por ejemplo administrador): ").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,64}", usuario):
            raise BootstrapError("Use entre 3 y 64 letras sin tildes, números, puntos, guiones o guiones bajos.")
        if usuario.lower() in {"cociber_app", "cociberctf", "postgres", "redis"}:
            raise BootstrapError("Elija un nombre distinto de las cuentas de bases de datos.")
        clave = getpass("Contraseña nueva de al menos 16 caracteres (no se verá al escribir): ")
        repetida = getpass("Escriba otra vez la misma contraseña: ")
        if clave != repetida:
            raise BootstrapError("Las contraseñas no coinciden. No se creó ninguna cuenta.")
        if not 16 <= len(clave) <= 256:
            raise BootstrapError("La contraseña debe tener entre 16 y 256 caracteres. No se creó ninguna cuenta.")
        if input("Para crear esta cuenta escriba CREAR y pulse Enter: ").strip() != "CREAR":
            print("Cancelado. No se creó ninguna cuenta.")
            return 0
        clave_hash = hash_password(clave)
        del clave, repetida
        async with sesiones() as session:
            async with session.begin():
                await session.execute(text("SET LOCAL lock_timeout = '5s'"))
                await session.execute(text("LOCK TABLE public.users IN SHARE ROW EXCLUSIVE MODE"))
                await comprobar_vacia(session)
                cuenta = User(username=usuario, password_hash=clave_hash, role="admin", is_active=True)
                session.add(cuenta)
                await session.flush()
                session.add(AuditEvent(
                    actor_id=cuenta.id, action="user.bootstrap_admin", entity_type="user",
                    entity_id=str(cuenta.id), details={"method": "initial_empty_database"},
                ))
        print("OK: administrador inicial creado. Inicie sesión en la web con el nombre y contraseña elegidos.")
        print("Conserve esa contraseña en un gestor de contraseñas.")
        return 0
    except BootstrapError as error:
        print("ERROR: " + str(error))
        return 1
    except Exception as error:
        print("ERROR: " + type(error).__name__ + ". No se muestran contraseñas ni detalles privados.")
        print("Revise la conexión, el esquema y los permisos. No se modifican cuentas existentes.")
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except (KeyboardInterrupt, EOFError):
        print("Creación cancelada.")
        sys.exit(130)
    except Exception as error:
        print("ERROR: " + type(error).__name__ + ". No se muestran detalles privados.")
        sys.exit(1)
