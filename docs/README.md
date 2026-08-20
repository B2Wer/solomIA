# Documentación técnica — Solomia

Documentación generada a partir de la exploración del proyecto el 2026-08-20.

> **Nota sobre sanitización:** por decisión explícita, esta documentación
> **no incluye** hostnames reales, IPs, usuarios de acceso, el nombre de la
> organización, ni nombres/códigos reales de documentos internos o de
> sistemas propietarios. Donde la arquitectura real depende de esos datos,
> se usan placeholders (`<...>`) o descripciones genéricas. Antes de
> compartir o subir esta carpeta a un repositorio remoto, revisa igualmente
> el resto del proyecto (`docker-compose.yml`, logs de terminal, etc.) —
> esta documentación describe la arquitectura, no reemplaza una auditoría
> de secretos.

## Índice

1. [Arquitectura general](01-arquitectura.md) — las 2 máquinas, cómo se comunican
2. [Pipeline de procesamiento documental (RAG)](02-pipeline-rag.md)
3. [Configuración de contenedores departamentales](03-contenedores-departamentales.md)
4. [Decisiones técnicas y hallazgos](04-decisiones-tecnicas.md)

## Alcance

Cubre lo que existe hoy en el árbol del proyecto (`infraestructura/`,
`procesamiento-documental/`, `ia-departamental/`, `administracion/`). Varias
carpetas del proyecto están **vacías** (placeholders para trabajo futuro):
`administracion/{configs,scripts,documentacion,logs}`,
`infraestructura/{docker,monitoring,nginx,backups}`, y las 5 subcarpetas de
`ia-departamental/`. Se listan en el documento de decisiones técnicas para
que quede registro de qué falta poblar.
