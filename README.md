# markdown-to-gdoc

Write Markdown with Mermaid diagrams. Get a PDF to review locally and a native Google Doc
in your Google Drive.

```
bash scripts/pdf/md-to-pdf.sh docs/tutorial.md
bash scripts/docx/md-to-docx.sh --gdrive gdrive: docs/tutorial.md /tmp/markdown-to-google-doc-tutorial.docx
```

Start with **[docs/tutorial.md](docs/tutorial.md)**: it covers installing the tools
(Arch Linux and Ubuntu), connecting Google Drive with rclone, writing the Markdown, the two
build scripts, styling, troubleshooting, and how to check the result. The tutorial is built
with these scripts, so building it is also the smoke test.

Layout: `scripts/pdf/`, `scripts/docx/` (with `docx-style/`), `docs/`, and `CLAUDE.md` plus
`.claude/skills/` for working with Claude Code.
