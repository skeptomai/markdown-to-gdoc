---
name: md-to-pdf
description: >
  Convert a Markdown file (with Mermaid diagrams) to PDF. Use when the user asks to
  convert a doc to PDF, generate a PDF, or types "/md-to-pdf". Renders Mermaid blocks as
  PNG images, then runs pandoc and LuaLaTeX. Output lands next to the source by default.
---

# md-to-pdf

Run from the repository root, passing the Markdown path the user specified:

```
bash scripts/pdf/md-to-pdf.sh <input.md> [output.pdf]
```

Report the output path and the size from the script's last line. Relay any warnings
briefly. If the user did not name a file, use the Markdown file being discussed, and
confirm only if it is genuinely ambiguous.
