---
name: md-to-gdoc
description: >
  Build a styled .docx from a Markdown file (with Mermaid diagrams) and upload it to the
  user's Google Drive as a native Google Doc. Use when the user asks to publish, upload,
  or update a doc in Google Docs, or types "/md-to-gdoc".
---

# md-to-gdoc

1. Rebuild the PDF first so the user has a local copy: `bash scripts/pdf/md-to-pdf.sh <input.md>`.
2. Build and upload, from the repository root:

```
bash scripts/docx/md-to-docx.sh --gdrive gdrive: <input.md> <scratch-dir>/<fixed-name>.docx
```

Rules (see CLAUDE.md for the reasons):

- Use the **same output filename every time** for a given document, ending in `.docx`, so
  the existing Google Doc is updated in place. Look it up with `rclone lsf gdrive:` if unsure.
- Never run `rclone link`. To give the user the doc's URL, read the file ID with
  `rclone lsf gdrive: --format "ip"` and build
  `https://docs.google.com/document/d/<id>/edit`.
- Report what the build printed (diagram count, header rows styled, any images shrunk) and
  say plainly that you did not see the Google rendering. Do not commit until the user has
  reviewed it.
