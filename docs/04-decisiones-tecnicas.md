# 4. Decisiones técnicas clave y hallazgos

Este documento junta el "por qué" detrás de las decisiones de arquitectura
que se pueden inferir del código, más una lista de hallazgos/riesgos
encontrados durante la exploración que valen una revisión.

## 4.1 Decisiones de diseño (inferidas)

### Un contenedor Open WebUI por departamento, en vez de una instancia multi-tenant
**Razonamiento probable:** aislamiento fuerte de datos. Cada departamento
tiene su propio `vector_db` (RAG), su propio `webui.db` (usuarios/chats) y
su propio puerto. Evita que un bug de permisos en Open WebUI exponga
documentos de un departamento a otro — el aislamiento ocurre a nivel de
proceso/filesystem, no de lógica de aplicación. El costo es 5x el uso de
recursos (5 procesos Node/Python de Open WebUI corriendo simultáneamente)
frente a una instancia multi-tenant.

### Groq como backend de inferencia, con Ollama local presente pero deshabilitado
**Razonamiento probable:** la GPU local de la Máquina A tiene memoria
limitada (~4 GB VRAM), insuficiente para servir con buena latencia modelos
de tamaño razonable para uso corporativo. Groq ofrece inferencia rápida
como servicio cloud. Ollama local parece reservado para tareas más ligeras
— se encontró evidencia de que se descargó un modelo de embeddings
(`nomic-embed-text`), lo que sugiere que el rol pensado para Ollama es
generar embeddings localmente (barato, corre bien en poco VRAM) mientras
Groq se encarga del chat/completions (caro en cómputo).

**Implicación a validar con el responsable:** con `OPENAI_API_BASE_URL`
apuntando a Groq, el contenido de los prompts (y de los fragmentos RAG que
Open WebUI inyecte en el contexto) sale de la red interna hacia un
proveedor externo. Para departamentos con documentos sensibles (RH, TI)
esto puede requerir una revisión de cumplimiento/confidencialidad.

### Pipeline documental en dos etapas separadas (`convert.sh` + `clean.py`)
**Razonamiento probable:** separar "conversión de formato" (Pandoc: DOCX →
Markdown, responsabilidad genérica) de "limpieza semántica de plantilla
corporativa" (regex específicas para tablas de firma, historial de
revisiones, headings falsos de Word — responsabilidad específica del
dominio). Permite iterar la lógica de limpieza sin tocar la conversión, y
depurar cada etapa por separado revisando su carpeta de salida
intermedia (`2converted-md/`).

### Aislamiento de `vector_db` por departamento, pero Postgres compartido
**Razonamiento probable:** el RAG (dato sensible/departamental) está
aislado; Postgres probablemente se pensó para metadata/autenticación no
sensible por departamento (o quedó de una fase de diseño anterior — ver
hallazgo 4.2). Es una asimetría a resolver: si Postgres sí llega a
usarse para algo departamental, el aislamiento se rompería ahí.

### Arquitectura de dos máquinas (orquestación + inferencia)
**Razonamiento probable:** descargar el cómputo de inferencia pesada a un
host separado con mejor hardware, dejando la Máquina A dedicada a
orquestar contenedores y servir el pipeline documental. **No se pudo
confirmar en el código** que esta segunda máquina esté conectada al flujo
productivo actual (ver nota en `01-arquitectura.md`) — hoy el backend de
inferencia real es Groq (cloud), no esta segunda máquina.

## 4.2 Hallazgos / riesgos a revisar

| # | Hallazgo | Ubicación | Severidad sugerida |
|---|---|---|---|
| 1 | `WEBUI_SECRET_KEY` y `POSTGRES_PASSWORD` hardcodeados en texto plano, con patrón predecible (`<algo>-solomia-2026`) | `infraestructura/compose/docker-compose.yml` | Alta si el repo se sube a git o se comparte — mover a `.env` + `.gitignore`, o a Docker secrets |
| 2 | Puerto `5432` de Postgres expuesto a toda la LAN (`0.0.0.0:5432`), no solo a `localhost` | `docker-compose.yml` | Media — si no hay firewall en la Máquina A, cualquier equipo en la LAN puede intentar conectarse a la base |
| 3 | `clean.py` tiene el cuerpo entero duplicado en el archivo (funciones y `main()` repetidos) | `procesamiento-documental/docu-rag/scripts/clean.py` | Baja (no rompe funcionalidad, sí mantenibilidad) |
| 4 | TI tiene documentos preparados en el pipeline pero ningún contenedor Open WebUI propio | `docker-compose.yml` vs `/mnt/data/solomia/TI/` | Media — probable trabajo pendiente, confirmar intención |
| 5 | Segunda máquina de inferencia no referenciada en ningún archivo de configuración del repo | Todo el repo | Media — riesgo de "infraestructura fantasma" no documentada si de verdad está en uso productivo |
| 6 | `OPENAI_API_KEY` es un placeholder sin rellenar en las 5 instancias (`TU_GROQ_KEY_<depto>`) | `docker-compose.yml` | Informativo — si las keys reales se están inyectando por otro medio (`.env`, edición manual post-deploy), documentarlo; si no, los contenedores no podrían llamar a Groq con esta config tal cual |
| 7 | Carpetas vacías reservadas para trabajo futuro | `administracion/{configs,scripts,documentacion,logs}`, `infraestructura/{docker,monitoring,nginx,backups}`, `ia-departamental/{calidad,id,produccion,rh,ventas}` | Informativo |
| 8 | No hay `.gitignore` a nivel de proyecto ni el proyecto es aún un repo git | Raíz de `solomIA/` | A definir antes de versionar — asegurar que `venv/`, `__pycache__/`, y cualquier futuro `.env` queden excluidos |
| 9 | El filtro Lua de `convert.sh` elimina imágenes antes de que `clean.py` pueda leer su alt-text | `convert.sh` (paso Lua) vs `clean.py` (paso 5) | Baja — inconsistencia menor de diseño entre etapas, no bloqueante |

## 4.3 Preguntas abiertas para el responsable de infraestructura

- ¿La segunda máquina de inferencia está integrada al flujo productivo hoy,
  o es de uso experimental/manual?
- ¿Postgres se usa activamente por algún contenedor (vía `DATABASE_URL` no
  visible en este compose), o quedó desplegado para una fase futura?
- ¿Los departamentos con documentos sensibles (RH, TI) están de acuerdo en
  que sus prompts/fragmentos RAG salgan hacia Groq (API externa)?
- ¿Qué va a pasar con TI (contenedor pendiente) y con `Normas`
  (carpeta reservada)?
