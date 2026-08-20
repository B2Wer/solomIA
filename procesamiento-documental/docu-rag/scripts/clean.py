#!/usr/bin/env python3
from importlib.resources import files
import re
import sys
from pathlib import Path


BASE_DIR = Path("/mnt/data/solomia")

if len(sys.argv) < 2:
    print("Uso: python clean.py <departamento>")
    print("Ejemplo: python clean.py Calidad")
    sys.exit(1)

depto = sys.argv[1]
INPUT_DIR = BASE_DIR / depto / "2converted-md"
OUTPUT_DIR = BASE_DIR / depto / "3cleaned-md"

BOILERPLATE_TABLE_WORDS = (
    "HISTORIAL DE REVISIONES",
    "ELABORÓ", "ELABORO",
    "REVISÓ", "REVISO",
    "AUTORIZÓ", "AUTORIZO",
    "RESPONSABLE SANITARIO",
)

AUTO_ALT_NOISE = (
    "Descripción generada automáticamente",
    "descripcion generada automaticamente",
    "con confianza baja",
    "con confianza media",
    "El contenido generado por IA puede ser incorrecto.",
    "El contenido generado por IA puede ser incorrecto",
)

FAKE_HEADING_PREFIXES = re.compile(
    r"^(Deberá|Velará|Será|Podrá|Se |No |Solo |Los |Las |Ningún|Recibirá|"
    r"Conformará|Programará|Realizará|Asegurará|Guardará|Suspenderá|"
    r"Instruirá|Verificará|Instalará|Restringirá|Definirá|Establecerá|"
    r"Llevará|Tendrá|Aplica|Todos los|El )",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Tablas grid (boilerplate: encabezados, firmas)
# ---------------------------------------------------------------------------

def is_grid_border(line):
    return bool(re.match(r"^\s*\+(?:[-=]+\+)+\s*$", line))

def is_grid_row(line):
    return bool(re.match(r"^\s*\|.*\|\s*$", line))

def table_is_boilerplate(block):
    plain = re.sub(r"[*_`\[\]{}#.]", "", "\n".join(block)).upper()
    return any(word in plain for word in BOILERPLATE_TABLE_WORDS)

def remove_boilerplate_grid_tables(text):
    lines = text.splitlines()
    output = []
    index = 0
    while index < len(lines):
        if is_grid_border(lines[index]):
            end = index
            block = []
            while end < len(lines) and (
                is_grid_border(lines[end]) or is_grid_row(lines[end]) or not lines[end].strip()
            ):
                block.append(lines[end])
                end += 1
                if (
                    block and not block[-1].strip()
                    and end < len(lines)
                    and not (is_grid_border(lines[end]) or is_grid_row(lines[end]))
                ):
                    break
            if any(is_grid_row(line) for line in block) and table_is_boilerplate(block):
                index = end
                continue
        output.append(lines[index])
        index += 1
    return "\n".join(output)


# ---------------------------------------------------------------------------
# Tablas simple-style (guiones) → texto plano legible
# Formato Pandoc:
#   "  ----long----"           <- borde superior
#   "  HEADER1  HEADER2"      <- cabeceras
#   "  ------  --------"      <- separador de columnas (define anchos)
#   "  datos   datos"         <- filas
#   "  ----long----"           <- borde inferior
# ---------------------------------------------------------------------------

def convert_simple_tables_to_text(text):
    lines = text.splitlines()
    output = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detectar borde superior: 2+ espacios + 30+ guiones sin espacios internos
        if re.match(r'^\s{2,}-{30,}\s*$', line):
            # Verificar que las siguientes líneas forman una tabla válida
            if i + 3 >= len(lines):
                output.append(line)
                i += 1
                continue

            header_line = lines[i + 1]
            col_sep_line = lines[i + 2]

            # Validar separador de columnas (grupos de guiones separados por espacios)
            if not re.match(r'^\s{2,}(-+\s+)+-+\s*$', col_sep_line):
                output.append(line)
                i += 1
                continue

            # Calcular spans de columnas desde el separador
            col_spans = []
            for m in re.finditer(r'-+', col_sep_line):
                col_spans.append((m.start(), m.end()))

            if len(col_spans) < 2:
                output.append(line)
                i += 1
                continue

            def extract_cols(row_line, spans):
                cols = []
                for idx, (start, end) in enumerate(spans):
                    next_start = spans[idx + 1][0] if idx + 1 < len(spans) else len(row_line)
                    seg = row_line[start:next_start] if start < len(row_line) else ''
                    cols.append(seg.strip())
                return cols

            headers = extract_cols(header_line, col_spans)
            headers = [re.sub(r'\*+', '', h).strip() for h in headers]

            # Recoger filas hasta el borde inferior
            data_rows = []
            j = i + 3
            while j < len(lines):
                dline = lines[j]
                if re.match(r'^\s{2,}-{30,}\s*$', dline):
                    j += 1
                    break
                data_rows.append(dline if dline.strip() else None)
                j += 1

            # Convertir a texto plano
            output.append("")
            current_category = ""
            current_parts = []

            def flush(parts, category):
                if not parts:
                    return
                prefix = f"[{category}] " if category else ""
                output.append(prefix + " | ".join(parts))

            for dline in data_rows:
                if dline is None:
                    flush(current_parts, current_category)
                    current_parts = []
                    continue

                cols = extract_cols(dline, col_spans)
                cols = [re.sub(r'\*+', '', c).strip() for c in cols]

                if cols and cols[0]:
                    current_category = cols[0]

                parts = []
                for idx, (h, v) in enumerate(zip(headers, cols)):
                    if idx == 0:
                        continue
                    if v:
                        parts.append(f"{h}: {v}" if h else v)
                current_parts.extend(parts)

            flush(current_parts, current_category)
            output.append("")
            i = j
            continue

        output.append(line)
        i += 1

    return "\n".join(output)


# ---------------------------------------------------------------------------
# Headings falsos (párrafos Word con estilo Título) → párrafo normal
# ---------------------------------------------------------------------------

def fix_fake_headings(text):
    lines = text.splitlines()
    output = []
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            content = m.group(2).strip()
            content_plain = re.sub(r'\*\*([^*]+)\*\*', r'\1', content).strip()
            if len(content_plain) > 60 or bool(FAKE_HEADING_PREFIXES.match(content_plain)):
                output.append(content)
                continue
        output.append(line)
    return "\n".join(output)


# ---------------------------------------------------------------------------
# Listas con indentación excesiva → aplanar a máximo 4 espacios
# ---------------------------------------------------------------------------

def flatten_deep_lists(text):
    lines = text.splitlines()
    output = []
    for line in lines:
        m = re.match(r'^(\s+)(\d+\.\s+|-\s+)(.*)', line)
        if m:
            indent = m.group(1)
            marker = m.group(2)
            content = m.group(3)
            new_indent = "    " if len(indent) >= 8 else indent
            output.append(f"{new_indent}{marker}{content}")
        else:
            output.append(line)
    return "\n".join(output)


# ---------------------------------------------------------------------------
# Helpers restantes
# ---------------------------------------------------------------------------

def strip_pandoc_span_attrs(text):
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\[([^\[\]\n]+)\]\{[^}\n]*\}", r"\1", text)
    return text

def remove_leading_revision_header(text):
    lines = text.splitlines()
    end = -1
    for index, line in enumerate(lines[:25]):
        upper = line.upper()
        if (
            "HISTORIAL DE REVISIONES" in upper
            or "CAMBIOS DEL DOCUMENTO" in upper
            or re.match(r"^\s*-{5,}\s*$", line)
        ):
            end = index
    if end < 0:
        return text
    while end + 1 < len(lines) and not lines[end + 1].strip():
        end += 1
    return "\n".join(lines[end + 1:])

def clean_alt_text(alt_text):
    alt_text = alt_text.strip()
    for noise in AUTO_ALT_NOISE:
        alt_text = alt_text.replace(noise, "")
    alt_text = re.sub(r"\s+", " ", alt_text)
    return alt_text.strip(" ,.;:-")

def replace_images_with_notes(text):
    image_re = re.compile(r"!\[([^\]]*)\]\((?:\./)?media/[^)]+\)(?:\{[^}\n]*\})?")
    def replace(match):
        alt_text = clean_alt_text(match.group(1))
        return f"[Imagen: {alt_text}]" if alt_text else "[Imagen]"
    return image_re.sub(replace, text)

def add_document_title(text, title):
    title = title.strip()
    text = text.strip()
    if not title:
        return text + ("\n" if text else "")
    if text.startswith(f"# {title}"):
        return text + "\n"
    if not text:
        return f"# {title}\n"
    return f"# {title}\n\n{text}\n"


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def limpiar(text, title=None):
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Bloques HTML vacíos de Word
    text = re.sub(
        r"^\s*```\{=html\}\s*\n.*?^\s*```\s*$",
        "", text, flags=re.DOTALL | re.MULTILINE,
    )

    # 2. Spans de Pandoc [{.mark} etc.]
    text = strip_pandoc_span_attrs(text)

    # 3. Tablas grid boilerplate (encabezado corporativo, firmas)
    text = remove_boilerplate_grid_tables(text)

    # 4. Historial de revisiones al inicio
    text = remove_leading_revision_header(text)

    # 5. Referencias de imagen → nota de texto
    text = replace_images_with_notes(text)

    # 6. Tablas simple-style (guiones) → texto plano semántico
    text = convert_simple_tables_to_text(text)

    # 7. Headings falsos → párrafo normal
    text = fix_fake_headings(text)

    # 8. Listas con indentación excesiva → aplanar
    text = flatten_deep_lists(text)

    # 9. IDs de Pandoc en headings
    text = re.sub(r"(?m)^(#{1,6}\s.*?)\s*\{#[^}\n]+\}\s*$", r"\1", text)
    text = re.sub(r"(?m)^#\s*\{#[^}\n]+\}\s*$", "", text)
    text = re.sub(r"(?m)(?<=\S)\s+\{[#.][^}\n]+\}\s*$", "", text)

    # 10. Blockquotes → párrafo
    text = re.sub(r"(?m)^\s*>\s?", "", text)

    # 11. Escapes innecesarios de Pandoc
    text = re.sub(r"\\([`*_{}\[\]()#+\-.!>@])", r"\1", text)

    # 12. Viñetas manuales
    text = re.sub(r"(?m)^\s*•\s+", "- ", text)

    # 13. Líneas de formato residuales
    text = re.sub(r"(?m)^\s*-{5,}\s*$", "", text)
    text = re.sub(r"(?m)^\s*\\?-{3,}\s*$", "", text)
    text = re.sub(r"(?m)^\s*[.,;:]\s*$", "", text)

    # 14. Espacios finales y líneas en blanco múltiples
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if title:
        return add_document_title(text, title)
    return text + ("\n" if text else "")


def main():
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"No existe la carpeta de entrada: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(INPUT_DIR.rglob("*.md"))
    if not files:
        print("No hay archivos .md en 2converted-md/")
        return

    import re
import sys
from pathlib import Path


BASE_DIR = Path("/mnt/data/solomia")

if len(sys.argv) < 2:
    print("Uso: python clean.py <departamento>")
    print("Ejemplo: python clean.py Calidad")
    sys.exit(1)

depto = sys.argv[1]
INPUT_DIR = BASE_DIR / depto / "2converted-md"
OUTPUT_DIR = BASE_DIR / depto / "3cleaned-md"

BOILERPLATE_TABLE_WORDS = (
    "HISTORIAL DE REVISIONES",
    "ELABORÓ", "ELABORO",
    "REVISÓ", "REVISO",
    "AUTORIZÓ", "AUTORIZO",
    "RESPONSABLE SANITARIO",
)

AUTO_ALT_NOISE = (
    "Descripción generada automáticamente",
    "descripcion generada automaticamente",
    "con confianza baja",
    "con confianza media",
    "El contenido generado por IA puede ser incorrecto.",
    "El contenido generado por IA puede ser incorrecto",
)

FAKE_HEADING_PREFIXES = re.compile(
    r"^(Deberá|Velará|Será|Podrá|Se |No |Solo |Los |Las |Ningún|Recibirá|"
    r"Conformará|Programará|Realizará|Asegurará|Guardará|Suspenderá|"
    r"Instruirá|Verificará|Instalará|Restringirá|Definirá|Establecerá|"
    r"Llevará|Tendrá|Aplica|Todos los|El )",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Tablas grid (boilerplate: encabezados, firmas)
# ---------------------------------------------------------------------------

def is_grid_border(line):
    return bool(re.match(r"^\s*\+(?:[-=]+\+)+\s*$", line))

def is_grid_row(line):
    return bool(re.match(r"^\s*\|.*\|\s*$", line))

def table_is_boilerplate(block):
    plain = re.sub(r"[*_`\[\]{}#.]", "", "\n".join(block)).upper()
    return any(word in plain for word in BOILERPLATE_TABLE_WORDS)

def remove_boilerplate_grid_tables(text):
    lines = text.splitlines()
    output = []
    index = 0
    while index < len(lines):
        if is_grid_border(lines[index]):
            end = index
            block = []
            while end < len(lines) and (
                is_grid_border(lines[end]) or is_grid_row(lines[end]) or not lines[end].strip()
            ):
                block.append(lines[end])
                end += 1
                if (
                    block and not block[-1].strip()
                    and end < len(lines)
                    and not (is_grid_border(lines[end]) or is_grid_row(lines[end]))
                ):
                    break
            if any(is_grid_row(line) for line in block) and table_is_boilerplate(block):
                index = end
                continue
        output.append(lines[index])
        index += 1
    return "\n".join(output)


# ---------------------------------------------------------------------------
# Tablas simple-style (guiones) → texto plano legible
# Formato Pandoc:
#   "  ----long----"           <- borde superior
#   "  HEADER1  HEADER2"      <- cabeceras
#   "  ------  --------"      <- separador de columnas (define anchos)
#   "  datos   datos"         <- filas
#   "  ----long----"           <- borde inferior
# ---------------------------------------------------------------------------

def convert_simple_tables_to_text(text):
    lines = text.splitlines()
    output = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detectar borde superior: 2+ espacios + 30+ guiones sin espacios internos
        if re.match(r'^\s{2,}-{30,}\s*$', line):
            # Verificar que las siguientes líneas forman una tabla válida
            if i + 3 >= len(lines):
                output.append(line)
                i += 1
                continue

            header_line = lines[i + 1]
            col_sep_line = lines[i + 2]

            # Validar separador de columnas (grupos de guiones separados por espacios)
            if not re.match(r'^\s{2,}(-+\s+)+-+\s*$', col_sep_line):
                output.append(line)
                i += 1
                continue

            # Calcular spans de columnas desde el separador
            col_spans = []
            for m in re.finditer(r'-+', col_sep_line):
                col_spans.append((m.start(), m.end()))

            if len(col_spans) < 2:
                output.append(line)
                i += 1
                continue

            def extract_cols(row_line, spans):
                cols = []
                for idx, (start, end) in enumerate(spans):
                    next_start = spans[idx + 1][0] if idx + 1 < len(spans) else len(row_line)
                    seg = row_line[start:next_start] if start < len(row_line) else ''
                    cols.append(seg.strip())
                return cols

            headers = extract_cols(header_line, col_spans)
            headers = [re.sub(r'\*+', '', h).strip() for h in headers]

            # Recoger filas hasta el borde inferior
            data_rows = []
            j = i + 3
            while j < len(lines):
                dline = lines[j]
                if re.match(r'^\s{2,}-{30,}\s*$', dline):
                    j += 1
                    break
                data_rows.append(dline if dline.strip() else None)
                j += 1

            # Convertir a texto plano
            output.append("")
            current_category = ""
            current_parts = []

            def flush(parts, category):
                if not parts:
                    return
                prefix = f"[{category}] " if category else ""
                output.append(prefix + " | ".join(parts))

            for dline in data_rows:
                if dline is None:
                    flush(current_parts, current_category)
                    current_parts = []
                    continue

                cols = extract_cols(dline, col_spans)
                cols = [re.sub(r'\*+', '', c).strip() for c in cols]

                if cols and cols[0]:
                    current_category = cols[0]

                parts = []
                for idx, (h, v) in enumerate(zip(headers, cols)):
                    if idx == 0:
                        continue
                    if v:
                        parts.append(f"{h}: {v}" if h else v)
                current_parts.extend(parts)

            flush(current_parts, current_category)
            output.append("")
            i = j
            continue

        output.append(line)
        i += 1

    return "\n".join(output)


# ---------------------------------------------------------------------------
# Headings falsos (párrafos Word con estilo Título) → párrafo normal
# ---------------------------------------------------------------------------

def fix_fake_headings(text):
    lines = text.splitlines()
    output = []
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            content = m.group(2).strip()
            content_plain = re.sub(r'\*\*([^*]+)\*\*', r'\1', content).strip()
            if len(content_plain) > 60 or bool(FAKE_HEADING_PREFIXES.match(content_plain)):
                output.append(content)
                continue
        output.append(line)
    return "\n".join(output)


# ---------------------------------------------------------------------------
# Listas con indentación excesiva → aplanar a máximo 4 espacios
# ---------------------------------------------------------------------------

def flatten_deep_lists(text):
    lines = text.splitlines()
    output = []
    for line in lines:
        m = re.match(r'^(\s+)(\d+\.\s+|-\s+)(.*)', line)
        if m:
            indent = m.group(1)
            marker = m.group(2)
            content = m.group(3)
            new_indent = "    " if len(indent) >= 8 else indent
            output.append(f"{new_indent}{marker}{content}")
        else:
            output.append(line)
    return "\n".join(output)


# ---------------------------------------------------------------------------
# Helpers restantes
# ---------------------------------------------------------------------------

def strip_pandoc_span_attrs(text):
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\[([^\[\]\n]+)\]\{[^}\n]*\}", r"\1", text)
    return text

def remove_leading_revision_header(text):
    lines = text.splitlines()
    end = -1
    for index, line in enumerate(lines[:25]):
        upper = line.upper()
        if (
            "HISTORIAL DE REVISIONES" in upper
            or "CAMBIOS DEL DOCUMENTO" in upper
            or re.match(r"^\s*-{5,}\s*$", line)
        ):
            end = index
    if end < 0:
        return text
    while end + 1 < len(lines) and not lines[end + 1].strip():
        end += 1
    return "\n".join(lines[end + 1:])

def clean_alt_text(alt_text):
    alt_text = alt_text.strip()
    for noise in AUTO_ALT_NOISE:
        alt_text = alt_text.replace(noise, "")
    alt_text = re.sub(r"\s+", " ", alt_text)
    return alt_text.strip(" ,.;:-")

def replace_images_with_notes(text):
    image_re = re.compile(r"!\[([^\]]*)\]\((?:\./)?media/[^)]+\)(?:\{[^}\n]*\})?")
    def replace(match):
        alt_text = clean_alt_text(match.group(1))
        return f"[Imagen: {alt_text}]" if alt_text else "[Imagen]"
    return image_re.sub(replace, text)

def add_document_title(text, title):
    title = title.strip()
    text = text.strip()
    if not title:
        return text + ("\n" if text else "")
    if text.startswith(f"# {title}"):
        return text + "\n"
    if not text:
        return f"# {title}\n"
    return f"# {title}\n\n{text}\n"


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def limpiar(text, title=None):
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Bloques HTML vacíos de Word
    text = re.sub(
        r"^\s*```\{=html\}\s*\n.*?^\s*```\s*$",
        "", text, flags=re.DOTALL | re.MULTILINE,
    )

    # 2. Spans de Pandoc [{.mark} etc.]
    text = strip_pandoc_span_attrs(text)

    # 3. Tablas grid boilerplate (encabezado corporativo, firmas)
    text = remove_boilerplate_grid_tables(text)

    # 4. Historial de revisiones al inicio
    text = remove_leading_revision_header(text)

    # 5. Referencias de imagen → nota de texto
    text = replace_images_with_notes(text)

    # 6. Tablas simple-style (guiones) → texto plano semántico
    text = convert_simple_tables_to_text(text)

    # 7. Headings falsos → párrafo normal
    text = fix_fake_headings(text)

    # 8. Listas con indentación excesiva → aplanar
    text = flatten_deep_lists(text)

    # 9. IDs de Pandoc en headings
    text = re.sub(r"(?m)^(#{1,6}\s.*?)\s*\{#[^}\n]+\}\s*$", r"\1", text)
    text = re.sub(r"(?m)^#\s*\{#[^}\n]+\}\s*$", "", text)
    text = re.sub(r"(?m)(?<=\S)\s+\{[#.][^}\n]+\}\s*$", "", text)

    # 10. Blockquotes → párrafo
    text = re.sub(r"(?m)^\s*>\s?", "", text)

    # 11. Escapes innecesarios de Pandoc
    text = re.sub(r"\\([`*_{}\[\]()#+\-.!>@])", r"\1", text)

    # 12. Viñetas manuales
    text = re.sub(r"(?m)^\s*•\s+", "- ", text)

    # 13. Líneas de formato residuales
    text = re.sub(r"(?m)^\s*-{5,}\s*$", "", text)
    text = re.sub(r"(?m)^\s*\\?-{3,}\s*$", "", text)
    text = re.sub(r"(?m)^\s*[.,;:]\s*$", "", text)

    # 14. Espacios finales y líneas en blanco múltiples
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if title:
        return add_document_title(text, title)
    return text + ("\n" if text else "")


def main():
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"No existe la carpeta de entrada: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(INPUT_DIR.rglob("*.md"))
    if not files:
        print("No hay archivos .md en 2converted-md/")
        return

    for path in files:
        rel_path = path.relative_to(INPUT_DIR)
        text = path.read_text(encoding="utf-8")
        clean_text = limpiar(text, title=path.stem)
        output_path = OUTPUT_DIR / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(clean_text, encoding="utf-8")
        print(f"Limpio: {rel_path}")

    print("--- Limpieza completa ---")


if __name__ == "__main__":
    main()

    print("--- Limpieza completa ---")


if __name__ == "__main__":
    main()