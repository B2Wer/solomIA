# 1. Arquitectura general

## 1.1 Resumen

Solomia es una plataforma de asistentes IA departamentales (RH, Calidad,
Producción, I+D, Ventas) basada en [Open WebUI](https://github.com/open-webui/open-webui),
con un backend de inferencia externo (Groq) y una base de datos PostgreSQL
compartida. Se apoya en **dos máquinas físicas/lógicas** distintas:

| | Máquina A — Host de Orquestación | Máquina B — Host de Inferencia |
|---|---|---|
| Rol | Ejecuta Docker Engine: los 5 contenedores Open WebUI + PostgreSQL. También corre un servicio Ollama local y el pipeline de procesamiento documental. | Máquina separada, alcanzable por red privada tipo VPN mesh; acceso administrativo por SSH. |
| GPU | GPU de gama de entrada (~4 GB VRAM) — insuficiente para servir modelos grandes con buen rendimiento. | No confirmado en el código del proyecto (ver nota abajo). |
| Conectividad | IP en la LAN interna de la organización + IP en la red privada VPN. | Alcanzable solo por la red privada VPN (no aparece en la LAN local ni en el `docker-compose.yml`). |

> ⚠️ **Nota de honestidad sobre la Máquina B:** su existencia se confirmó por
> evidencia operativa (acceso SSH registrado y presencia como nodo en la red
> VPN privada), **no** porque aparezca referenciada en `docker-compose.yml`,
> en las variables de entorno de los contenedores, o en algún script del
> repo. Ningún archivo del proyecto apunta a su IP/hostname como backend de
> inferencia. Esto sugiere dos escenarios posibles, que conviene confirmar
> con el responsable de infraestructura:
> 1. Es una máquina de uso manual/experimental (probar modelos localmente,
>    desarrollo) que aún no está integrada al flujo productivo, o
> 2. Está integrada de alguna forma no versionada en este repo (por ejemplo,
>    configurada manualmente dentro de una instancia de Open WebUI vía su
>    UI, en vez de por variable de entorno).
>
> Tal como está el código hoy, el **backend de LLM en producción es Groq**
> (API cloud), no la Máquina B ni el Ollama local — ver `1.3`.

## 1.2 Diagrama de comunicación

```
┌─────────────────────────────────────────────────────────────┐
│ Máquina A — Host de Orquestación (Docker)                   │
│                                                               │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐      │
│  │ openwebui-rh  │ │openwebui-cal. │ │openwebui-prod.│ ...  │
│  │  :3001        │ │  :3002        │ │  :3003        │      │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘      │
│          │                 │                 │              │
│          └────────┬────────┴────────┬────────┘              │
│                    │                 │                       │
│           ┌────────▼──────┐  ┌───────▼────────┐             │
│           │  PostgreSQL    │  │  Ollama local   │             │
│           │  :5432         │  │  :11434         │             │
│           │  (compartida   │  │  (presente, no  │             │
│           │   entre todos) │  │  conectado hoy  │             │
│           └────────────────┘  │  a Open WebUI — │             │
│                                │  ENABLE_OLLAMA  │             │
│                                │  _API=false)    │             │
│                                └─────────────────┘             │
└─────────────────────┬───────────────────────────────────────┘
                       │  HTTPS (OPENAI_API_BASE_URL)
                       ▼
              ┌──────────────────┐
              │  Groq API (cloud) │  ← backend de inferencia real hoy
              │  api.groq.com     │
              └──────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Máquina B — Host de Inferencia (separada)                    │
│  Alcanzable por VPN privada. Acceso SSH administrativo.      │
│  Rol productivo no confirmado en el código del repo.         │
└─────────────────────────────────────────────────────────────┘
```

## 1.3 Backend de inferencia: Groq, no Ollama

Cada contenedor Open WebUI departamental está configurado con:

```
ENABLE_OLLAMA_API=false
OPENAI_API_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=<placeholder por departamento, sin rellenar en el compose actual>
OLLAMA_BASE_URL=http://<gateway-bridge-docker>:11434
```

Es decir: aunque hay un servicio Ollama corriendo en la Máquina A (y se
encontró evidencia de que se descargó al menos un modelo de embeddings),
**la API de Ollama está deshabilitada** (`ENABLE_OLLAMA_API=false`) en los 5
contenedores. El proveedor de chat/completions activo es **Groq** (API
externa, cloud, OpenAI-compatible).

Esto tiene una implicación de arquitectura importante: **los prompts y
posiblemente fragmentos de los documentos departamentales (vía RAG) salen
de la red interna hacia Groq** cada vez que un usuario conversa con un
asistente. Vale la pena confirmar con el responsable si esto es aceptable
para los documentos de tipo RH/Calidad/TI (algunos son procedimientos
internos sensibles).

## 1.4 Redes

- **LAN interna**: red local de la organización, donde vive la Máquina A y
  los equipos de usuarios finales que acceden a los puertos `3001-3005`.
- **Red privada tipo VPN mesh**: conecta administrativamente ambas
  máquinas (y otros equipos de la organización) fuera de la LAN, usada para
  acceso remoto/SSH, no para tráfico de la aplicación Open WebUI.
- **Red de contenedores Docker**: bridge interno (`172.18.0.0/16` en el
  compose actual) usado solo para que los contenedores alcancen el Ollama
  del host vía `host.docker.internal`.

## 1.5 Almacenamiento

- Cada departamento tiene su propio volumen persistente (`/mnt/data/docker-volumes/<depto>/`)
  con: `uploads/` (documentos subidos por el usuario a Open WebUI),
  `vector_db/` (índice vectorial del RAG, uno **aislado por departamento**),
  `cache/` y el `webui.db` (SQLite de configuración/usuarios de esa
  instancia).
- PostgreSQL tiene su propio volumen (`postgres-data`), compartido por
  todos los departamentos — ver riesgo asociado en el documento de
  decisiones técnicas.
