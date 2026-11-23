#!/usr/bin/env bash
# Convert a Markdown file with Mermaid diagrams to .docx (importable as a Google Doc).
#
# Usage: md-to-docx.sh [--plain] [--gdrive REMOTE:] <input.md> [output.docx]
#
#   (default)         NVIDIA-docs styling: docx-style/nvidia-reference.docx (white title
#                     block with a green rule, green heading rules, black table headers,
#                     Arial/Roboto Mono; NVIDIA Sans is proprietary so it is not used) and a matching mermaid theme.
#                     The template is rebuilt from docx-style/build-reference.py if missing.
#   --plain           pandoc's default template and mermaid's default theme instead.
#
#   --gdrive REMOTE:  also upload to Google Drive via rclone and convert to a native
#                     Google Doc (e.g. --gdrive gdrive:). Full-size images, no size cap.
#                     The Drive MCP connector cannot be used for this: its create_file
#                     rejects or truncates binary uploads above a few hundred KB.
#                     One-time setup: sudo pacman -S rclone;
#                       rclone config create gdrive drive scope=drive.file
#
# Same diagram handling as md-to-pdf.sh: mermaid blocks become PNGs (mmdc) embedded
# as images. Pandoc writes the .docx directly; no LibreOffice needed. LaTeX in the
# front matter (header-includes, \newpage) is ignored by the docx writer.
# Requires: pandoc, mmdc (mermaid-cli), python3 + python-lxml; rclone for --gdrive.
# Post-processing (docx-style/): fit-images.py caps image height, inline-table-headers.py
# makes table headers survive Google's import.
# Optional: libreoffice (soffice) to render the .docx to PDF for visual checks.
set -euo pipefail

GDRIVE=""
PLAIN=0
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --gdrive) GDRIVE="${2:?--gdrive needs a remote, e.g. gdrive:}"; shift 2 ;;
        --plain) PLAIN=1; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done
STYLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docx-style"
REFDOC="$STYLE_DIR/nvidia-reference.docx"
if [[ $PLAIN -eq 0 && ! -f "$REFDOC" ]]; then
    python3 "$STYLE_DIR/build-reference.py" "$REFDOC"
fi

INPUT="${1:-}"
[[ -n "$INPUT" ]] || { echo "Usage: $0 <input.md> [output.docx]" >&2; exit 1; }
INPUT="$(realpath "$INPUT")"
[[ -f "$INPUT" ]] || { echo "Error: file not found: $INPUT" >&2; exit 1; }
OUTPUT="${2:-${INPUT%.md}.docx}"
OUTPUT="$(realpath -m "$OUTPUT")"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "==> Rendering Mermaid diagrams..."
python3 - "$INPUT" "$TMPDIR" <<'PYEOF'
import re, sys
src = open(sys.argv[1]).read()
tmpdir = sys.argv[2]
diagrams = []
def replace(m):
    idx = len(diagrams)
    diagrams.append(m.group(1))
    return f'![]({tmpdir}/diagram-{idx}.png)'
out = re.sub(r'```mermaid\n(.*?)```', replace, src, flags=re.DOTALL)
for i, code in enumerate(diagrams):
    open(f'{tmpdir}/diagram-{i}.mmd', 'w').write(code)
open(f'{tmpdir}/input.md', 'w').write(out)
print(f'found {len(diagrams)} diagram(s)')
PYEOF

for MMD in "$TMPDIR"/diagram-*.mmd; do
    [[ -f "$MMD" ]] || continue
    MMDC_CFG=()
    [[ $PLAIN -eq 0 ]] && MMDC_CFG=(-c "$STYLE_DIR/diagram-config.json")
    mmdc -i "$MMD" -o "${MMD%.mmd}.png" --width 3200 --scale 3 -q "${MMDC_CFG[@]}"
    echo "    rendered $(basename "${MMD%.mmd}.png")"
done

echo "==> Converting to docx with pandoc..."
PANDOC_REF=()
[[ $PLAIN -eq 0 ]] && PANDOC_REF=(--reference-doc "$REFDOC")
pandoc "$TMPDIR/input.md" -o "$OUTPUT" --from markdown --to docx --number-sections "${PANDOC_REF[@]}"
# Both fixes apply to every build, styled or plain: oversized images hurt either way.
python3 "$STYLE_DIR/fit-images.py" "$OUTPUT"
if [[ $PLAIN -eq 0 ]]; then
    python3 "$STYLE_DIR/inline-table-headers.py" "$OUTPUT"
fi
echo "==> Done: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"

if [[ -n "$GDRIVE" ]]; then
    NAME="$(basename "$OUTPUT")"
    echo "==> Uploading to ${GDRIVE} as a Google Doc..."
    rclone copyto "$OUTPUT" "${GDRIVE}${NAME}" --drive-import-formats docx
    echo "==> Uploaded: ${GDRIVE}${NAME} (converted to a native Google Doc)"
fi
