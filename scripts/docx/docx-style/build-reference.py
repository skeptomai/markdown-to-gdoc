#!/usr/bin/env python3
"""Build nvidia-reference.docx: a pandoc --reference-doc styled after NVIDIA docs.

Starts from pandoc's own default reference.docx and rewrites styles.xml, adds a footer
and sets page geometry. Requires python-lxml (every fragment and part is parsed, so a
malformed edit fails loudly instead of producing a broken template).

Palette (NVIDIA green is #76B900; the rest follows nvidia.com's black/white/gray look):
  green 76B900 · black 000000 · near-black 1A1A1A · grays 3F3F3F 5E5E5E 757575 A7A7A7

Font: NVIDIA Sans is proprietary (EULA), so body text is Arial, which is also the
fallback in NVIDIA's own stylesheets. Code is Roboto Mono (available in Google Docs).

Usage: build-reference.py [output.docx]   (default: nvidia-reference.docx beside this file)
"""
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

GREEN, BLACK, INK = "76B900", "000000", "1A1A1A"
G3, G5, G7, GA = "3F3F3F", "5E5E5E", "757575", "A7A7A7"
BODY, MONO = "Arial", "Roboto Mono"


def rfonts(font):
    return f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>'


def pstyle(sid, name, based="Normal", nxt=None, ppr="", rpr="", ui=None):
    return (
        f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/>'
        + (f'<w:basedOn w:val="{based}"/>' if based else "")
        + (f'<w:next w:val="{nxt}"/>' if nxt else "")
        + (f'<w:uiPriority w:val="{ui}"/>' if ui else "")
        + f"<w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>"
    )


def cstyle(sid, name, rpr, based="DefaultParagraphFont"):
    return (
        f'<w:style w:type="character" w:styleId="{sid}"><w:name w:val="{name}"/>'
        f'<w:basedOn w:val="{based}"/><w:qFormat/><w:rPr>{rpr}</w:rPr></w:style>'
    )


STYLES = {
    "Normal": (
        f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
        f'<w:qFormat/><w:rPr>{rfonts(BODY)}<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>'
    ),
    "BodyText": pstyle("BodyText", "Body Text", "Normal", "BodyText",
                       '<w:spacing w:before="80" w:after="120" w:line="300" w:lineRule="auto"/>'),
    "FirstParagraph": pstyle("FirstParagraph", "First Paragraph", "BodyText", "BodyText"),
    "Compact": pstyle("Compact", "Compact", "BodyText", None,
                      '<w:spacing w:before="20" w:after="20" w:line="260" w:lineRule="auto"/>',
                      '<w:sz w:val="20"/><w:szCs w:val="20"/>'),
    # Title block: white page, large bold black title, gray subtitle, green rule under the date
    "Title": pstyle("Title", "Title", "Normal", "Subtitle",
                    '<w:keepNext/><w:spacing w:before="240" w:after="80" w:line="240" w:lineRule="auto"/>',
                    f'<w:b/><w:color w:val="{BLACK}"/><w:sz w:val="60"/><w:szCs w:val="60"/>', 10),
    "Subtitle": pstyle("Subtitle", "Subtitle", "Normal", "Date",
                       '<w:keepNext/><w:spacing w:before="0" w:after="60" w:line="240" w:lineRule="auto"/>',
                       f'<w:b/><w:color w:val="{G3}"/><w:sz w:val="32"/><w:szCs w:val="32"/>', 11),
    "Author": pstyle("Author", "Author", "Normal", "Date",
                     '<w:keepNext/><w:spacing w:before="0" w:after="0"/>',
                     f'<w:color w:val="{G7}"/><w:sz w:val="22"/>'),
    "Date": pstyle("Date", "Date", "Normal", "BodyText",
                   f'<w:pBdr><w:bottom w:val="single" w:sz="36" w:space="10" w:color="{GREEN}"/></w:pBdr>'
                   '<w:spacing w:before="0" w:after="360"/>',
                   f'<w:color w:val="{G7}"/><w:sz w:val="22"/><w:szCs w:val="22"/>'),
    # Headings: green rule under H1, green bar left of H2
    "Heading1": pstyle(
        "Heading1", "heading 1", "Normal", "BodyText",
        '<w:keepNext/><w:keepLines/>'
        f'<w:pBdr><w:bottom w:val="single" w:sz="18" w:space="4" w:color="{GREEN}"/></w:pBdr>'
        '<w:spacing w:before="480" w:after="200" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="0"/>',
        f'<w:b/><w:color w:val="{BLACK}"/><w:sz w:val="44"/><w:szCs w:val="44"/>', 9),
    "Heading2": pstyle(
        "Heading2", "heading 2", "Normal", "BodyText",
        '<w:keepNext/><w:keepLines/>'
        f'<w:pBdr><w:left w:val="single" w:sz="36" w:space="8" w:color="{GREEN}"/></w:pBdr>'
        '<w:spacing w:before="360" w:after="120" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:left="200"/><w:outlineLvl w:val="1"/>',
        f'<w:b/><w:color w:val="{BLACK}"/><w:sz w:val="32"/><w:szCs w:val="32"/>', 9),
    "Heading3": pstyle(
        "Heading3", "heading 3", "Normal", "BodyText",
        '<w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="80"/><w:outlineLvl w:val="2"/>',
        f'<w:b/><w:color w:val="{G3}"/><w:sz w:val="26"/><w:szCs w:val="26"/>', 9),
    "Heading4": pstyle(
        "Heading4", "heading 4", "Normal", "BodyText",
        '<w:keepNext/><w:keepLines/><w:spacing w:before="200" w:after="60"/><w:outlineLvl w:val="3"/>',
        f'<w:b/><w:color w:val="{G5}"/><w:sz w:val="22"/><w:szCs w:val="22"/>', 9),
    "TOCHeading": pstyle(
        "TOCHeading", "TOC Heading", "Normal", "BodyText",
        '<w:keepNext/>' + f'<w:pBdr><w:bottom w:val="single" w:sz="18" w:space="4" w:color="{GREEN}"/></w:pBdr>'
        '<w:spacing w:before="240" w:after="160"/>',
        f'<w:b/><w:color w:val="{BLACK}"/><w:sz w:val="36"/><w:szCs w:val="36"/>', 39),
    "TOC1": pstyle("TOC1", "toc 1", "Normal", "BodyText",
                   '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9350"/></w:tabs><w:spacing w:before="80" w:after="20"/>',
                   '<w:b/><w:sz w:val="21"/>', 39),
    "TOC2": pstyle("TOC2", "toc 2", "Normal", "BodyText",
                   '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9350"/></w:tabs><w:spacing w:before="0" w:after="0"/><w:ind w:left="240"/>',
                   f'<w:color w:val="{G5}"/><w:sz w:val="20"/>', 39),
    "BlockText": pstyle(
        "BlockText", "Block Text", "BodyText", "BodyText",
        f'<w:pBdr><w:left w:val="single" w:sz="24" w:space="10" w:color="{GREEN}"/></w:pBdr>'
        '<w:spacing w:before="120" w:after="120"/><w:ind w:left="360"/>',
        f'<w:i/><w:color w:val="{G5}"/>'),
    "FootnoteText": pstyle("FootnoteText", "footnote text", "Normal", None, "",
                           f'<w:color w:val="{G5}"/><w:sz w:val="18"/><w:szCs w:val="18"/>'),
    "Caption": pstyle("Caption", "Caption", "Normal", None,
                      '<w:spacing w:before="60" w:after="200"/><w:jc w:val="center"/>',
                      f'<w:i/><w:color w:val="{G5}"/><w:sz w:val="18"/><w:szCs w:val="18"/>'),
    "ImageCaption": pstyle("ImageCaption", "Image Caption", "Caption", None),
    "TableCaption": pstyle("TableCaption", "Table Caption", "Caption", None),
    "Figure": pstyle("Figure", "Figure", "Normal", None, '<w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/>'),
    "CaptionedFigure": pstyle("CaptionedFigure", "Captioned Figure", "Figure", None, "<w:keepNext/>"),
    # Character styles
    "VerbatimChar": cstyle("VerbatimChar", "Verbatim Char",
                           f'{rfonts(MONO)}<w:color w:val="{INK}"/><w:sz w:val="19"/><w:szCs w:val="19"/>'
                           '<w:shd w:val="clear" w:color="auto" w:fill="F0F0F0"/>'),
    "SectionNumber": cstyle("SectionNumber", "Section Number", f'<w:color w:val="{BLACK}"/>'),
    "Hyperlink": cstyle("Hyperlink", "Hyperlink",
                        f'<w:color w:val="{BLACK}"/><w:u w:val="single" w:color="{GREEN}"/>'),
    # Table: black header row with white bold text, light gray rules, subtle banding
    "Table": (
        '<w:style w:type="table" w:default="1" w:styleId="Table"><w:name w:val="Table"/>'
        '<w:uiPriority w:val="59"/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/>'
        f'<w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="{BLACK}"/>'
        f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="{BLACK}"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="D0D0D0"/></w:tblBorders>'
        '<w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:left w:w="110" w:type="dxa"/>'
        '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="110" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:color w:val="FFFFFF"/></w:rPr>'
        f'<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="{BLACK}"/></w:tcPr></w:tblStylePr>'
        '<w:tblStylePr w:type="band2Horz"><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="F6F6F6"/></w:tcPr></w:tblStylePr>'
        '</w:style>'
    ),
}

# Styles that pandoc's default lacks entirely: appended before </w:styles>.
APPEND_IF_MISSING = ("TOC1", "TOC2")

FOOTER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:p><w:pPr><w:pBdr>'
    f'<w:top w:val="single" w:sz="12" w:space="6" w:color="{GREEN}"/></w:pBdr>'
    '<w:tabs><w:tab w:val="right" w:pos="9360"/></w:tabs><w:spacing w:before="0" w:after="0"/></w:pPr>'
    f'<w:r><w:rPr><w:color w:val="{G7}"/><w:sz w:val="18"/></w:rPr><w:tab/></w:r>'
    f'<w:r><w:rPr><w:color w:val="{G7}"/><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve">Page </w:t></w:r>'
    f'<w:r><w:rPr><w:b/><w:color w:val="{BLACK}"/><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
    f'<w:r><w:rPr><w:b/><w:color w:val="{BLACK}"/><w:sz w:val="18"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
    f'<w:r><w:rPr><w:b/><w:color w:val="{BLACK}"/><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="separate"/></w:r>'
    f'<w:r><w:rPr><w:b/><w:color w:val="{BLACK}"/><w:sz w:val="18"/></w:rPr><w:t>1</w:t></w:r>'
    f'<w:r><w:rPr><w:b/><w:color w:val="{BLACK}"/><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>'
    '</w:p></w:ftr>'
)

SECTPR = (
    '<w:sectPr><w:footerReference w:type="default" r:id="rIdNvFooter1"/>'
    '<w:footnotePr><w:numRestart w:val="eachSect"/></w:footnotePr>'
    '<w:pgSz w:w="12240" w:h="15840"/>'
    '<w:pgMar w:top="1300" w:right="1440" w:bottom="1300" w:left="1440" w:header="720" w:footer="600" w:gutter="0"/>'
    '</w:sectPr>'
)


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}


def q(tag):
    return "{%s}%s" % (W, tag)


def frag(xml):
    """Parse one XML fragment that uses the w: and r: prefixes."""
    return etree.fromstring(f'<root xmlns:w="{W}" xmlns:r="{R}">{xml}</root>')[0]


def load(parts, name):
    return etree.fromstring(parts[name])


def dump(root):
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("nvidia-reference.docx")
    base = subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                          check=True, capture_output=True).stdout
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "base.docx"
        path.write_bytes(base)
        with zipfile.ZipFile(path) as z:
            parts = {n: z.read(n) for n in z.namelist()}

    # styles.xml: document defaults, then replace (or append) each style by id
    styles = load(parts, "word/styles.xml")
    for rf in styles.xpath("w:docDefaults/w:rPrDefault/w:rPr/w:rFonts", namespaces=NS):
        for a in list(rf.attrib):
            del rf.attrib[a]
        for a in ("ascii", "hAnsi", "cs", "eastAsia"):
            rf.set(q(a), BODY)
    for tag in ("sz", "szCs"):
        for el in styles.xpath(f"w:docDefaults/w:rPrDefault/w:rPr/w:{tag}", namespaces=NS):
            el.set(q("val"), "22")
    # Default text color goes here, not in Normal: a paragraph-style color would override
    # the white header text of the table style.
    rpr = styles.xpath("w:docDefaults/w:rPrDefault/w:rPr", namespaces=NS)[0]
    color = etree.SubElement(rpr, q("color"))
    color.set(q("val"), INK)
    rpr.insert(list(rpr).index(rpr.xpath("w:rFonts", namespaces=NS)[0]) + 1, color)
    for sid, xml in STYLES.items():
        new = frag(xml)
        old = styles.xpath(f'w:style[@w:styleId="{sid}"]', namespaces=NS)
        if old:
            styles.replace(old[0], new)
        else:
            styles.append(new)
    parts["word/styles.xml"] = dump(styles)

    # document.xml: page geometry and footer reference
    doc = load(parts, "word/document.xml")
    sect = doc.xpath("//w:sectPr", namespaces=NS)
    assert len(sect) == 1, "expected one sectPr in default reference.docx"
    sect[0].getparent().replace(sect[0], frag(SECTPR))
    parts["word/document.xml"] = dump(doc)

    # footer part, its relationship and content type
    parts["word/footer1.xml"] = dump(etree.fromstring(FOOTER.encode()))
    rels = load(parts, "word/_rels/document.xml.rels")
    rels.append(etree.fromstring(
        f'<Relationship xmlns="http://schemas.openxmlformats.org/package/2006/relationships" '
        f'Id="rIdNvFooter1" Type="{R}/footer" Target="footer1.xml"/>'))
    parts["word/_rels/document.xml.rels"] = dump(rels)
    ct = load(parts, "[Content_Types].xml")
    ct.append(etree.fromstring(
        '<Override xmlns="http://schemas.openxmlformats.org/package/2006/content-types" '
        'PartName="/word/footer1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'))
    parts["[Content_Types].xml"] = dump(ct)

    # every XML part must parse, and every pStyle used by the styles must exist
    for name, data in parts.items():
        if name.endswith((".xml", ".rels")):
            etree.fromstring(data)
    ids = set(styles.xpath("w:style/@w:styleId", namespaces=NS))
    for ref in styles.xpath("w:style/w:basedOn/@w:val | w:style/w:next/@w:val", namespaces=NS):
        assert ref in ids, f"style refers to missing style {ref!r}"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", parts.pop("[Content_Types].xml"))
        for name, data in parts.items():
            z.writestr(name, data)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
