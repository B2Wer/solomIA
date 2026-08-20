#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="/mnt/data/solomia"

if [ -z "${1:-}" ]; then
    echo "Uso: ./convert.sh <departamento>"
    echo "Ejemplo: ./convert.sh Calidad"
    exit 1
fi

DEPTO="$1"
INPUT_DIR="$BASE_DIR/$DEPTO/1raw-docx"
OUTPUT_DIR="$BASE_DIR/$DEPTO/2converted-md"

mkdir -p "$OUTPUT_DIR"

if ! command -v pandoc >/dev/null 2>&1; then
    echo "Error: pandoc no está instalado o no está en PATH." >&2
    exit 1
fi

filter_file="$(mktemp)"
tmp_output=""
trap 'rm -f "$filter_file" ${tmp_output:+"$tmp_output"}' EXIT

cat > "$filter_file" <<'LUA'
function Image(_)
  return {}
end

function Span(el)
  return el.content
end

function Para(el)
  if #el.content == 0 then
    return {}
  end
end

function Plain(el)
  if #el.content == 0 then
    return {}
  end
end
LUA

mapfile -d '' files < <(find "$INPUT_DIR" -type f -iname "*.docx" -print0)

if [ "${#files[@]}" -eq 0 ]; then
    echo "No hay archivos .docx en 1raw-docx/ (ni subcarpetas)"
    exit 1
fi

converted=0
failed=0

for file in "${files[@]}"; do
    rel_path="${file#$INPUT_DIR/}"
    rel_dir="$(dirname "$rel_path")"
    filename="$(basename "$file")"
    filename="${filename%.*}"

    dest_dir="$OUTPUT_DIR"
    [ "$rel_dir" != "." ] && dest_dir="$OUTPUT_DIR/$rel_dir"
    mkdir -p "$dest_dir"

    output_file="$dest_dir/${filename}.md"
    tmp_output="$(mktemp "$dest_dir/.${filename}.XXXXXX.md")"

###
    if pandoc "$file" \
        --from=docx \
        --to=markdown-header_attributes \
        --wrap=none \
        --markdown-headings=atx \
        --lua-filter="$filter_file" \
        -o "$tmp_output"; then

        sed -i '/^[[:space:]]*```{=html}[[:space:]]*$/,/^[[:space:]]*```[[:space:]]*$/d' "$tmp_output"
        sed -i '/^[[:space:]]*&nbsp;[[:space:]]*$/d' "$tmp_output"
        mv -f "$tmp_output" "$output_file"
        tmp_output=""

        converted=$((converted + 1))
        echo "Convertido: $filename"
    else
        rm -f "$tmp_output"
        tmp_output=""
        failed=$((failed + 1))
        echo "Error al convertir: $filename" >&2
    fi
done

if [ "$failed" -gt 0 ]; then
    echo "--- Conversión incompleta: $converted convertido(s), $failed error(es) ---" >&2
    exit 1
fi

echo "--- Conversión completa: $converted archivo(s) ---"
