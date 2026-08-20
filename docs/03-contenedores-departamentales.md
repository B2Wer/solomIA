# 3. Configuración de contenedores departamentales

Fuente: `infraestructura/compose/docker-compose.yml`. Todos los contenedores
departamentales comparten la misma imagen e idéntico patrón de
configuración; solo cambian nombre, puerto y volumen.

## 3.1 Patrón común (Open WebUI x5)

```yaml
image: ghcr.io/open-webui/open-webui:main
restart: unless-stopped
extra_hosts:
  - "host.docker.internal:<gateway-bridge-docker>"
environment:
  - WEBUI_NAME=<Nombre visible del departamento>
  - WEBUI_SECRET_KEY=<patrón predecible, ver 3.3>
  - ENABLE_OLLAMA_API=false
  - OPENAI_API_BASE_URL=https://api.groq.com/openai/v1
  - OPENAI_API_KEY=<placeholder sin rellenar en el compose>
  - OLLAMA_BASE_URL=http://<gateway-bridge-docker>:11434
  - AIOHTTP_CLIENT_TIMEOUT=300
```

## 3.2 Tabla de instancias

| Departamento | Container | Puerto host→contenedor | Volumen de datos |
|---|---|---|---|
| RH / Nóminas | `openwebui-rh` | `3001:8080` | `/mnt/data/docker-volumes/rh` |
| Calidad | `openwebui-calidad` | `3002:8080` | `/mnt/data/docker-volumes/calidad` |
| Producción | `openwebui-produccion` | `3003:8080` | `/mnt/data/docker-volumes/produccion` |
| I+D | `openwebui-id` | `3004:8080` | `/mnt/data/docker-volumes/id` |
| Ventas | `openwebui-ventas` | `3005:8080` | `/mnt/data/docker-volumes/ventas` |

Cada volumen contiene, dentro del contenedor, `app/backend/data`:
`uploads/`, `vector_db/`, `cache/` y el `webui.db` (SQLite) de esa
instancia — es decir, **usuarios, historial de chats y config de UI están
aislados por departamento**, no solo el contenido RAG.

## 3.3 Convención de `WEBUI_SECRET_KEY`

El valor sigue el patrón `<departamento>-solomia-2026` (ej. para RH sería
algo como `rh-solomia-2026`). **Esto no es un secreto generado
aleatoriamente**, es un valor predecible y hardcodeado directamente en el
`docker-compose.yml`. `WEBUI_SECRET_KEY` en Open WebUI se usa para firmar
tokens de sesión/JWT — un valor predecible reduce la protección real que
ese secreto está pensado para dar. Detalle y recomendación en el documento
de decisiones técnicas.

## 3.4 PostgreSQL (compartido)

```yaml
image: postgres:16
container_name: solomia-postgres
restart: unless-stopped
ports:
  - "5432:5432"
volumes:
  - /mnt/data/docker-volumes/postgres-data:/var/lib/postgresql/data
environment:
  - POSTGRES_USER=solomia
  - POSTGRES_PASSWORD=<hardcodeado en el compose, patrón simple>
  - POSTGRES_DB=solomia
```

- Es **una sola instancia compartida**, no una base por departamento (a
  diferencia del `vector_db`/SQLite de cada Open WebUI, que sí están
  aislados).
- Expone el puerto `5432` directamente al host (`0.0.0.0:5432` en el
  compose, sin restricción de bind a `127.0.0.1`) — cualquier equipo que
  alcance la LAN/IP de la Máquina A en el puerto 5432 puede intentar
  conectarse. Ver riesgo en decisiones técnicas.
- No queda claro en el compose actual **para qué usa Postgres cada
  instancia de Open WebUI** (por configuración por defecto, Open WebUI usa
  SQLite local salvo que se le indique `DATABASE_URL` explícitamente, y
  ese `DATABASE_URL` no aparece en las variables de entorno de ningún
  contenedor). Vale la pena confirmar si Postgres está realmente en uso
  hoy o si quedó desplegado para una integración futura.

## 3.5 Departamento sin contenedor propio: TI

`/mnt/data/solomia/TI/` tiene su propio árbol de pipeline documental
(`1raw-docx`, `2converted-md`, `3cleaned-md`, `backups`) con documentos ya
procesados, pero **no existe un `openwebui-ti` en el compose**. Es decir:
TI tiene documentos preparados para RAG pero, tal como está la
infraestructura hoy, no tiene un asistente departamental propio donde
consultarlos. Vale la pena confirmar si es un despliegue pendiente o si
esos documentos se piensan integrar a otro departamento.

## 3.6 Carpeta `Normas`

Existe `/mnt/data/solomia/Normas/` sin las subcarpetas de pipeline
(`1raw-docx`, etc.) y sin contenedor asociado — parece un directorio
reservado para uso futuro (ej. normativa transversal a todos los
departamentos), aún no poblado.
