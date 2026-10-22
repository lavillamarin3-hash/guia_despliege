#!/usr/bin/env python3
"""Comprueba conexiones y esquema sin modificar PostgreSQL ni Redis.

Ejecutar dentro de la imagen API, con DATABASE_URL y REDIS_URL en el entorno.
No importa app.main ni inicia tareas de la plataforma. No imprime secretos.
"""

import asyncio
import os
import sys
from urllib.parse import urlsplit

import redis.asyncio as redis
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base


def revisar_columnas(connection):
    inspector = inspect(connection)
    disponibles = set(inspector.get_table_names(schema="public"))
    faltantes = []
    for tabla in sorted(Base.metadata.tables.values(), key=lambda item: item.name):
        if tabla.name not in disponibles:
            faltantes.append("tabla " + tabla.name)
            continue
        columnas = {item["name"] for item in inspector.get_columns(tabla.name, schema="public")}
        for columna in tabla.columns:
            if columna.name not in columnas:
                faltantes.append("columna " + tabla.name + "." + columna.name)
    return faltantes


async def verificar_postgresql(url):
    engine = None
    try:
        engine = create_async_engine(url, pool_pre_ping=True)
        async with asyncio.timeout(30):
            async with engine.begin() as connection:
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                await connection.execute(text("SELECT 1"))
                cuenta = await connection.scalar(text("SELECT current_user"))
                if cuenta != "cociber_app":
                    print("ERROR PostgreSQL: la cuenta conectada no es cociber_app.")
                    return False
                print("OK PostgreSQL: conexión autenticada y consulta de lectura.")
                cifrado = await connection.scalar(text(
                    "SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
                ))
                if cifrado is not True:
                    print("ERROR PostgreSQL: esta conexión no usa TLS; revise ssl=require.")
                    return False
                print("OK PostgreSQL: la conexión utiliza TLS.")
                faltantes = await connection.run_sync(revisar_columnas)
                if faltantes:
                    print("ERROR Esquema: faltan los siguientes objetos:")
                    for objeto in faltantes:
                        print("  - " + objeto)
                    print("Solicite revisar la migración al administrador de la base.")
                    print("No active MANAGE_SCHEMA_ON_STARTUP ni reinicialice una base con datos.")
                    return False
                print("OK Esquema: presentes las " + str(len(Base.metadata.tables))
                      + " tablas del código y sus columnas.")
                print("Esta comprobación no compara todos los índices, tipos ni restricciones.")
                roles = await connection.scalar(text("SELECT count(*) FROM public.roles"))
                usuarios = await connection.scalar(text("SELECT count(*) FROM public.users"))
                admins = await connection.scalar(text(
                    "SELECT count(*) FROM public.users WHERE role = 'admin' AND is_active IS TRUE"
                ))
                print(f"Datos: {roles} etiquetas de rol; {usuarios} usuarios; {admins} administradores web activos.")
                if usuarios == 0:
                    print("AVISO: la base no tiene usuarios. Siga la sección de administrador inicial.")
                elif admins == 0:
                    print("AVISO: hay usuarios, pero ningún administrador activo; solicite revisar la cuenta existente.")
                print("El usuario PostgreSQL cociber_app no es una cuenta de acceso a la web.")
        return True
    except Exception as error:
        print("ERROR PostgreSQL: " + type(error).__name__ + ". No se muestran credenciales ni detalles privados.")
        return False
    finally:
        if engine is not None:
            await engine.dispose()


async def verificar_redis(url):
    cliente = None
    try:
        destino = urlsplit(url)
        if not destino.username or not destino.password:
            print("ERROR Redis: REDIS_URL debe incluir la cuenta ACL y su contraseña codificada.")
            return False
        cliente = redis.from_url(url, decode_responses=True, socket_connect_timeout=10, socket_timeout=10)
        async with asyncio.timeout(20):
            if await cliente.ping() is not True:
                print("ERROR Redis: PING no devolvió la respuesta esperada.")
                return False
        print("OK Redis: conexión autenticada y PING correcto, sin modificar claves.")
        print("PING no comprueba por sí solo todos los permisos de sesiones y reservas.")
        return True
    except Exception as error:
        print("ERROR Redis: " + type(error).__name__ + ". No se muestran credenciales ni detalles privados.")
        return False
    finally:
        if cliente is not None:
            await cliente.aclose()


async def main():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not database_url or not redis_url:
        print("ERROR: faltan DATABASE_URL o REDIS_URL en el entorno del contenedor.")
        return 2
    resultados = await asyncio.gather(verificar_postgresql(database_url), verificar_redis(redis_url))
    if all(resultados):
        print("COMPROBACIÓN CORRECTA. Continúe con el arranque y las pruebas desde el navegador.")
        return 0
    print("COMPROBACIÓN INCOMPLETA. Corrija los errores antes de abrir la plataforma a estudiantes.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("Comprobación cancelada.")
        sys.exit(130)
    except Exception as error:
        print("ERROR: " + type(error).__name__ + ". No se muestran detalles privados.")
        sys.exit(1)
