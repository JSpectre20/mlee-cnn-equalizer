"""Helpers that write the MLEE report into the course template with the template's own formatting.

The template uses direct formatting (Arial everywhere), so every helper here reproduces the exact
paragraph / run / table properties of the template's prototype elements (see
CONTEXT_HANDOFF.md section 0 and the template itself).

Inline markup in text strings:
  **bold**   *italic*   ^{sup}   _{sub}   $latex$ (inline Word equation)   [@key] (citation, IEEE numbered)
  {fig:key} / {tab:key} / {eq:key} (cross-references, numbered in order of definition)
"""
import copy
import re
from pathlib import Path

import docx
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu
from latex2mathml.converter import convert as latex_to_mathml
from lxml import etree

MML2OMML = Path(r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL")
_XSLT = etree.XSLT(etree.parse(str(MML2OMML)))
TEXT_W_CM = 15.92   # 9026 dxa

NAVY, BLUE, LIGHT, PALE = "1F3864", "2E75B6", "D9E2F3", "EAF1FB"


# ----------------------------------------------------------------------------- low level
def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k) if ":" in k else k, str(v))   # unprefixed attributes (e.g. a:ext/@uri) stay unqualified
    return e


def _rpr(size=22, bold=False, italic=False, color=None, vert=None, font="Arial"):
    rpr = _el("w:rPr")
    rpr.append(_el("w:rFonts", **{"w:ascii": font, "w:cs": font, "w:eastAsia": font, "w:hAnsi": font}))
    if bold:
        rpr.append(_el("w:b")); rpr.append(_el("w:bCs"))
    if italic:
        rpr.append(_el("w:i")); rpr.append(_el("w:iCs"))
    if color:
        rpr.append(_el("w:color", **{"w:val": color}))
    rpr.append(_el("w:sz", **{"w:val": size})); rpr.append(_el("w:szCs", **{"w:val": size}))
    if vert:
        rpr.append(_el("w:vertAlign", **{"w:val": vert}))
    return rpr


def _run(text, **fmt):
    r = _el("w:r")
    r.append(_rpr(**fmt))
    parts = text.split("\t")
    for i, part in enumerate(parts):
        if i:
            r.append(_el("w:tab"))
        if part:
            t = _el("w:t"); t.text = part; t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            r.append(t)
    return r


def omml(latex):
    """LaTeX -> MathML (latex2mathml) -> OMML (Office's MML2OMML.XSL) -> <m:oMath> element."""
    mml = latex_to_mathml(latex)
    # MML2OMML drops <mspace>; turn spacing into em-space text, and pad the 'mod' operator
    mml = re.sub(r'<mspace width="2em"\s*/>', "<mtext>  </mtext>", mml)
    mml = re.sub(r'<mspace width="1em"\s*/>', "<mtext> </mtext>", mml)
    mml = re.sub(r'<mspace width="[0-9.]+em"\s*/>', "<mtext> </mtext>", mml)
    mml = mml.replace("<mo>mod</mo>", "<mtext> mod </mtext>")
    tree = _XSLT(etree.fromstring(mml.encode("utf8")))
    root = tree.getroot()
    om = root if root.tag.endswith("}oMath") else root.find(".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath")
    return copy.deepcopy(om)


def _ppr(spacing=None, jc=None, ind=None, keep_next=False, tabs=None, border=None, shd=None, style=None, num=None, keep_lines=False):
    ppr = _el("w:pPr")
    if style:
        ppr.append(_el("w:pStyle", **{"w:val": style}))
    if keep_next:
        ppr.append(_el("w:keepNext"))
    if keep_lines:
        ppr.append(_el("w:keepLines"))
    if num is not None:
        np_ = _el("w:numPr"); np_.append(_el("w:ilvl", **{"w:val": 0})); np_.append(_el("w:numId", **{"w:val": num})); ppr.append(np_)
    if border:
        ppr.append(border)
    if shd:
        ppr.append(_el("w:shd", **{"w:fill": shd, "w:color": "auto", "w:val": "clear"}))
    if tabs:
        tb = _el("w:tabs")
        for kind, pos in tabs:
            tb.append(_el("w:tab", **{"w:val": kind, "w:pos": pos}))
        ppr.append(tb)
    if spacing:
        ppr.append(_el("w:spacing", **{f"w:{k}": v for k, v in spacing.items()}))
    if ind:
        ppr.append(_el("w:ind", **{f"w:{k}": v for k, v in ind.items()}))
    if jc:
        ppr.append(_el("w:jc", **{"w:val": jc}))
    return ppr


TOKEN = re.compile(r"(`[^`]+`|\*\*.+?\*\*|\*[^*\s][^*]*?\*|\^\{[^}]*\}|_\{[^}]*\}|\$[^$]+\$|\[@[\w,\s@-]+\]|\{(?:fig|tab|eq|sec):[\w-]+\})")


# ----------------------------------------------------------------------------- the report
class Report:
    def __init__(self, template, figdir):
        self.doc = docx.Document(template)
        self.body = self.doc.element.body
        self.figdir = Path(figdir)
        self.cites, self.refs = [], {}
        self.labels = {"fig": {}, "tab": {}, "eq": {}}
        self.pending = []      # (run element, kind, key) placeholders for forward references
        self._svg_n = 0
        self.units, self._group = [], None
        els = list(self.body.iterchildren())
        self.title_block = els[:6]
        self.sectPr = els[-1]
        for e in els[6:-1]:
            self.body.remove(e)

    # ---- inline text with markup
    def _inline(self, p, text, size=22, bold=False, italic=False, color=None):
        for tok in TOKEN.split(text):
            if not tok:
                continue
            if tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
                p.append(_run(tok[1:-1], size=size - 1, bold=bold, italic=italic, color=color, font="Consolas"))
            elif tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
                self._inline(p, tok[2:-2], size, True, italic, color)
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2 and not tok.startswith("**"):
                self._inline(p, tok[1:-1], size, bold, True, color)
            elif tok.startswith("^{"):
                p.append(_run(tok[2:-1], size=size, bold=bold, italic=italic, color=color, vert="superscript"))
            elif tok.startswith("_{"):
                p.append(_run(tok[2:-1], size=size, bold=bold, italic=italic, color=color, vert="subscript"))
            elif tok.startswith("$"):
                p.append(omml(tok[1:-1]))
            elif tok.startswith("[@"):
                keys = [k.strip().lstrip("@") for k in tok[2:-1].split(",")]
                nums = []
                for k in keys:
                    if k not in self.cites:
                        self.cites.append(k)
                    nums.append(self.cites.index(k) + 1)
                p.append(_run(self._cite_str(nums), size=size, bold=bold, italic=italic, color=color))
            elif tok.startswith("{"):
                kind, key = tok[1:-1].split(":")
                r = _run("??", size=size, bold=bold, italic=italic, color=color)
                self.pending.append((r, kind, key))
                p.append(r)
            else:
                p.append(_run(tok, size=size, bold=bold, italic=italic, color=color))

    @staticmethod
    def _cite_str(nums):
        nums = sorted(set(nums))
        out, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            out.append(f"{nums[i]}–{nums[j]}" if j - i >= 2 else ", ".join(str(n) for n in nums[i:j + 1]))
            i = j + 1
        return "[" + ", ".join(out) + "]"

    # Layout units: "body" (a paragraph, or a paragraph with its bullet list, that may be moved in front of a float),
    # "float" (figure + caption, or caption + table + note) and "fixed" (headings, equations, lead-ins).
    def _add(self, el):
        self.sectPr.addprevious(el)
        if getattr(self, "_group", None) is not None:
            self._group[1].append(el)
        else:
            self.units.append(["fixed", [el]])
        return el

    def _begin(self, kind):
        if getattr(self, "_group", None) is not None:
            return False                      # nested call (e.g. a table note): stays in the outer unit
        self._group = [kind, []]
        self.units.append(self._group)
        return True

    def _end(self, started):
        if started:
            self._group = None

    def apply_deferrals(self, defer):
        """Move the n body units that follow float k in front of it (defer = {k: n}); returns {k: n actually moved}."""
        done = {}
        floats = [i for i, u in enumerate(self.units) if u[0] == "float"]
        for k, ui in enumerate(floats):
            n = defer.get(k, 0)
            if not n:
                continue
            j, moved = self.units.index(self.units[ui]) + 1, 0
            fl = self.units[self.units.index(self.units[ui])]
            while moved < n and j < len(self.units):
                # a body unit moves alone; a sub-section heading moves together with the body unit that follows it
                if self.units[j][0] == "body":
                    take = 1
                elif moved == 0 and self.units[j][0] == "h2" and j + 1 < len(self.units) and self.units[j + 1][0] == "body":
                    # only when the float ends its sub-section, so it never travels past its own discussion
                    take = 2
                else:
                    break
                for _ in range(take):
                    for el in self.units[j][1]:
                        fl[1][0].addprevious(el)
                    unit = self.units.pop(j)
                    self.units.insert(self.units.index(fl), unit)
                    j = self.units.index(fl) + 1
                moved += 1
            done[k] = moved
        return done

    # ---- block elements (formats copied from the template prototypes)
    def para(self, text, jc="both", after=120, before=None, size=22, keep_next=False, italic=False, color=None, ind=None):
        started = self._begin("leadin" if keep_next else "body")
        sp = {"after": after, "line": 276}
        if before is not None:
            sp["before"] = before
        p = _el("w:p"); p.append(_ppr(spacing=sp, jc=jc, keep_next=keep_next, ind=ind))
        self._inline(p, text, size=size, italic=italic, color=color)
        self._add(p)
        self._end(started)
        return p

    def lead(self, head, text):
        """Body paragraph with a bold run-in heading (used for sub-sub-sections)."""
        return self.para(f"**{head}** {text}")

    def bullets(self, items, num=2):
        # a list belongs to the paragraph that introduces it (body or lead-in): extend that unit; after a heading it is
        # a unit of its own
        if self.units and self.units[-1][0] in ("body", "leadin"):
            self.units[-1][0] = "body"
            self._group = self.units[-1]
        else:
            self._begin("body")
        for it in items:
            p = _el("w:p"); p.append(_ppr(style="ListParagraph", num=num, spacing={"after": 60, "line": 264}, jc="both"))
            self._inline(p, it, size=22)
            self._add(p)
        self._group = None

    def abstract_heading(self):
        p = _el("w:p"); p.append(_ppr(spacing={"after": 80, "before": 120}, keep_next=True))
        p.append(_run("Abstract", size=24, bold=True, color=NAVY))
        return self._add(p)

    def keywords(self, kw):
        p = _el("w:p"); p.append(_ppr(spacing={"after": 200}))
        p.append(_run("Keywords: ", size=20, bold=True))
        p.append(_run(kw, size=20, italic=True))
        return self._add(p)

    def h1(self, text, page_break=False):
        p = _el("w:p"); ppr = _ppr(style="Heading1", keep_next=True)
        if page_break:
            ppr.append(_el("w:pageBreakBefore"))
        p.append(ppr); p.append(_run(text, size=28, bold=True, color=NAVY))
        return self._add(p)

    def h2(self, text):
        started = self._begin("h2")
        p = _el("w:p"); p.append(_ppr(style="Heading2", keep_next=True)); p.append(_run(text, size=24, bold=True, color=BLUE))
        self._add(p)
        self._end(started)
        return p

    def equation(self, latex, key):
        n = len(self.labels["eq"]) + 1
        self.labels["eq"][key] = n
        p = _el("w:p"); p.append(_ppr(tabs=[("center", 4513), ("right", 9026)], spacing={"after": 160, "before": 80}))
        p.append(_run("\t", size=22)); p.append(omml(latex)); p.append(_run(f"\t({n})", size=22))
        return self._add(p)

    def _caption(self, label, text, before=80, after=200, keep_next=False):
        p = _el("w:p"); p.append(_ppr(spacing={"after": after, "before": before}, jc="center", keep_next=keep_next))
        p.append(_run(label, size=19, italic=True, bold=True))
        self._inline(p, text, size=19, italic=True)
        return self._add(p)

    # ---- figures: SVG with a PNG fallback (Word shows the SVG; older readers the PNG)
    def figure(self, stem, key, caption, width_cm=TEXT_W_CM):
        n = len(self.labels["fig"]) + 1
        self.labels["fig"][key] = n
        png, svg = self.figdir / f"{stem}.png", self.figdir / f"{stem}.svg"
        started = self._begin("float")
        p = _el("w:p"); p.append(_ppr(spacing={"after": 0, "before": 120}, jc="center", keep_next=True))
        self._add(p)
        para = docx.text.paragraph.Paragraph(p, self.doc._body)
        para.add_run().add_picture(str(png), width=Cm(width_cm))
        if svg.exists():
            self._attach_svg(p, svg)
        self._caption(f"Figure {n}: ", caption)
        self._end(started)

    def _attach_svg(self, p, svg):
        self._svg_n += 1
        part = Part(PackURI(f"/word/media/svgfig{self._svg_n}.svg"), "image/svg+xml", svg.read_bytes(), self.doc.part.package)
        rid = self.doc.part.relate_to(part, RT.IMAGE)
        blip = p.find(".//" + qn("a:blip"))
        ext_lst = _el("a:extLst")
        ext = _el("a:ext", uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}")
        ns = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
        svgblip = etree.SubElement(ext, f"{{{ns}}}svgBlip", nsmap={"asvg": ns})
        svgblip.set(qn("r:embed"), rid)
        ext_lst.append(ext)
        blip.append(ext_lst)

    # ---- tables (format of the template's Table 1 / Table 2)
    def table(self, key, caption, header, rows, widths, align=None, bold_rows=(), shade_rows=(), size=18, first_col_bold=False,
              note=None):
        started = self._begin("float")
        n = len(self.labels["tab"]) + 1
        self.labels["tab"][key] = n
        self._caption(f"Table {n}: ", caption, after=80, keep_next=True)
        total = sum(widths)
        tbl = _el("w:tbl")
        tp = _el("w:tblPr"); tp.append(_el("w:tblW", **{"w:type": "dxa", "w:w": total})); tp.append(_el("w:jc", **{"w:val": "center"}))
        tp.append(_el("w:tblLayout", **{"w:type": "fixed"}))
        tbl.append(tp)
        grid = _el("w:tblGrid")
        for w in widths:
            grid.append(_el("w:gridCol", **{"w:w": w}))
        tbl.append(grid)
        align = align or ["left"] + ["center"] * (len(widths) - 1)

        keep = len(rows) <= 14   # short tables stay on one page (keepNext on every row but the last)

        def cell(text, w, hdr=False, bold=False, fill=None, jc="left", last=False):
            tc = _el("w:tc"); pr = _el("w:tcPr")
            pr.append(_el("w:tcW", **{"w:type": "dxa", "w:w": w}))
            b = _el("w:tcBorders")
            for side in ("top", "left", "bottom", "right"):
                b.append(_el(f"w:{side}", **{"w:val": "single", "w:color": "A6A6A6", "w:sz": 4}))
            pr.append(b)
            if fill:
                pr.append(_el("w:shd", **{"w:fill": fill, "w:color": "auto", "w:val": "clear"}))
            m = _el("w:tcMar")
            for side, v in (("top", 50), ("left", 90), ("bottom", 50), ("right", 90)):
                m.append(_el(f"w:{side}", **{"w:type": "dxa", "w:w": v}))
            pr.append(m); pr.append(_el("w:vAlign", **{"w:val": "center"}))
            tc.append(pr)
            for line in str(text).split("\n"):
                p = _el("w:p"); p.append(_ppr(jc=jc, spacing={"after": 0, "line": 240}, keep_next=keep and not last))
                self._inline(p, line, size=size, bold=hdr or bold)
                tc.append(p)
            return tc

        tr = _el("w:tr"); trp = _el("w:trPr"); trp.append(_el("w:tblHeader")); trp.append(_el("w:cantSplit")); tr.append(trp)
        for h, w, a in zip(header, widths, align):
            tr.append(cell(h, w, hdr=True, fill=LIGHT, jc=a))
        tbl.append(tr)
        for i, row in enumerate(rows):
            tr = _el("w:tr"); trp = _el("w:trPr"); trp.append(_el("w:cantSplit")); tr.append(trp)
            for j, (v, w, a) in enumerate(zip(row, widths, align)):
                tr.append(cell(v, w, bold=(i in bold_rows) or (first_col_bold and j == 0), fill=PALE if i in shade_rows else None, jc=a,
                               last=i == len(rows) - 1))
            tbl.append(tr)
        self._add(tbl)
        if note:
            self.para(note, jc="left", after=200, size=17, italic=True, before=40)
        else:
            sp = _el("w:p"); sp.append(_ppr(spacing={"after": 120})); self._add(sp)
        self._end(started)

    def page_break(self):
        p = _el("w:p"); r = _el("w:r"); r.append(_el("w:br", **{"w:type": "page"})); p.append(r); self._add(p)

    # ---- references
    def reference_list(self, bib):
        missing = [k for k in self.cites if k not in bib]
        if missing:
            raise KeyError(f"no bibliography entry for {missing}")
        for i, k in enumerate(self.cites, 1):
            p = _el("w:p"); p.append(_ppr(spacing={"after": 80, "line": 264}, ind={"left": 540, "hanging": 540}, jc="left"))
            self._inline(p, f"[{i}]\t{bib[k]}", size=20)
            self._add(p)
        unused = [k for k in bib if k not in self.cites]
        return unused

    # ---- finish: resolve cross-references
    def resolve(self):
        for r, kind, key in self.pending:
            n = self.labels[kind].get(key)
            if n is None:
                raise KeyError(f"undefined reference {kind}:{key}")
            r.find(qn("w:t")).text = {"fig": f"Figure {n}", "tab": f"Table {n}", "eq": f"({n})"}[kind]

    def save(self, path):
        self.resolve()
        self.doc.save(path)
