# markdown-to-gdoc

Instructions for AI coding agents working in this repository (Claude Code, Codex and
others). `CLAUDE.md` imports this file, so there is one source of truth: edit this one.

Scripts that turn one Markdown file (with Mermaid diagrams) into a PDF for local review
and a native Google Doc in the user's Google Drive. `docs/tutorial.md` is the full
walkthrough, and it is built with these scripts. If you change a script or its behaviour,
update the tutorial in the same change, rebuild it, and re-upload it.

## Layout

- `.claude/skills/`: Claude Code skills `/md-to-pdf` and `/md-to-gdoc`. Other agents do not
  load them; follow the same commands and rules from this file.
- `scripts/pdf/md-to-pdf.sh <input.md> [output.pdf]`: mmdc diagrams, pandoc, LuaLaTeX.
- `scripts/docx/md-to-docx.sh [--plain] [--gdrive gdrive:] <input.md> [output.docx]`: mmdc
  diagrams, pandoc with the styled template, `fit-images.py`, `inline-table-headers.py`,
  then optionally `rclone copyto` so Drive converts the .docx to a Google Doc.
- `scripts/docx/docx-style/`: `build-reference.py` (Word template; needs python-lxml),
  `diagram-config.json` (Mermaid theme), `fit-images.py`, `inline-table-headers.py`.
  The generated `nvidia-reference.docx` is git-ignored and rebuilt when missing.
- Run commands from the repository root; the scripts locate their helpers relative to
  themselves.

## Rules

- **Never run `rclone link`.** It makes a public share URL. Uploading with `copyto` to the
  user's own `gdrive:` remote is private by default; sharing is always the user's call.
- **Keep the .docx output filename identical on every run, and ending in `.docx`.** rclone
  then updates the existing Google Doc in place. A new name creates a duplicate; a name
  without `.docx` is not converted.
- **Ask before committing or pushing**, and before anything that publishes content outside
  the machine. Show what a rebase touches before doing one.
- **Never shrink images to fit an upload limit.** Fidelity matters. The Drive MCP connector
  is deliberately not used for uploads because it truncates files above a few hundred KB;
  rclone has no such limit.
- **If a tool is missing, ask the user to install it.** Do not silently substitute an
  inferior one.
- **Verify before reporting.** After a build, check the evidence (diagram count, the
  header-row count printed by `inline-table-headers.py`, image sizes). You cannot see Google's
  rendering: say so, and let the user review the Google Doc before anything is committed.
- When giving the user a command to run themselves, make it a single line.

## Authoring gotchas

- Diagrams are fenced code blocks tagged `mermaid`, found by regex, so a document cannot
  show a literal mermaid fence as an example. Quote every label. Draw wide, not tall:
  `flowchart LR` with short labels. A tall top-to-bottom chart scales to page width and
  can end up many inches taller than the page.
- Pipe-table column widths come from the dash counts in the separator row. Narrow columns
  make bold header labels wrap.
- Numbered cross-references in prose ("section 5.6") are hard-coded. Use `{#anchor}` links.
- Google's .docx import drops the table style's conditional header colour; that is why
  `inline-table-headers.py` writes the fill and white text onto each header cell.
- rclone uses a shared Google OAuth client that is being retired during 2026. When uploads
  fail with an auth error, the fix is the user's own client ID (see the tutorial).

## Setup the user must do once

`rclone config create gdrive drive scope=drive.file`, then approve access in the browser.
The `drive.file` scope limits rclone to files it created. Installation notes for Arch and
Ubuntu are in the tutorial.
