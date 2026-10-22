"""Combina la configuración privada existente con las conexiones de la VM de datos.

Ejecutar en Ubuntu con sudo python3. Requiere el paquete python3-dotenv.
No imprime secretos, no conecta a servicios y nunca reemplaza el destino.
"""
import argparse
import os
from pathlib import Path
import secrets
import sys
from urllib.parse import urlsplit

from dotenv import dotenv_values


def read_env(path):
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValueError("El origen debe ser un archivo regular, no un enlace.")
    values = dotenv_values(source, encoding="utf-8-sig", interpolate=False)
    if not values or any(value is None for value in values.values()):
        raise ValueError("Hay valores vacíos o líneas sin asignación en el origen.")
    return dict(values)


def combine(database, base=None):
    values = dict(base or {})
    if base is not None:
        for key in ("JWT_SECRET", "FIELD_HMAC_SECRET"):
            if not values.get(key) or values[key].startswith("unsafe-development-"):
                raise ValueError("El entorno de origen no contiene secretos JWT y HMAC válidos.")
    else:
        values.update({
            "JWT_SECRET": secrets.token_hex(32),
            "FIELD_HMAC_SECRET": secrets.token_hex(32),
            "JWT_ALGORITHM": "HS256",
            "ACCESS_TOKEN_MINUTES": "20",
            "REFRESH_TOKEN_DAYS": "7",
            "GUACAMOLE_MODE": "stub",
            "FLAG_INJECTOR_ENABLED": "false",
        })
    for key, scheme, port in (("DATABASE_URL", "postgresql+asyncpg", 5432),
                              ("REDIS_URL", "redis", 6379)):
        value = database.get(key, "")
        parts = urlsplit(value)
        if (parts.scheme != scheme or parts.hostname != "10.10.10.14"
                or parts.port != port or parts.username != "cociber_app"
                or not parts.password):
            raise ValueError("Las conexiones no coinciden con la VM y la cuenta de este despliegue.")
        if key == "DATABASE_URL" and (parts.path != "/cociber_ctf" or parts.query != "ssl=require"):
            raise ValueError("Esta plantilla espera cociber_ctf con ssl=require para la red de laboratorio.")
        if key == "REDIS_URL" and parts.path != "/0":
            raise ValueError("Esta plantilla utiliza la base Redis número 0.")
        values[key] = value
    values.update({
        "MANAGE_SCHEMA_ON_STARTUP": "false",
        "CTF_SEED_DEMO_DATA": "false",
        "PUBLIC_ORIGIN": "http://10.10.10.13",
    })
    # Variables del Compose local que no utiliza el backend.
    for key in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "WEB_PORT"):
        values.pop(key, None)
    return values


def serialize(values):
    lines = ["# Privado. No publicar ni copiar su contenido al chat."]
    for key, value in values.items():
        if not key.replace("_", "").isalnum() or any(c in value for c in "\r\n\x00"):
            raise ValueError("Se encontró una clave o un valor con formato no admitido.")
        # Comillas simples evitan que Compose interprete $ como una variable.
        escaped = value.replace("'", "\\'")
        lines.append(f"{key}='{escaped}'")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--base", help="Entorno privado de la plataforma que se traslada")
    mode.add_argument("--nuevo", action="store_true", help="Solo para una instalación sin datos previos")
    parser.add_argument("--database", required=True, help="application-db.env generado en la VM de datos")
    parser.add_argument("--output", default="/etc/cociber-ctf/web.env")
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists() or target.is_symlink() or not target.parent.is_dir():
        raise ValueError("El destino ya existe o su carpeta no está creada. No se reemplazó nada.")
    data = serialize(combine(read_env(args.database), read_env(args.base) if args.base else None))
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(data)
    print("Configuración creada con permisos 0600; no se imprimieron credenciales.")
    if args.nuevo:
        print("Modo nuevo: Guacamole simulado e inyector desactivado. Falta integrar los laboratorios.")
    else:
        print("JWT, HMAC y configuración de laboratorios conservados; verifica sus direcciones y rutas.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print("No se creó la configuración. " + (str(error) if isinstance(error, ValueError)
              else "Comprueba los archivos y permisos."), file=sys.stderr)
        raise SystemExit(1)
