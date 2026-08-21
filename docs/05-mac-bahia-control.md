# 5. Mac (bahía de control) — Nginx Proxy Manager, Uptime Kuma, Homepage, Netdata

Fuente: exploración por SSH de la segunda máquina física del proyecto (el
iMac descrito en el README raíz como "Bahía de consulta y administración
remota"), el 2026-08-21. Se leyó `~/solomia/docker-compose.yml`, los
archivos de configuración de Homepage, y el estado de los contenedores
Docker corriendo en esa máquina.

> **Nota sobre sanitización:** igual que el resto de la documentación, este
> archivo **no incluye** IPs, hostnames reales, ni el usuario de acceso
> SSH/Tailscale usado para llegar a esta máquina. Se usan placeholders
> (`<...>`) donde la configuración real depende de esos datos. Los valores
> reales existen en `docker-compose.yml` y en `homepage/settings.yaml` /
> `homepage/services.yaml` de esa máquina — revísalos ahí directamente si
> los necesitas, y ten cuidado si en algún momento subes esa carpeta a un
> repositorio.

## 5.1 Corrección a la "Máquina B" de `01-arquitectura.md`

El documento de arquitectura general (`01-arquitectura.md`, sección 1.1)
documentó, a partir de evidencia indirecta encontrada en la Máquina A
(host SSH conocido + presencia como nodo en una red VPN mesh), una
"Máquina B" cuyo rol productivo no se pudo confirmar en el código, y
planteó como hipótesis que fuera un host de inferencia separado o una
máquina de uso experimental.

Con acceso directo por SSH a esa máquina, se puede confirmar que:

- **No es un host de inferencia.** No corre Ollama, ni ningún backend LLM,
  ni tiene GPU relevante para ese rol.
- **Es la "bahía de control"** descrita en el README raíz del proyecto:
  corre exclusivamente servicios de administración/observabilidad —
  **Nginx Proxy Manager, Uptime Kuma, Homepage y Netdata** — como
  contenedores Docker en un único `docker-compose.yml`.
- Confirma la separación de responsabilidades que ya proponía el README:
  la Máquina A dedica sus recursos (limitados: GPU de 4GB, 16GB RAM) a
  servir los asistentes IA; esta segunda máquina administra sin
  competir por esos recursos.

Esto **no** contradice el resto de `01-arquitectura.md` — el backend de
inferencia real hoy sigue siendo Groq (cloud), no esta máquina ni la
Máquina A. Solo corrige la naturaleza de la "Máquina B": es un nodo de
control/observabilidad, no un segundo nodo de cómputo.

## 5.2 Sistema base

| | Detalle |
|---|---|
| Hardware | iMac 24" A1225 (ver specs en README raíz: 4GB RAM, 480GB SSD SATA) |
| OS | Debian GNU/Linux 12 (bookworm) — **no macOS**: es un iMac con Debian instalado, no ejecutando el sistema operativo de Apple |
| Docker | Docker 29.7.2 + Docker Compose v5.5.0 (plugin `compose`) |
| Uptime al momento de la exploración | ~25 días |
| Uso de disco | ~5% de 438GB |
| RAM libre | ~2.8GB disponibles de 3.8GB (mayormente caché) |

## 5.3 Stack de contenedores

Todo vive en un único `~/solomia/docker-compose.yml`, con cuatro
servicios, cada uno con `restart: unless-stopped` y su propio volumen
bind-mount en un subdirectorio local (`./npm`, `./kuma`, `./homepage`; Netdata no persiste datos propios, monta `/proc` y `/sys` del host en solo lectura):

| Servicio | Imagen | Puerto host→contenedor | Volumen |
|---|---|---|---|
| `nginx-proxy-manager` | `jc21/nginx-proxy-manager:latest` | `80`, `443`, `81` (admin UI) | `./npm/data`, `./npm/letsencrypt` |
| `uptime-kuma` | `louislam/uptime-kuma:1` | `3005:3001` | `./kuma` |
| `netdata` | `netdata/netdata` | `19999:19999` | `/proc`, `/sys` (solo lectura, del host) |
| `homepage` | `ghcr.io/gethomepage/homepage:latest` | `3010:3000` | `./homepage` |

Estado al momento de la exploración: los cuatro contenedores están
**activos**, tres marcados `healthy` por Docker (NPM no expone healthcheck
propio). Homepage se recreó más recientemente (julio 2026) que los otros
tres (mayo 2026), consistente con que su variable `HOMEPAGE_ALLOWED_HOSTS`
se haya ajustado después del despliegue inicial.

## 5.4 Nginx Proxy Manager — estado actual

- Expone su UI de administración en el puerto `81` (HTTP, no HTTPS) y
  reserva `80`/`443` para el tráfico proxied.
- **No hay ningún "Proxy Host" configurado todavía**: el directorio
  `npm/data/nginx/proxy_host/` está vacío (sin archivos `.conf`), y
  `npm/letsencrypt/` no tiene ningún certificado emitido (`live/` no
  existe, `custom_ssl/` vacío). Es decir, NPM está **instalado pero sin
  configurar** — no está actuando todavía como reverse proxy de ningún
  servicio real, ni hay dominios ni TLS asociados.
- Esto contrasta con el objetivo declarado en el README raíz ("Proxy de
  acceso → Nginx"): hoy el acceso a los servicios de la Dell y de esta
  misma máquina se hace **directo por IP:puerto** (ver Homepage, 5.6), no
  a través de NPM.

## 5.5 Uptime Kuma

- Corre en el puerto `3005` (mapeado a `3001` interno).
- Persiste su estado en `kuma.db` (SQLite) dentro de `./kuma`; no se pudo
  inspeccionar el contenido (no hay `sqlite3` disponible ni en el host ni
  en la imagen del contenedor) para listar qué monitores tiene
  configurados exactamente. Existen subcarpetas `docker-tls/`,
  `screenshots/` y `upload/`, todas presentes pero sin indicios (por sus
  fechas) de uso activo más allá del despliegue inicial.
- El README raíz lo describe como el monitor de los servicios de la Dell;
  no se pudo confirmar desde este archivo qué monitores concretos tiene
  dados de alta sin acceso a la UI o a la base SQLite.

## 5.6 Homepage — dashboard central

Configurado en español (`language: es`), tema oscuro, título "SolomIA
Dashboard". Sirve como el punto de entrada visual a todo el stack,
organizado en dos grupos:

- **Mac (Control):** enlaces directos (por IP:puerto, no vía NPM) a Nginx
  Proxy Manager, Uptime Kuma, Netdata y al propio Homepage.
- **Dell (IA):** enlaces directos a los 3 Open WebUI departamentales
  desplegados hoy (puertos `3001`–`3003`, consistente con lo documentado
  en `03-contenedores-departamentales.md`) y a Ollama (`11434`).

Notas:

- `bookmarks.yaml` y `widgets.yaml` están en su contenido **por defecto**
  del template de Homepage (enlaces genéricos a GitHub/Reddit/YouTube,
  widgets de recursos del sistema + buscador) — no personalizados para
  Solomia todavía.
- `docker.yaml` está vacío/comentado: Homepage no está integrado con el
  socket de Docker para auto-descubrir contenedores; los enlaces son
  estáticos, mantenidos a mano en `services.yaml`.
- `HOMEPAGE_ALLOWED_HOSTS` (variable de entorno) y `allowed_hosts` (en
  `settings.yaml`) listan, además de la IP LAN de esta máquina, **cuatro
  IPs adicionales de una red privada tipo VPN mesh** (mismo mecanismo de
  red privada mencionado en `01-arquitectura.md`, sección 1.4) — es decir,
  Homepage está pensado para accederse tanto desde la LAN local como
  remotamente a través de esa VPN.

## 5.7 Netdata

Corre con `cap_add: SYS_PTRACE` y monta `/proc` y `/sys` del host en modo
lectura para reportar métricas del sistema (CPU, memoria, red, procesos)
de esta máquina en tiempo real, expuesto sin autenticación en el puerto
`19999`. No tiene configuración adicional (no hay `netdata.conf`
personalizado en el volumen — corre con la config por defecto de la
imagen).

## 5.8 Red

- Esta máquina tiene una IP en la LAN local **y** una IP en la red privada
  tipo VPN mesh (Tailscale, aunque el binario/cliente no se identifica por
  nombre en la documentación general — ver `01-arquitectura.md` 1.4), la
  misma red mencionada como conexión administrativa entre ambas máquinas.
- Se confirma por esta vía que la Máquina A (Dell) es alcanzable desde
  esta máquina tanto por IP LAN directa como por su IP en esa red privada
  — consistente con `01-arquitectura.md`.
- **Hallazgo nuevo:** la red privada tiene, además de esta máquina y la
  Dell, **al menos otros 3 nodos** (identificados solo por su nombre en
  esa red, uno de ellos actualmente desconectado) que no aparecen
  mencionados en ningún documento del proyecto ni en el README raíz. No
  se pudo determinar desde aquí si son equipos personales del
  administrador, otros clientes de la organización que administra esta
  infraestructura, o parte de un despliegue no documentado. Vale la pena
  confirmar con el responsable qué son esos nodos y si tienen algún tipo
  de acceso a los servicios de Solomia.

## 5.9 Watchtower — ausente

El mensaje que originó esta exploración mencionaba Watchtower como parte
del stack de esta máquina, pero **no se encontró evidencia de que esté
desplegado**: no aparece en `docker ps` (ni activo ni detenido), no está
declarado en `docker-compose.yml`, no hay `crontab` ni temporizador de
`systemd` relacionado, y no se encontró ningún archivo con "watchtower" en
el nombre en el home del usuario. Dos lecturas posibles a confirmar con el
responsable:

1. Watchtower está planeado pero aún no desplegado (consistente con que
   NPM tampoco está configurado todavía — ver 5.4), o
2. Se retiró en algún momento y el README/las notas del proyecto quedaron
   desactualizadas.

En cualquier caso, **hoy no hay actualización automática de imágenes**
para ninguno de los 4 contenedores de esta máquina — las actualizaciones,
si se hacen, son manuales.

## 5.10 Hallazgos / riesgos a revisar

| # | Hallazgo | Severidad sugerida |
|---|---|---|
| 1 | Nginx Proxy Manager está desplegado pero sin ningún Proxy Host ni certificado configurado — no cumple hoy su rol de proxy central | Media — objetivo declarado en el README no implementado aún |
| 2 | Watchtower, mencionado como parte del stack, no está desplegado ni configurado en ningún lado de esta máquina | Baja/Informativo — confirmar si es trabajo pendiente o documentación desactualizada |
| 3 | Netdata expone métricas del sistema en el puerto `19999` sin autenticación | Media si la LAN no está segmentada — cualquier equipo en la LAN puede ver métricas detalladas del host |
| 4 | NPM UI de administración (`:81`) accesible por HTTP plano, no HTTPS | Media — credenciales de admin de NPM viajarían sin cifrar en la LAN |
| 5 | La red privada VPN mesh tiene ≥3 nodos adicionales no documentados en el proyecto | Media — confirmar su propósito y si tienen alcance a los servicios de Solomia |
| 6 | No se pudo inspeccionar el contenido de `kuma.db` (sin `sqlite3` disponible) para verificar qué monitores están dados de alta realmente | Informativo — pendiente de revisión directa en la UI de Uptime Kuma |

## 5.11 Preguntas abiertas para el responsable de infraestructura

- ¿NPM y Watchtower son trabajo pendiente de la Fase 3 del proyecto (ver
  README raíz), o hay una razón para que sigan sin configurarse?
- ¿Qué son los nodos adicionales de la red privada VPN mesh (5.8) y
  tienen algún tipo de acceso a los servicios de Solomia?
- ¿Netdata y el puerto de administración de NPM (`:81`) deberían quedar
  restringidos a la red privada VPN en vez de expuestos en la LAN local?
