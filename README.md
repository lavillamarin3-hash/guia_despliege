# Despliegue de Cociber CTF

Guía paso a paso para instalar la plataforma en **Ubuntu Server 26.04**, con el servidor web en **10.10.10.13/24** y PostgreSQL 16 y Redis 7 en la VM **10.10.10.14**.

## Empezar

1. Lee la [guía completa en Markdown](GUIA_DESPLIEGUE_CTF_UBUNTU_26_04.md).
2. También puedes descargar la [versión HTML](GUIA_DESPLIEGUE_CTF_UBUNTU_26_04.html) y abrirla con tu navegador para leer o imprimir.
3. Descarga [las plantillas de despliegue](Plantillas_Despliegue_Web_CTF.zip) desde el botón de descarga del archivo. La guía explica dónde copiarlas y en qué orden utilizarlas.

Si descargas el ZIP desde GitHub, guárdalo en la ruta de Windows indicada en el paso 8 o sustituye esa ruta por la carpeta donde lo descargaste.

## Qué contiene

- `compose.web.yml`: únicamente backend y frontend; conecta a las bases remotas.
- `preparar_entorno.py`: combina la configuración anterior con las conexiones privadas de la VM de datos, conservando los secretos de la aplicación.
- `verificar_servicios.py`: comprueba conexiones y esquema con operaciones de lectura.
- `crear_admin_inicial.py`: crea el primer administrador web solo si no hay usuarios existentes.

Los archivos también se encuentran individualmente en [plantillas_web](plantillas_web/).

El código de la plataforma debe copiarse desde tu carpeta de trabajo según la guía. Este repositorio no contiene la aplicación completa, contraseñas, archivos `.env`, claves SSH ni respaldos de bases.

## Repositorios relacionados

- [Plataforma Cociber CTF](https://github.com/lavillamarin3-hash/ctf-platform)
- [Preparación y migración de PostgreSQL y Redis](https://github.com/lavillamarin3-hash/cociber-ctf-deploy)

## Estado de validación

Preparado el 22 de octubre de 2026. La guía se contrastó con el código y la documentación de despliegue existentes. Se revisó la sintaxis de los auxiliares y la coherencia del procedimiento. La instalación y las pruebas de conexión contra las VM reales deben ejecutarse siguiendo los puntos de comprobación de la guía; no se presentan como pruebas ya realizadas.

