# solomIA
Local AI infrastructure with RAG by department | Ollama + Groq + Open WebUI | On-premise deployment

Sistema de IA corporativa multitenante con RAG por departamento, desplegado en hardware propio. Diseñado para PYMEs que necesitan privacidad de datos, sin depender de la nube para información sensible.

---

## Arquitectura

Mac (Bahía / Admin) ─────────────────────────────
├── Monitoreo → Uptime Kuma
├── Proxy → Nginx
├── Terminal personal → Script Groq
└── Acceso web a servicios de la Dell
│
│ vía web / red local
▼
Dell Inspiron (Motor principal) ─────────────────
├── Contenedor Depto 1 → Open WebUI → Groq → ChromaDB
├── Contenedor Depto 2 → Open WebUI → Groq → ChromaDB
├── Contenedor Depto 3 → Open WebUI → Groq → ChromaDB
└── Contenedor VIP → Ollama local (VRAM) → datos sensibles

---

## Hardware

Inspiron 15 Gaming 5577

CPU

Intel (R) Core(TM) i5-7300HQ Quad Core CPU @ 3.5 GHz , 7th Gen.

RAM

16GB DDR4

### Dell Inspiron 15 Gaming 5577 — Motor
| Componente | Detalle |
|---|---|
| RAM | 16GB DDR4 2133MHz |
| CPU | Intel(R) Core(TM) i5-7300HQ Quad Core CPU @3.5 GHz, 7th Gen. |
| GPU | NVIDIA GeForce GTX 1050 4GB VRAM |
| Almacenamiento | 480GB SSD + 120GB NVMe |
| OS | Ubuntu Server 24.04 LTS minimal |

### iMac 24" A1225 — Bahía consulta y de administración remota a Dell
| Componente | Detalle |
|---|---|
| RAM | 4GB |
| Almacenamiento | 480GB SSD SATA |
| OS | Debian 12 minimal |

---

## Stack tecnológico

| Herramienta | Rol |
|---|---|
| Ollama + qwen3:4b | Modelo local para datos sensibles |
| Groq API | Backend LLM para departamentos |
| Open WebUI | Interfaz por departamento |
| ChromaDB | Base de vectores RAG por contenedor |
| Docker | Aislamiento por departamento |
| Nginx | Proxy y acceso central |
| Uptime Kuma | Monitoreo de servicios |

---

## Estructura de contenedores

Cada departamento tiene:
- Su propia instancia de Open WebUI
- Su propio puerto
- Sus propios documentos encapsulados
- Su propia cuenta Groq
- Su propia base ChromaDB

Los documentos de un departamento **nunca son accesibles** desde otro.

---

## FASES DEL PROYECTO

### Fase 1 — Infraestructura base <--- aquí estamos
- [ ] Reinstalación Ubuntu Server 24.04 en Dell
- [ ] Reinstalación Debian 12 minimal en Mac
- [ ] Docker + NVIDIA Container Toolkit
- [ ] Ollama con qwen3:4b
- [ ] Primer contenedor Open WebUI funcionando

### Fase 2 — RAG por departamento
- [ ] ChromaDB por contenedor
- [ ] Documentos ingresados por departamento
- [ ] Groq como backend por contenedor
- [ ] Acceso multiusuario por depto (3 personas c/u)

### Fase 3 — Administración y monitoreo
- [ ] Uptime Kuma en Mac
- [ ] Nginx como proxy
- [ ] Script Groq en terminal para uso personal

### Fase 4 — Desktop overlay
- [ ] App flotante tipo Copilot (Electron → Tauri)
- [ ] Acceso rápido desde cualquier punto de la empresa

---

## Decisiones de arquitectura

**¿Por qué Groq y no solo Ollama?**
La GTX 1050 tiene 4GB de VRAM. Groq maneja el cómputo/logica-matematica pesada en la nube para los departamentos generales. Ollama local solo procesa datos sensibles que no pueden salir de la red.

**¿Por qué un contenedor por departamento?**
Aislamiento real de documentos. Produccion no puede acceder a documentos de Calidad, Investigacion y Desarrollo, etc.

**¿Por qué la Mac como bahía separada?**
Separación de responsabilidades. La Dell usa todos sus recursos en servir IA. La Mac administra sin consumir recursos del motor.

---

## 👤 Autor

Beto — [@B2Wer](https://github.com/B2Wer)  
Auxiliar de Sistemas | Estudiante de Ing. en Desarrollo de Software  
Construyendo infraestructura de IA on-premise desde cero.
