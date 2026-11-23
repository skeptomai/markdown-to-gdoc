#!/usr/bin/env python3
"""Make table header rows self-contained: explicit black fill + white bold text on
every header cell. The Table style gets this from a conditional firstRow rule, which
Word honours but Google Docs' importer does not (it keeps the fill and drops the white
text, giving black on black). Usage: inline-table-headers.py <file.docx>"""
import sys, zipfile, shutil, tempfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
q = lambda t: f"{{{W}}}{t}"
BLACK = "000000"

path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    infos = z.infolist()
    items = {i.filename: z.read(i.filename) for i in infos}
doc = etree.fromstring(items["word/document.xml"])

def child(parent, tag, before=()):
    el = parent.find(f"w:{tag}", NS)
    if el is None:
        el = etree.Element(q(tag))
        idx = len(parent)
        for i, c in enumerate(parent):
            if etree.QName(c).localname in before:
                idx = i
                break
        parent.insert(idx, el)
    return el

n = 0
for tr in doc.xpath("//w:tr[w:trPr/w:tblHeader]", namespaces=NS):
    for tc in tr.findall("w:tc", NS):
        tcpr = child(tc, "tcPr")
        shd = child(tcpr, "shd", before=("noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark"))
        shd.set(q("val"), "clear"); shd.set(q("color"), "auto"); shd.set(q("fill"), BLACK)
        for r in tc.xpath(".//w:r", namespaces=NS):
            rpr = r.find("w:rPr", NS)
            if rpr is None:
                rpr = etree.Element(q("rPr")); r.insert(0, rpr)
            for tag in ("b", "bCs"):
                if rpr.find(f"w:{tag}", NS) is None:
                    etree.SubElement(rpr, q(tag))
            col = rpr.find("w:color", NS)
            if col is None:
                col = etree.SubElement(rpr, q("color"))
            col.set(q("val"), "FFFFFF")
    n += 1
items["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)

tmp = tempfile.mktemp(suffix=".docx")
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
    for i in infos:
        out.writestr(i, items[i.filename])
shutil.move(tmp, path)
print(f"inlined header styling on {n} table header rows")
