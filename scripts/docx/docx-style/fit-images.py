#!/usr/bin/env python3
"""Cap the height of every image in a .docx, keeping its proportions.

pandoc scales an image to the page width, so a tall, narrow diagram (for example a
top-to-bottom flowchart) can come out many inches taller than the page. Word and Google
Docs then clip it or push it onto a page of its own. This shrinks any image taller than
MAX_HEIGHT_IN so it fits on a page.

Usage: fit-images.py <file.docx> [max-height-inches]   (default 6.0)
"""
import sys, zipfile, shutil, tempfile
from lxml import etree

EMU_PER_IN = 914400
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"wp": WP, "a": A}

path = sys.argv[1]
max_emu = int(float(sys.argv[2] if len(sys.argv) > 2 else 6.0) * EMU_PER_IN)

with zipfile.ZipFile(path) as z:
    infos = z.infolist()
    items = {i.filename: z.read(i.filename) for i in infos}
doc = etree.fromstring(items["word/document.xml"])

n = 0
for drawing in doc.xpath("//wp:inline | //wp:anchor", namespaces=NS):
    ext = drawing.find("wp:extent", NS)
    cx, cy = int(ext.get("cx")), int(ext.get("cy"))
    if cy <= max_emu:
        continue
    k = max_emu / cy
    new_cx, new_cy = int(cx * k), int(cy * k)
    ext.set("cx", str(new_cx)); ext.set("cy", str(new_cy))
    for pic_ext in drawing.xpath(".//a:xfrm/a:ext", namespaces=NS):
        pic_ext.set("cx", str(new_cx)); pic_ext.set("cy", str(new_cy))
    n += 1
    print(f"  shrank an image from {cx/EMU_PER_IN:.1f}x{cy/EMU_PER_IN:.1f} in "
          f"to {new_cx/EMU_PER_IN:.1f}x{new_cy/EMU_PER_IN:.1f} in")

items["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
tmp = tempfile.mktemp(suffix=".docx")
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
    for i in infos:
        out.writestr(i, items[i.filename])
shutil.move(tmp, path)
print(f"fit-images: {n} image(s) capped at {max_emu/EMU_PER_IN:.1f} in tall")
