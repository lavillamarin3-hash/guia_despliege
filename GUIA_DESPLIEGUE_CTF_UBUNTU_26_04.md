# Guía paso a paso para desplegar Cociber CTF en Ubuntu Server 26 04

**Servidor web:** `10.10.10.13/24` · **Servidor de datos:** `10.10.10.14/24`  
**Preparada el 22 de octubre de 2026** a partir del código local y los chats del proyecto.

Esta guía lleva la plataforma de tu carpeta de Windows a la máquina virtual del servidor web. Al terminar podrás abrir **http://10.10.10.13** desde un equipo con acceso a esa red. El backend y el frontend se ejecutarán en el servidor web; PostgreSQL y Redis seguirán en la VM de datos existente.

Se entrega un procedimiento para ejecutar. **No se ha realizado una conexión ni una instalación en tus VM durante la preparación de esta guía.** Cada comprobación indica qué debes observar antes de continuar.

## 1 Cómo leer esta guía

Hay tres equipos. Antes de copiar un comando, mira dónde se ejecuta:

| Nombre que usaremos | Equipo | Para qué sirve |
|---|---|---|
| WINDOWS | Tu computadora HP | Tiene la carpeta actual del proyecto y esta guía |
| WEB | Ubuntu Server 26.04 en `10.10.10.13` | Ejecutará la plataforma |
| DATOS | La VM existente en `10.10.10.14` | Ya aloja o debe terminar de preparar PostgreSQL y Redis |

Una **terminal** es la ventana donde escribes órdenes. En Windows abre el menú Inicio, escribe **PowerShell** y ábrelo. En Ubuntu puedes usar la consola de la VM o entrar desde Windows mediante SSH, que permite manejar el servidor a distancia.

- Copia cada bloque de comandos completo, pégalo y pulsa **Enter**. Espera a que vuelva a aparecer la línea donde puedes escribir.
- No copies los símbolos de las cercas de código ni los nombres `bash` o `powershell`.
- Si aparece una contraseña, escríbela y pulsa Enter. En Linux **no aparecen puntos ni asteriscos** mientras escribes: es normal.
- `sudo` pide ejecutar una orden como administrador. La contraseña es la del usuario de Ubuntu, no la contraseña de PostgreSQL.
- `cd` entra a una carpeta; `ls` muestra su contenido.
- Para salir de una vista de registros que se actualiza, pulsa **Ctrl+C**. Para salir de `less`, pulsa **q**.
- Si un paso muestra un error, resuélvelo antes de continuar. No repitas todos los pasos desde el principio.

**Cómo editar con nano:** abre el archivo con el comando indicado; usa las flechas; pega o modifica el texto. Guarda con **Ctrl+O**, confirma con **Enter** y sal con **Ctrl+X**. En YAML usa espacios, no la tecla Tab.

Los textos `TU_USUARIO_WEB`, `TU_USUARIO_DATOS`, `INTERFAZ_REAL`, `PUERTA_DE_ENLACE_REAL` y `DNS_REAL` son marcadores. Debes reemplazarlos. No son cuentas ni direcciones que ya existan.

## 2 Qué se instalará y qué está confirmado

```text
Navegador del estudiante
        |
        | HTTP puerto 80
        v
WEB 10.10.10.13 Ubuntu Server 26.04
  Docker
    web  Nginx sirve el frontend React ya compilado
      |
      | /api/ y WebSocket
      v
    api  FastAPI con Python 3.12 y Uvicorn
      |                              |
      | PostgreSQL TLS puerto 5432   | Redis puerto 6379
      v                              v
DATOS 10.10.10.14
  PostgreSQL 16                      Redis 7
  base cociber_ctf                   base lógica 0
  cuenta cociber_app                 cuenta cociber_app
```

**Docker** ejecuta cada parte de la aplicación en un entorno preparado llamado contenedor. No necesitas instalar manualmente todas las bibliotecas en Ubuntu: los Dockerfile del proyecto las instalan al construir las imágenes.

| Parte | Dependencias reales del proyecto | Cómo se instalan |
|---|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn, SQLAlchemy, asyncpg, pydantic-settings, PyJWT, Argon2, Redis, multipart, email-validator, Paramiko, cryptography y websockets | `backend/Dockerfile` instala `backend/requirements.txt` |
| Frontend | Node.js 22 para compilar; React 18, Vite 5, TypeScript 5, Tailwind, PostCSS y Autoprefixer | `frontend/Dockerfile` ejecuta `npm ci` y `npm run build` |
| Servidor HTTP | Nginx, actualmente imagen `nginx:1.27-alpine` del proyecto | Etapa final del Dockerfile del frontend |
| Ubuntu | Docker Engine, complemento Compose, SSH, herramientas de red y Python para el asistente de configuración | Se instalan en los pasos siguientes |

Se conserva Python 3.12 porque es la versión del proyecto. El Python predeterminado de Ubuntu 26.04 es 3.14; no lo vamos a sustituir. Docker admite Ubuntu 26.04. Referencias: [Ubuntu 26.04](https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/) y [Docker en Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

El archivo Compose original crea **cuatro servicios**, incluidas bases locales. Esta guía entrega un archivo **independiente**, `compose.web.yml`, que crea únicamente `api` y `web`. Por eso todos los comandos del servidor nuevo incluyen `-f compose.web.yml`.

### Información recuperada del proyecto

- Carpeta activa: `C:\Users\HP\Documents\Codex\Proyecto_CTF_Fase5_Laboratorio_Ranking_Top10\ctf_project`.
- El código se descarga desde `ctf-platform` en GitHub. Los cambios que permanezcan únicamente en Windows deben publicarse primero mediante `git push`.
- Las guías actuales de bases están en `C:\Users\HP\Documents\Codex\cociber-ctf-deploy`.
- La cuenta `cociberctf` es administrativa. La plataforma se conecta con **`cociber_app`**, que tiene permisos de ejecución.
- `cociber_app` y su contraseña **no son un usuario y contraseña para entrar a la página web**.
- El esquema actual tiene 19 tablas. La guía existente de bases coincide con los modelos actuales inspeccionados.
- Operación Cóndor en `10.10.30.20` es otra aplicación. No se instala en el servidor principal mediante esta guía.

## 3 Lo que debes tener antes de comenzar

Anota o confirma estos datos con quien administra la red:

| Dato | Valor o acción |
|---|---|
| IP del servidor web | `10.10.10.13/24`; equivale a máscara `255.255.255.0` |
| IP de bases | `10.10.10.14` |
| Usuario de Ubuntu WEB | El creado al instalar Ubuntu; debe poder usar `sudo` |
| Usuario de Ubuntu DATOS | Cuenta para entrar a la VM de bases mediante SSH |
| Puerta de enlace | Confirmar; **no se deduce** que sea `10.10.10.1` |
| DNS | Confirmar los servidores DNS de tu red |
| Red de la VM | La tarjeta debe conectarse a la red/VLAN que contiene `10.10.10.0/24` |
| Acceso a Internet de WEB | Necesario para descargar paquetes e imágenes durante la instalación |
| Archivo privado de bases | `application-db.env`, generado con la guía de bases |
| Configuración anterior | `.env` de la plataforma actual, para conservar sus secretos e integraciones |

Como punto inicial para el servidor web puedes asignar **4 vCPU, 8 GB de RAM y 40 GB de disco**, ajustándolo después según el uso. Es una propuesta para comenzar, no una capacidad probada para un número determinado de alumnos.

Esta guía comienza con Ubuntu Server instalado. Si la VM ya tiene servicios, no reinstales ni formatees discos. Si es nueva, instala Ubuntu Server 26.04 desde la ISO oficial, crea un usuario administrativo y activa **OpenSSH server** durante el instalador. La VM de DATOS se conserva.

**Antes del cambio definitivo**, cierra las sesiones de laboratorio, conserva un respaldo de PostgreSQL y guarda la configuración privada anterior. No deben quedar dos API ejecutando tareas de limpieza sobre la misma base durante el cambio.

## 4 Confirmar y configurar la dirección del servidor WEB

**Dónde: consola de la VM WEB.** Para cambiar la red es preferible la consola del hipervisor, porque no depende de SSH.

```bash
cat /etc/os-release
hostname
ip -br address
ip route
resolvectl status
```

Debe aparecer Ubuntu 26.04. Identifica la tarjeta de red: puede llamarse `ens18`, `ens160` o `enp1s0`. **No cambies su nombre por adivinación.** Si ya ves `10.10.10.13/24` en la tarjeta correcta y tienes conectividad, no vuelvas a configurar la IP.

Si todavía falta la dirección fija:

```bash
sudo cp -a /etc/netplan /root/netplan-respaldo-ctf
ls -l /etc/netplan
sudo netplan get
```

La copia guarda la configuración anterior. Abre con nano el archivo YAML existente que contiene tu tarjeta. Por ejemplo, **solo si ese es su nombre**:

```bash
sudo nano /etc/netplan/50-cloud-init.yaml
```

Modifica la sección de esa tarjeta. No borres otras interfaces. Para una VM con **una sola tarjeta**, la estructura sería esta; reemplaza los tres marcadores antes de guardar:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    INTERFAZ_REAL:
      dhcp4: false
      addresses:
        - 10.10.10.13/24
      routes:
        - to: default
          via: PUERTA_DE_ENLACE_REAL
      nameservers:
        addresses:
          - DNS_REAL
```

Si tienes **dos tarjetas**, una para Internet y otra para el laboratorio, normalmente debes conservar la ruta por defecto y el DNS en la tarjeta de Internet. La tarjeta del laboratorio puede llevar solamente `dhcp4: false` y `addresses: [10.10.10.13/24]`. No agregues una segunda ruta por defecto sin revisar la topología.

Si el archivo advierte que lo genera `cloud-init`, confirma con el administrador del hipervisor cuál es la configuración de red persistente de esa VM antes de dar por terminado el cambio.

Aplica permisos al archivo que editaste y verifica la sintaxis; reemplaza el nombre si era diferente:

```bash
sudo chmod 600 /etc/netplan/50-cloud-init.yaml
sudo netplan generate
sudo netplan try --timeout 120
```

Si `generate` muestra error, corrige el YAML y no continúes. Durante `try`, comprueba desde otra consola que tienes acceso y confirma con Enter. Si pierdes acceso, espera el plazo y revisa la reversión desde la consola. Comprueba el archivo en disco antes de reiniciar: Netplan advierte que hay situaciones en las que la reversión debe verificarse. [Referencia Netplan](https://netplan.readthedocs.io/en/stable/netplan-try/).

```bash
ip -br address
ip route get 10.10.10.14
ping -c 3 10.10.10.14
getent hosts download.docker.com
```

**Resultado esperado:** dirección `.13/24`, ruta hacia `.14` con origen `.13`, y resolución del nombre de Docker. Un ping puede estar bloqueado; las pruebas de puertos del paso 6 son más concluyentes.

## 5 Entrar por SSH y preparar Ubuntu

**Dónde: WEB, inicialmente por consola.**

```bash
sudo apt update
sudo apt install -y openssh-server ca-certificates curl nano tar unzip netcat-openbsd python3 python3-dotenv
sudo systemctl enable --now ssh
sudo systemctl status ssh --no-pager
```

**Dónde: WINDOWS, PowerShell.** Sustituye `TU_USUARIO_WEB` por tu cuenta de Ubuntu:

```powershell
ssh TU_USUARIO_WEB@10.10.10.13
```

En la primera conexión verifica que estás entrando a la VM correcta y acepta su huella SSH. Después escribe la contraseña de Ubuntu. A partir de ahora esa ventana opera en **WEB**, aunque la hayas abierto desde Windows. Puedes abrir otra pestaña de PowerShell para ejecutar pasos de WINDOWS.

En WEB:

```bash
sudo apt upgrade -y
timedatectl
df -h /
free -h
```

Comprueba que la hora sea correcta: los tokens de sesión dependen de ella. Si Ubuntu indica que debes reiniciar, ejecuta `sudo reboot`, espera a que vuelva a iniciar y entra de nuevo por SSH. Hazlo durante la preparación, antes de dar servicio a estudiantes.

## 6 Comprobar que la VM de DATOS está preparada

**Dónde: WEB.**

```bash
nc -vz -w 5 10.10.10.14 5432
nc -vz -w 5 10.10.10.14 6379
```

Ambos deben indicar conexión exitosa, normalmente `succeeded`. Esta prueba solo comprueba el puerto; más adelante verificaremos autenticación y tablas.

Si falla, revisa **en DATOS**, no en WEB:

```bash
sudo pg_lsclusters
sudo systemctl status postgresql@16-main --no-pager
sudo systemctl status cociber-redis --no-pager
sudo ss -lntp
sudo ufw status verbose
```

`cociber-redis` es el nombre utilizado por tus guías actuales. Si se instaló Redis mediante el paquete de Ubuntu, su servicio puede llamarse `redis-server`. No instales un segundo Redis para corregir un nombre de servicio.

Si el firewall de DATOS está activo y falta el permiso de WEB, estas son las reglas acotadas a la aplicación:

```bash
sudo ufw allow from 10.10.10.13 to 10.10.10.14 port 5432 proto tcp comment 'Cociber WEB PostgreSQL'
sudo ufw allow from 10.10.10.13 to 10.10.10.14 port 6379 proto tcp comment 'Cociber WEB Redis'
```

Además, PostgreSQL debe escuchar en `.14`, tener TLS habilitado y permitir a `cociber_app` desde `.13/32` mediante `pg_hba.conf`; Redis debe escuchar en `.14` y tener creada su cuenta ACL `cociber_app`. Las reglas del firewall por sí solas no crean esas cuentas ni habilitan los motores.

**Comprueba el destino antes de conectar la plataforma. En DATOS:**

```bash
sudo -u postgres psql -X -d cociber_ctf -c "SELECT count(*) AS tablas FROM pg_tables WHERE schemaname='public';"
sudo -u postgres psql -X -d cociber_ctf -c "SELECT rolname, rolsuper FROM pg_roles WHERE rolname IN ('cociberctf','cociber_app');"
sudo -u postgres psql -X -d cociber_ctf -c "SELECT count(*) AS usuarios FROM users;"
```

Se esperan 19 tablas para esta versión, `cociber_app` sin superusuario y tus usuarios si restauraste la base anterior. Si `users` no existe o la base está vacía cuando esperabas datos, termina primero la [guía de aplicación y migración de bases](https://github.com/lavillamarin3-hash/cociber-ctf-deploy/blob/main/docs/05_APLICACION_Y_MIGRACION.md).

**No importes nuevamente el esquema sobre una base con datos.** Esta guía mantiene `MANAGE_SCHEMA_ON_STARTUP=false`, por lo que arrancar el backend no creará ni actualizará tablas.

## 7 Instalar Docker en WEB

**Dónde: WEB.** Primero mira si ya existe:

```bash
sudo docker version
sudo docker compose version
```

Si ambos funcionan y ya instalaste Docker desde el repositorio oficial, conserva esa instalación. Si indica `command not found` y el servidor es nuevo, sigue estos bloques. Si hay contenedores o una instalación de otra procedencia, revisa su estado antes de reemplazar paquetes.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

```bash
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

**Resultado esperado:** `Hello from Docker!` y una versión de Compose. Usa `sudo docker` en toda la guía. No es necesario añadir tu cuenta al grupo Docker.

La sintaxis oficial puede actualizarse; se verificó para Ubuntu 26.04 en [Docker Engine para Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

## 8 Descargar el código de la plataforma desde GitHub

En lugar de copiar el proyecto desde Windows, descarga **backend** y **frontend** directamente de la rama `main` de [ctf-platform](https://github.com/lavillamarin3-hash/ctf-platform). Solo se incluyen los cambios publicados en GitHub mediante `git push`; los cambios que permanezcan únicamente en tu equipo local no aparecerán aquí.

**Dónde: WEB, en la sesión SSH de Ubuntu.** Instala Git:

```bash
sudo apt update
sudo apt install -y git
git --version
```

**En un despliegue nuevo**, asegúrate de que `/opt/ctf` no contenga una instalación previa:

```bash
ls -ld /opt/ctf 2>/dev/null || true
```

Si la carpeta no existe o está vacía, descarga el proyecto:

```bash
sudo install -d -m 0755 -o "$USER" -g "$(id -gn)" /opt/ctf
git clone --branch main --single-branch https://github.com/lavillamarin3-hash/ctf-platform.git /opt/ctf
cd /opt/ctf
```

Si `/opt/ctf` ya tiene una aplicación instalada, **no** sobrescribas ni borres nada. Utiliza el procedimiento de actualización del paso 17, después de respaldar datos y configuración.

Valida el repositorio y registra el commit exacto desplegado:

```bash
cd /opt/ctf
git remote -v
git branch --show-current
git rev-parse HEAD
test -f backend/Dockerfile && test -f frontend/Dockerfile && echo 'Código descargado correctamente'
git status --short
```

El remoto debe apuntar a `https://github.com/lavillamarin3-hash/ctf-platform.git` y la rama debe ser `main`. **No uses `docker compose up` con `docker-compose.yml` del proyecto**, porque ese archivo inicia también PostgreSQL y Redis locales. Esta guía utiliza `compose.web.yml` para enlazar con la VM de DATOS.

### Descargar las plantillas para el despliegue separado

Las plantillas auxiliares no forman parte del código de `ctf-platform`; se obtienen del repositorio [guia_despliege](https://github.com/lavillamarin3-hash/guia_despliege). **Dónde: WEB.**

```bash
cd /opt/ctf
mkdir -p deploy
for archivo in compose.web.yml preparar_entorno.py verificar_servicios.py crear_admin_inicial.py; do
  curl -fsSL "https://raw.githubusercontent.com/lavillamarin3-hash/guia_despliege/main/plantillas_web/$archivo" -o "deploy/$archivo" || exit 1
done
sudo install -m 0644 deploy/compose.web.yml /opt/ctf/compose.web.yml
ls -l deploy/ compose.web.yml
```

Debes ver los cuatro archivos auxiliares y `compose.web.yml` en la raíz. El archivo original `docker-compose.yml` permanece intacto; no lo ejecutes en el servidor WEB. Si Git marcara archivos auxiliares como no rastreados, no los elimines.

### Conservar la configuración privada de una instalación anterior (opcional)

Para migrar tu plataforma existente, necesitarás además el `.env` anterior, **que no está en GitHub**. **Dónde: WINDOWS, PowerShell fuera de SSH.** Sustituye `TU_USUARIO_WEB`:

```powershell
scp 'C:\Users\HP\Documents\Codex\Proyecto_CTF_Fase5_Laboratorio_Ranking_Top10\ctf_project\.env' TU_USUARIO_WEB@10.10.10.13:~/ctf-original.env
```

**Dónde: WEB.** Protege el archivo para el paso 10:

```bash
chmod 600 ~/ctf-original.env
```

Si es una instalación nueva, omite esa copia y utiliza la opción B del paso 10. Nunca publiques credenciales, claves privadas, respaldos ni archivos `.env` en GitHub.

## 9 Obtener el archivo privado de conexión a las bases

**Dónde: DATOS.** Entra a su consola o por SSH. Estos comandos se basan en el repositorio de despliegue ya preparado:

```bash
cd /opt/cociber-ctf-deploy
sudo test -f /etc/cociber-ctf/application-db.env && echo 'El archivo de conexión ya existe'
```

Si el archivo ya existe, úsalo. Si **no existe**, créalo:

```bash
sudo python3 tools/write_application_env.py --secrets-file /etc/cociber-ctf/deploy-secrets.env --output /etc/cociber-ctf/application-db.env
```

Este programa utiliza las contraseñas de ejecución configuradas en la VM de datos y codifica sus caracteres especiales. No cambia contraseñas ni crea usuarios. Si faltan `PG_APP_PASSWORD` o `REDIS_APP_PASSWORD`, termina el aprovisionamiento de las cuentas `cociber_app` con la guía de bases. No sustituyas esas cuentas por el superusuario.

Deja una copia temporal privada para transferir por SSH. Ejecuta desde tu usuario normal de Ubuntu DATOS, sin entrar primero a una consola `sudo -i`:

```bash
sudo install -m 0600 -o "$USER" -g "$(id -gn)" /etc/cociber-ctf/application-db.env "$HOME/application-db.env"
```

**Dónde: WEB.** Reemplaza `TU_USUARIO_DATOS`:

```bash
scp TU_USUARIO_DATOS@10.10.10.14:~/application-db.env ~/application-db.env
chmod 600 ~/application-db.env
```

Si el firewall de DATOS no permite SSH desde WEB, transfiere ese archivo desde tu equipo administrativo usando `scp` en dos pasos, sin abrir el puerto a toda la red.

El archivo debe contener las conexiones a `10.10.10.14`, base `cociber_ctf`, cuenta `cociber_app`, PostgreSQL con `ssl=require` y Redis base `0`. No hay que escribir las contraseñas a mano ni mostrarlas en pantalla.

## 10 Crear la configuración privada de la plataforma

**Dónde: WEB.**

```bash
sudo install -d -m 0700 /etc/cociber-ctf
```

Elige **solo una** de estas dos opciones.

### Opción A Conservar usuarios retos y configuración anteriores

Es la opción adecuada para trasladar tu plataforma actual. La VM de datos debe contener la base restaurada o preparada con tus datos.

```bash
sudo python3 /opt/ctf/deploy/preparar_entorno.py --base "$HOME/ctf-original.env" --database "$HOME/application-db.env" --output /etc/cociber-ctf/web.env
```

El asistente conserva `JWT_SECRET`, `FIELD_HMAC_SECRET` y la configuración de Guacamole/SSH; reemplaza las conexiones de datos y configura `PUBLIC_ORIGIN=http://10.10.10.13`. Esto evita perder los secretos de la instalación anterior.

### Opción B Instalación completamente nueva

Úsala únicamente si no estás conservando usuarios, retos, puntuaciones ni secretos previos. Deben existir las 19 tablas vacías y los roles en DATOS:

```bash
sudo python3 /opt/ctf/deploy/preparar_entorno.py --nuevo --database "$HOME/application-db.env" --output /etc/cociber-ctf/web.env
```

Genera secretos nuevos, deja Guacamole en modo simulado y el inyector desactivado. Permite preparar el portal; **todavía no habilita laboratorios reales**. El administrador web inicial se crea en el paso 13.

### Comprobar el resultado

```bash
sudo stat -c '%a %U %n' /etc/cociber-ctf/web.env
```

Debe mostrar `600 root` y la ruta. No uses `cat` para publicar su contenido. El asistente se niega a reemplazar un archivo que ya exista. Para corregirlo, conserva una copia privada y edita el archivo con:

```bash
sudo cp -a /etc/cociber-ctf/web.env /etc/cociber-ctf/web.env.respaldo
sudo nano /etc/cociber-ctf/web.env
```

Los valores `MANAGE_SCHEMA_ON_STARTUP='false'` y `CTF_SEED_DEMO_DATA='false'` deben permanecer así. El backend no debe modificar automáticamente el esquema ni introducir datos de demostración.

PostgreSQL utiliza TLS con `ssl=require`: cifra el transporte, pero no verifica la identidad del servidor. Redis usa autenticación en la red privada. Esta configuración corresponde al laboratorio restringido documentado. Si se usa una red no confiable, configura CA y verificación completa para PostgreSQL y TLS en Redis antes de usarla; el asistente suministrado está limitado deliberadamente a la configuración de laboratorio existente.

## 11 Revisar Guacamole y las rutas hacia los laboratorios

Si conservaste el entorno anterior, revisa sus direcciones con `sudo nano /etc/cociber-ctf/web.env`. La configuración inspeccionada todavía contiene referencias a la antigua red `192.168.146.0/24`. Que la web cambie a `.13` **no cambia automáticamente** la dirección de Guacamole, de Kali ni de las víctimas.

| Elemento | Qué verificar |
|---|---|
| `GUACAMOLE_MODE` | `real` para tu integración existente; `stub` solo simula |
| `GUACAMOLE_BASE_URL` y `GUACAMOLE_API_URL` si existe | Dirección real alcanzable desde WEB; no escribir `localhost` para una VM distinta |
| Cuenta de servicio Guacamole | Conservar credenciales válidas, privadas |
| `FLAG_INJECTOR_ENABLED` | Activar solo con la infraestructura SSH del laboratorio ya preparada |
| Inventario de VM en la plataforma | Actualizar las IP y conexiones de Guacamole desde Administración si cambió la topología |
| Red | WEB debe llegar a DATOS, a Guacamole y a los servicios autorizados de las VM |

No cambies las IP antiguas por direcciones inventadas. La IP nueva de Guacamole y de Kali no queda confirmada por el dato `10.10.10.13`.

Si se utilizan claves SSH en archivos, estos deben existir **dentro del contenedor**. Las rutas de Windows no sirven en Linux. Crea un directorio privado en WEB, copia únicamente la clave del servicio y su archivo `known_hosts` verificado, y aplica:

```bash
sudo install -d -m 0700 /etc/cociber-ctf/ssh
```

Después de colocar los archivos con nombres `id_ed25519` y `known_hosts`:

```bash
sudo chown -R 10001:10001 /etc/cociber-ctf/ssh
sudo chmod 700 /etc/cociber-ctf/ssh
sudo chmod 600 /etc/cociber-ctf/ssh/id_ed25519 /etc/cociber-ctf/ssh/known_hosts
sudo nano /opt/ctf/compose.web.yml
```

Añade **dentro de `volumes` del servicio `api`**, conservando las otras líneas:

```yaml
      - /etc/cociber-ctf/ssh:/run/ctf-ssh:ro
```

Y configura estas rutas en `web.env`:

```dotenv
FLAG_INJECTOR_SSH_PRIVATE_KEY='/run/ctf-ssh/id_ed25519'
FLAG_INJECTOR_KNOWN_HOSTS='/run/ctf-ssh/known_hosts'
FLAG_INJECTOR_STRICT_HOST_KEY='true'
```

El UID `10001` es el usuario del backend en su Dockerfile. La huella del servidor SSH debe confirmarse por un canal administrativo antes de incorporarla a `known_hosts`. Si tu instalación usa contraseña SSH, no crees una clave vacía ni añadas ese montaje: conserva el método real y sus credenciales privadas.

La plataforma puede abrir aunque la terminal no funcione. La aceptación del laboratorio se comprueba por separado en el paso 15.

## 12 Construir backend y frontend

**Dónde: WEB.**

```bash
cd /opt/ctf
sudo docker compose -f compose.web.yml config --quiet
sudo docker compose -f compose.web.yml config --services
```

La primera orden termina sin texto si la configuración es válida. La segunda debe mostrar únicamente:

```text
api
web
```

Si aparecen `postgres` o `redis`, estás usando el archivo incorrecto. No continúes. Evita ejecutar `docker compose config` sin `--quiet`: puede mostrar secretos resueltos.

Ahora construye las imágenes:

```bash
sudo docker compose -f compose.web.yml build
```

Puede tardar varios minutos. Durante el proceso se descargan Python 3.12, Node 22 y Nginx, se instalan las dependencias y se compila React. Espera a que termine sin errores. No cierres la terminal mientras construye.

Comprueba las herramientas instaladas en la imagen del backend:

```bash
sudo docker compose -f compose.web.yml run --rm --no-deps api python --version
sudo docker compose -f compose.web.yml run --rm --no-deps api python -m pip check
```

Debes ver Python `3.12.x` y ninguna dependencia rota. Node es una herramienta de construcción y no necesita permanecer en el contenedor final de Nginx. La configuración Nginx se verifica después de iniciar la API, para que pueda resolver el nombre interno `api`.

## 13 Probar las bases y preparar el acceso inicial

**Dónde: WEB.** Aún no es necesario iniciar permanentemente la API:

```bash
cd /opt/ctf
sudo docker compose -f compose.web.yml run --rm --no-deps api python /opt/ctf-deploy/verificar_servicios.py
```

La prueba suministrada realiza consultas de lectura. Comprueba PostgreSQL, TLS, la cuenta de ejecución, las tablas y columnas esperadas y un `PING` autenticado a Redis. También informa cuántos usuarios y administradores existen. No imprime contraseñas ni URLs privadas.

**Debes obtener conexiones correctas y ningún faltante de esquema.** Tener el puerto abierto no basta. Si hay tablas o columnas faltantes, vuelve a la guía de bases y resuelve la migración con el administrador. No cambies `MANAGE_SCHEMA_ON_STARTUP` para saltarte el problema.

Si restauraste una instalación, entra después con su usuario web administrador existente. Si el verificador muestra cero usuarios y elegiste la instalación nueva, crea el administrador inicial:

```bash
sudo docker compose -f compose.web.yml run --rm --no-deps api python /opt/ctf-deploy/crear_admin_inicial.py
```

No añadas `-T`: este asistente necesita una terminal interactiva. Te pedirá un nombre de usuario y una contraseña de al menos 16 caracteres, que debes confirmar. Escribe `CREAR` cuando quieras guardarlo.

El asistente solo admite una base sin usuarios y con el rol `admin` ya creado. Si encuentra usuarios, se detiene para no duplicar ni modificar cuentas. Crea un usuario de la **plataforma**, no una cuenta de Ubuntu ni de PostgreSQL. No crea automáticamente su cuenta en Guacamole.

Si había usuarios pero ya no tienes acceso administrativo, no borres `users` ni ejecutes el asistente a la fuerza: recupera la cuenta con el responsable de la plataforma.

## 14 Iniciar la plataforma

Antes de este paso, cierra los laboratorios activos en la instalación anterior. Si la API anterior apunta a la misma base, detenla antes de arrancar la nueva. **Dónde: WINDOWS, solo si esa es tu instalación anterior administrada con Compose:**

```powershell
Set-Location 'C:\Users\HP\Documents\Codex\Proyecto_CTF_Fase5_Laboratorio_Ranking_Top10\ctf_project'
docker compose stop api web
```

Esto conserva los contenedores y datos anteriores para poder volver atrás. No uses `down -v`.

**Dónde: WEB.**

```bash
cd /opt/ctf
sudo docker compose -f compose.web.yml up -d
sudo docker compose -f compose.web.yml ps
sudo docker compose -f compose.web.yml logs --tail=80 api web
sudo docker compose -f compose.web.yml exec web nginx -t
```

`-d` significa que los servicios siguen funcionando aunque cierres SSH. Se espera `api` saludable, `web` iniciado y Nginx indicando `syntax is ok` / `test is successful`. El archivo incluye `restart: unless-stopped`, y Docker quedó habilitado para arrancar con Ubuntu.

El puerto `8000` solo existe dentro de la red Docker; no se publica. Nginx recibe peticiones en `10.10.10.13:80` y las reenvía al servicio llamado `api`. No uses `npm run dev` ni Uvicorn con `--reload` para este despliegue.

## 15 Comprobar la plataforma desde el navegador

**Dónde: WEB.**

```bash
curl -I http://10.10.10.13/
curl --fail http://10.10.10.13/api/v1/health
```

La portada debe responder `200 OK` y la API:

```json
{"status":"ok","service":"ctf-api"}
```

**Ese endpoint solo verifica que la API responde.** La prueba del paso 13 verifica las bases; ambas comprobaciones son necesarias.

**Dónde: WINDOWS o un equipo autorizado de estudiantes.** Abre Edge, Chrome o Firefox y escribe exactamente:

```text
http://10.10.10.13
```

No agregues `/24`. No uses `localhost`: eso apuntaría al equipo desde el que navegas.

Comprueba en este orden:

1. Aparece la pantalla de inicio de sesión.
2. Entras con un usuario web real. Las credenciales de bases no sirven aquí.
3. Como administrador ves usuarios, grupos, retos y ranking esperados.
4. Como estudiante ves solamente los retos asignados a tu grupo.
5. Al recargar una página interna, la aplicación sigue abriendo.
6. El ranking se actualiza sin errores de WebSocket.
7. En un reto ya preparado, inicia la sesión, abre la terminal integrada y verifica que funciona.
8. Completa la prueba de validación del reto, cierra la sesión y comprueba la liberación del recurso y su limpieza según el procedimiento del laboratorio.

Los puntos 7 y 8 requieren Guacamole y las VM de laboratorio operativas. Si solo aprueban los puntos 1 a 6, puedes registrar **portal funcionando; integración de laboratorios pendiente**. No presentes la instalación completa como aceptada todavía.

Si migraste datos, compara con el origen los usuarios, retos publicados y puntos. En DATOS:

```bash
sudo -u postgres psql -X -d cociber_ctf -c "SELECT count(*) AS usuarios FROM users;"
sudo -u postgres psql -X -d cociber_ctf -c "SELECT count(*) AS retos_publicados FROM challenges WHERE is_published;"
sudo -u postgres psql -X -d cociber_ctf -c "SELECT count(*) AS completados, coalesce(sum(awarded_points),0) AS puntos FROM challenge_completions;"
```

Finalmente, en una ventana sin alumnos conectados, reinicia WEB y repite las comprobaciones:

```bash
sudo reboot
```

Vuelve a entrar por SSH, ejecuta `cd /opt/ctf`, `sudo docker compose -f compose.web.yml ps`, la prueba de servicios del paso 13 y la comprobación del navegador. DATOS también debe tener su arranque y montaje persistente verificados según su propia guía.

## 16 Acceso de red y HTTPS

Este procedimiento publica **HTTP en una red de laboratorio restringida**. HTTP no cifra el acceso del navegador. Para alumnos en una red compartida o una publicación más amplia, completa HTTPS con un dominio o certificado de la autoridad interna antes de usar credenciales reales sobre ese acceso.

No se ha confirmado un nombre DNS ni una autoridad de certificados para esta instalación. No solicites un certificado público para la IP privada `10.10.10.13`. Cuando se configure HTTPS, actualiza `PUBLIC_ORIGIN` a la URL exacta y haz que el proxy preserve WebSocket y el protocolo HTTPS. No basta con cambiar `http` por `https` en el navegador.

Para la red, el administrador debe permitir:

| Origen | Destino | Puerto | Finalidad |
|---|---|---|---|
| Equipo administrativo autorizado | WEB `.13` | TCP 22 | SSH |
| Red de estudiantes autorizada | WEB `.13` | TCP 80 en esta fase | Portal |
| WEB `.13` | DATOS `.14` | TCP 5432 y 6379 | Bases |
| WEB `.13` | Guacamole real | El de su URL | Terminal integrada |
| WEB `.13` | VM de laboratorio autorizadas | SSH configurado | Preparación y limpieza cuando corresponda |

**Los puertos publicados por Docker pueden saltarse las reglas habituales de UFW.** Publicar solo en `10.10.10.13` limita la interfaz, pero no determina qué redes pueden llegar a ella. Usa las ACL del firewall de red o reglas compatibles con Docker para limitar el origen. No abras PostgreSQL, Redis ni el puerto API a los estudiantes. [Referencia Docker](https://docs.docker.com/engine/install/ubuntu/).

## 17 Operación diaria actualizaciones y respaldo

**Dónde: WEB.** Antes de cualquiera de estas órdenes:

```bash
cd /opt/ctf
```

| Necesidad | Comando |
|---|---|
| Ver estado | `sudo docker compose -f compose.web.yml ps` |
| Ver últimos errores del backend | `sudo docker compose -f compose.web.yml logs --tail=100 api` |
| Ver registros mientras llegan | `sudo docker compose -f compose.web.yml logs -f api web` |
| Reiniciar procesos sin cambios de configuración | `sudo docker compose -f compose.web.yml restart api web` |
| Detener la plataforma sin borrar nada | `sudo docker compose -f compose.web.yml stop` |
| Iniciarla de nuevo | `sudo docker compose -f compose.web.yml up -d` |
| Aplicar cambios en `web.env` | `sudo docker compose -f compose.web.yml up -d --force-recreate api web` |
| Ver espacio utilizado | `df -h /` y `sudo docker system df` |

**Modificar `web.env` y ejecutar `restart` no recarga las variables en el contenedor.** Usa el comando de recreación de la tabla.

### Actualizar el código sin perder la copia anterior

Con el código obtenido por Git, las siguientes versiones se actualizan mediante `git pull`, **sin transferir archivos comprimidos desde Windows**. Programa el mantenimiento sin estudiantes conectados, respalda la base en DATOS y comprueba el estado:

```bash
cd /opt/ctf
git remote -v
git branch --show-current
git status --short
git rev-parse HEAD
git fetch origin main
git log --oneline HEAD..origin/main
```

Verifica que el remoto sea `https://github.com/lavillamarin3-hash/ctf-platform.git` y la rama `main`. Si existen modificaciones locales rastreadas, revísalas antes de continuar: no uses `git reset --hard` ni `git clean -fd`. Los archivos `deploy/` y `compose.web.yml` se mantienen por separado de Git.

En WEB guarda las imágenes actuales y detén la plataforma:

```bash
cd /opt/ctf
sudo docker image tag cociber-api:despliegue-20261022 cociber-api:anterior
sudo docker image tag cociber-web:despliegue-20261022 cociber-web:anterior
sudo docker compose -f compose.web.yml stop
```

Respalda el código y la configuración:

```bash
sudo install -d -m 0700 /var/backups/cociber-web
sudo tar -czf "/var/backups/cociber-web/codigo-$(date +%Y%m%d-%H%M%S).tar.gz" -C /opt/ctf backend frontend deploy compose.web.yml
sudo cp -a /etc/cociber-ctf "/var/backups/cociber-web/config-$(date +%Y%m%d-%H%M%S)"
```

Después de revisar los commits pendientes, aplica solamente una actualización de avance rápido, comprueba los auxiliares y reconstruye:

```bash
cd /opt/ctf
git pull --ff-only origin main
git rev-parse HEAD
test -f deploy/compose.web.yml && test -f compose.web.yml && echo 'Plantillas presentes'
sudo docker compose -f compose.web.yml build
sudo docker compose -f compose.web.yml run --rm --no-deps api python /opt/ctf-deploy/verificar_servicios.py
sudo docker compose -f compose.web.yml up -d
```

Si Git informa un conflicto o no aparecen los auxiliares, detente y revisa antes de construir. Para actualizar `compose.web.yml` o los scripts de despliegue, revisa aparte las plantillas publicadas en `guia_despliege`. Si hay migraciones de datos, valida su procedimiento antes de aplicarlas: volver a imágenes anteriores no revierte la base.

### Volver a la imagen anterior si la actualización falla

Solo si creaste las etiquetas `anterior` y no se modificó el esquema de forma incompatible:

```bash
sudo docker compose -f compose.web.yml stop
sudo docker image tag cociber-api:anterior cociber-api:despliegue-20261022
sudo docker image tag cociber-web:anterior cociber-web:despliegue-20261022
sudo docker compose -f compose.web.yml up -d --no-build --force-recreate
```

Restaura también la configuración anterior si la cambiaste y comprueba el resultado. No uses `build` inmediatamente después: reemplazaría otra vez la imagen restaurada.

### Qué respaldar

- **En DATOS:** PostgreSQL, configuración y credenciales, y la persistencia Redis mediante su guía. Una copia del código no contiene usuarios ni ranking.
- **En WEB:** código, `compose.web.yml`, `/etc/cociber-ctf`, claves SSH y registro de las versiones de imágenes que aprobaste.
- Guarda los respaldos privados en otro almacenamiento protegido. Una copia en el mismo disco sirve para una corrección rápida, pero no para recuperarte si se pierde la VM.
- Conserva `FIELD_HMAC_SECRET` y `JWT_SECRET` junto con la copia de la instalación a la que pertenecen.

Elimina las copias temporales de configuración cuando todo funcione y tengas el respaldo privado. **En WEB**, únicamente las copias temporales del paso 8 y 9:

```bash
rm -i ~/ctf-original.env ~/application-db.env
```

Si alguno no existe, el aviso es normal. **En DATOS**, elimina solamente la copia de transferencia de tu carpeta personal, no la de `/etc`:

```bash
rm -i ~/application-db.env
```

No uses `docker compose down -v`, `docker system prune --volumes`, `FLUSHDB`, `FLUSHALL` ni borrados de tablas como mantenimiento habitual.

## 18 Solución de problemas

| Síntoma | Qué significa o qué comprobar | Acción |
|---|---|---|
| `no configuration file provided` | Estás en otra carpeta o falta `-f` | `cd /opt/ctf` y usa `sudo docker compose -f compose.web.yml ...` |
| `permission denied` con Docker | Falta permiso para el servicio Docker | Usa `sudo docker`; no cambies permisos del socket |
| `Cannot connect to the Docker daemon` | Docker no está iniciado | `sudo systemctl status docker --no-pager`; después `sudo systemctl start docker` si está detenido |
| `Cannot assign requested address` | `.13` no existe en la tarjeta de WEB | Revisa `ip -br address` y Netplan |
| `address already in use` | Otro servicio usa el puerto 80 | `sudo ss -lntp`; identifica el servicio antes de detenerlo |
| Falla la descarga de imágenes | Internet, DNS, proxy o espacio | `getent hosts registry-1.docker.io`, `df -h /`; revisa la red |
| `npm ci` falla | Error de descarga o incoherencia del lockfile | Guarda el primer error; conserva `package-lock.json` y Node 22; no uses `npm install` a ciegas |
| `502 Bad Gateway` | Nginx no puede hablar con API | Mira `ps` y `logs --tail=100 api`; verifica que el servicio se llame `api` |
| La portada abre pero no carga datos | API o bases fallan | Ejecuta `verificar_servicios.py`; el health HTTP solo no basta |
| `Connection refused` hacia `.14` | Motor apagado, puerto equivocado o escucha local | Revisa servicio y `ss -lntp` en DATOS |
| Timeout hacia `.14` | Firewall o ruta | Revisa `ip route get 10.10.10.14`, ACL y reglas para origen `.13` |
| PostgreSQL rechaza usuario o `pg_hba` | Cuenta/contraseña incorrecta, TLS o IP no autorizada | Revisa DATOS y regenera el archivo privado si cambiaron credenciales |
| `NOAUTH`, `WRONGPASS` o `NOPERM` Redis | Falta autenticación o permisos ACL | Usa la cuenta `cociber_app` y su contraseña Redis, no la de PostgreSQL |
| `relation does not exist` o columnas faltantes | Destino vacío o esquema distinto | Completa restauración/migración; no habilites creación automática |
| `admin` no inicia sesión | No es un usuario automático | Usa tu cuenta web restaurada o el asistente inicial solo si no hay usuarios |
| Terminal en blanco | Guacamole, WebSocket o ruta a las VM | Comprueba modo real, direcciones actuales y reglas de red; revisa logs sin publicar secretos |
| `Origin no permitido` | La URL usada no coincide con `PUBLIC_ORIGIN` | Usa `http://10.10.10.13` o configura la URL real y recrea contenedores |
| No aparecen cambios nuevos | Imagen antigua o caché del navegador | Reconstruye y recrea; después Ctrl+F5 en el navegador |
| Tras reiniciar no vuelve | Docker no habilitado o contenedores detenidos manualmente | `sudo systemctl enable --now docker` y `sudo docker compose -f compose.web.yml up -d` |

Al pedir ayuda, comparte el comando, el primer error y el estado de los servicios. Revisa los registros antes de copiarlos y retira contraseñas, tokens y URLs privadas.

## 19 Lista final de comprobación

- [ ] WEB ejecuta Ubuntu Server 26.04 y tiene `10.10.10.13/24` persistente.
- [ ] Gateway, DNS y tarjeta de red están confirmados.
- [ ] DATOS responde en `.14`, tiene la base `cociber_ctf` y las cuentas `cociber_app`.
- [ ] Se conservaron los datos anteriores o se eligió conscientemente la instalación nueva.
- [ ] Se clonó la rama `main` de `ctf-platform` y se registró el commit desplegado.
- [ ] Los secretos están fuera del código y del ZIP; `web.env` tiene permisos 600.
- [ ] El Compose nuevo enumera únicamente `api` y `web`.
- [ ] El build terminó sin errores y `pip check` / `nginx -t` aprobaron.
- [ ] El verificador confirma PostgreSQL, TLS, esquema y Redis autenticado.
- [ ] Existe un usuario administrador de la plataforma y puede iniciar sesión.
- [ ] Se ven los usuarios, retos y puntos esperados.
- [ ] La API anterior no está ejecutando limpieza sobre la misma base.
- [ ] El navegador abre `http://10.10.10.13` y las rutas internas funcionan.
- [ ] Se validaron ranking, WebSocket y, si aplica, terminal e inicio/cierre de laboratorio.
- [ ] El reinicio de WEB conserva el funcionamiento.
- [ ] Hay un respaldo fuera de la VM y un procedimiento de recuperación.
- [ ] Antes de ampliar el acceso, se resolvieron HTTPS y las restricciones de red.

## 20 Trazabilidad y referencias

Se contrastó la carpeta activa con los chats **Estabiliza la plataforma CTF**, **Revisa chats y carpetas de CTF**, **Verificar acceso al proyecto CTF** y **Datos proyecto CTF**. Los resúmenes históricos se contrastaron con el código actual; no demuestran por sí solos que las nuevas VM estén instaladas.

Archivos principales consultados: `backend/Dockerfile`, `backend/requirements.txt`, `backend/app/core.py`, `backend/app/models.py`, `backend/app/services/bootstrap.py`, `frontend/Dockerfile`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/nginx.conf`, `docker-compose.yml` y las guías `docs/05_APLICACION_Y_MIGRACION.md`, `docs/06_ACEPTACION_Y_RESPALDO.md` y los scripts SQL de `cociber-ctf-deploy`.

Las instrucciones de construcción preservan las versiones declaradas por el proyecto; las imágenes por etiqueta y los rangos Python no son una lista congelada de versiones. Después de aprobar el despliegue, registra las imágenes y dependencias resueltas antes de actualizar. No se afirma que las etiquetas actuales del repositorio sean las últimas versiones disponibles.

Fuentes oficiales complementarias:

- [Red en Ubuntu Server](https://ubuntu.com/server/docs/explanation/networking/configuring-networks/) para identificar interfaces y configurar red.
- [PostgreSQL 16 y copias lógicas](https://www.postgresql.org/docs/16/backup-dump.html) para respaldos y restauración.
- [Control de acceso PostgreSQL](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html) para restringir clientes.
- [Seguridad Redis](https://redis.io/docs/latest/operate/oss_and_stack/management/security/) para autenticación y acceso de red.
- [Nginx y WebSocket](https://nginx.org/en/docs/http/websocket.html) para el proxy de las conexiones persistentes.

Las plantillas acompañantes son auxiliares de este procedimiento. Se revisan y se ejecutan en tus servidores siguiendo el orden indicado; no sustituyen las pruebas de aceptación en las VM reales.
