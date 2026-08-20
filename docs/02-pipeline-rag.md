# 2. Pipeline de procesamiento documental (RAG)

Ubicación: `procesamiento-documental/docu-rag/scripts/`

El pipeline prepara documentos corporativos en `.docx` para ser ingeridos
como "Knowledge" (base de conocimiento) en el Open WebUI de cada
departamento. Consta de **dos scripts independientes**, ejecutados
manualmente en secuencia, uno por departamento:

```
1raw-docx/  ──(convert.sh)──>  2converted-md/  ──(clean.py)──>  3cleaned-md/  ──(carga manual en Open WebUI)──>  vector_db/
```

Cada departamento tiene su propio árbol de carpetas bajo un directorio base
de datos (`<BASE_DIR>/<Departamento>/`), con las etapas `1raw-docx`,
`2converted-md`, `3cleaned-md` y `backups` (esta última existe en disco pero
ningún script del repo escribe en ella — probablemente un respaldo manual).

## 2.1 Etapa 1 — `convert.sh <Departamento>`

Convierte cada `.docx` de `1raw-docx/` (recursivo, incluye subcarpetas) a
Markdown usando **Pandoc**, con:

- Filtro Lua embebido que **elimina todas las imágenes** del documento
  (`Image(_) → {}`) y los párrafos/`Plain` vacíos que Pandoc a veces genera
  al remover contenido.
- `--to=markdown-header_attributes --wrap=none --markdown-headings=atx`
  para headings estilo `#` y sin wrap de línea forzado.
- Post-procesado con `sed` para eliminar bloques `` ```{=html} ``` `` HTML
  crudos residuales y líneas sueltas de `&nbsp;`.
- Escritura atómica: convierte a un archivo temporal (`mktemp`) y solo
  hace `mv` al destino si Pandoc terminó sin error — evita dejar `.md`
  corruptos a medias si falla la conversión.
- Reporta al final cuántos archivos se convirtieron y cuántos fallaron;
  sale con código de error si hubo al menos un fallo.

**Nota:** el filtro Lua descarta imágenes por completo — no las convierte a
texto alternativo. Es la etapa 2 (`clean.py`) la que se encarga de convertir
las referencias de imagen restantes (si las hay, de una corrida anterior u
otro flujo) en notas de texto tipo `[Imagen: <alt>]`. Si el objetivo es
"toda imagen se documenta como texto", revisar si conviene mover esa lógica
a la etapa 1, ya que hoy la etapa 1 elimina la imagen antes de que la etapa
2 pueda leer su alt-text.

## 2.2 Etapa 2 — `clean.py <Departamento>`

Limpieza semántica del Markdown ya convertido, pensada específicamente para
plantillas corporativas de procedimientos/formatos (tienen tablas de
firmas, historial de revisiones, etc. que son ruido para un sistema RAG).
Pipeline de 14 pasos aplicado a cada archivo, en orden:

1. Elimina bloques HTML vacíos residuales de Word.
2. Quita spans de atributos de Pandoc (`[texto]{.clase}`).
3. Elimina **tablas grid boilerplate**: detecta tablas con bordes
   `+---+---+` y las descarta si contienen palabras clave como
   `HISTORIAL DE REVISIONES`, `ELABORÓ`, `REVISÓ`, `AUTORIZÓ`,
   `RESPONSABLE SANITARIO` (encabezados corporativos y bloques de firma).
4. Elimina el encabezado de historial de revisiones si aparece al inicio
   del documento (primeras 25 líneas).
5. Reemplaza referencias de imagen restantes por `[Imagen: <alt>]` o
   `[Imagen]`, limpiando ruido típico de alt-text generado
   automáticamente ("Descripción generada automáticamente", "con confianza
   baja/media", etc.).
6. Convierte **tablas "simple style"** de Pandoc (con separadores de
   guiones, no bordes `+`) a texto plano legible tipo
   `[Categoría] Campo: valor | Campo2: valor2`, reconstruyendo columnas
   por posición de carácter.
7. Corrige **"fake headings"**: párrafos que Word marcaba con estilo
   "Título" y Pandoc convirtió en `#`/`##` pero que en realidad son texto
   de instrucción largo (>60 caracteres) o empiezan con verbos de
   procedimiento ("Deberá", "Se…", "Realizará"…) — se regresan a párrafo
   normal para no ensuciar la jerarquía de headings del documento.
8. Aplana listas con indentación excesiva (≥8 espacios → 4 espacios).
9. Quita IDs de heading estilo Pandoc (`{#id}`).
10. Convierte blockquotes (`>`) a párrafo normal.
11. Quita escapes innecesarios de Markdown que agrega Pandoc
    (`\*`, `\_`, `\[`, etc.).
12. Normaliza viñetas manuales (`•`) a `-`.
13. Limpia líneas de separadores residuales y líneas con solo puntuación.
14. Colapsa espacios finales y más de 2 saltos de línea consecutivos.

Al final, antepone un título `# <nombre-de-archivo>` derivado del nombre del
`.md` (si el texto no empieza ya con ese título).

> ⚠️ **Hallazgo:** el archivo `clean.py` tiene **todo su cuerpo duplicado
> literalmente** (funciones, constantes y `main()` aparecen dos veces
> seguidas en el mismo archivo). No rompe la ejecución porque Python solo
> conserva la última definición de cada función/nombre, pero es ruido de
> mantenimiento — probablemente un artefacto de un copy-paste o merge
> accidental. Vale la pena limpiarlo.

## 2.3 Ingesta al RAG (Etapa 3 → vector_db)

**No existe un script de ingesta/embeddings en el repo.** Cada volumen de
Open WebUI departamental tiene su propia carpeta `vector_db/`, lo que
indica que la carga de los `.md` limpios a la base de conocimiento se hace
**manualmente desde la UI de Open WebUI** (función "Knowledge" / subir
documentos), departamento por departamento. Open WebUI se encarga
internamente del chunking y embeddings en ese paso — no es un proceso
propio de Solomia.

Esto significa que el pipeline de `docu-rag` es una etapa de
**preprocesamiento offline**, desacoplada de la ingesta real: no hay
automatización que tome `3cleaned-md/` y lo suba solo al `vector_db/`
correspondiente.

## 2.4 Aislamiento por departamento

Cada departamento tiene:
- Su propio árbol `1raw-docx → 2converted-md → 3cleaned-md` en disco.
- Su propio contenedor Open WebUI.
- Su propio `vector_db/` — **no hay un índice compartido entre
  departamentos**, lo que es consistente con la necesidad de que, por
  ejemplo, RH no exponga sus documentos al asistente de Ventas.

Una excepción notable: existe una carpeta de datos para **TI** en el mismo
árbol de departamentos (con sus propias etapas del pipeline), pero **no
hay un contenedor Open WebUI dedicado a TI** en `docker-compose.yml` — ver
detalle en el documento de decisiones técnicas.
