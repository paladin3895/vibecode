#!/usr/bin/env python3
"""Extract a chapter of a text-based PDF book into SQLite, export/import translation
batches, and render a layout-faithful HTML preview. Requires PyMuPDF (`pip install pymupdf`).

Subcommands: init-db, chapters, extract, export, import, render, status.
Run with --help for options. Layout heuristics are tuned in CFG for the ESMO book.
"""
import argparse
import glob
import hashlib
import html
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

try:
    import pymupdf
except ImportError:
    sys.exit("PyMuPDF is missing. Install it into the project environment: pip install pymupdf")

ROOT = Path(__file__).resolve().parents[4]
SCHEMA = Path(__file__).with_name("schema.sql")
DICT_FLAGS = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES

CFG = dict(
    title_color=0xB4447A, title_size=19.0, decor_size=38.0, decor_top=70,
    header_y=14, footer_y=800, heading_size=12.0, heading_l2=15.0, small_size=7.6,
    label_size=7.5, caption_max=9.5, caption_gap=35, fullwidth=400, col_split=297.6,
    min_fig=20, fig_pad=6, dpi=200, frame_rgb=(0.94, 0.86, 0.9), frag_gap=7.0,
)
BULLET_RE = re.compile(r"^\s*([•▪■◦]|[–-](?=\s)|\d+[.)](?=\s))\s*")
FIGLABEL_RE = re.compile(r"^Fig(?:ure)?\.?\s*\d+(?:\.\d+)*$", re.I)
TAG_RE = re.compile(r"</?(?:s\d+|sup|sub)>")
LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}


def die(msg):
    sys.exit(f"error: {msg}")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean(text):
    for k, v in LIGATURES.items():
        text = text.replace(k, v)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.replace("\u00ad", "").replace("\xa0", " ")


# ---------------------------------------------------------------- paths / db

def find_pdf(arg):
    if arg:
        p = Path(arg)
        return p if p.is_absolute() else (Path.cwd() / p)
    found = glob.glob(str(ROOT / "upload" / "*.pdf"))
    if len(found) != 1:
        die("pass --pdf (found %d PDFs in upload/)" % len(found))
    return Path(found[0])


def connect(args, must_exist=True):
    db = Path(args.db)
    db = db if db.is_absolute() else ROOT / db
    if must_exist and not db.exists():
        die(f"{db} does not exist. Ask the user to confirm, then run: init-db")
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- chapters

def detect_chapters(doc):
    """A chapter starts on a page with a 20pt accent-coloured title near the top."""
    starts = []
    for i, page in enumerate(doc):
        title, num = [], None
        for b in page.get_text("dict", flags=DICT_FLAGS)["blocks"]:
            if b["type"]:
                continue
            for line in b["lines"]:
                for s in line["spans"]:
                    if s["bbox"][1] > CFG["decor_top"]:
                        continue
                    if s["size"] >= CFG["title_size"] and s["color"] == CFG["title_color"] and s["text"].strip():
                        title.append((round(line["bbox"][1]), s["bbox"][0], s["text"]))
                    elif s["size"] >= CFG["decor_size"] and s["text"].strip().isdigit():
                        num = s["text"].strip()
        if title:
            text = " ".join(t[2] for t in sorted(title))
            starts.append(dict(number=num, title=re.sub(r"\s+", " ", clean(text)).strip(), start=i + 1))
    for n, c in enumerate(starts):
        c["end"] = starts[n + 1]["start"] - 1 if n + 1 < len(starts) else len(doc)
        c["slug"] = slugify(f"{c['number'] or ''} {c['title']}")[:62].strip("-")
    return starts


def pick_chapter(chapters, sel):
    m = re.fullmatch(r"p?(\d+)-(\d+)", sel)
    if m:
        a, b = int(m[1]), int(m[2])
        return dict(number=None, title=f"Pages {a}-{b}", start=a, end=b, slug=f"pages-{a}-{b}")
    hits = [c for c in chapters if c["number"] == sel] or [c for c in chapters if sel.lower() in c["title"].lower()]
    if len(hits) != 1:
        die(f"chapter '{sel}' matched {len(hits)} chapters; run `chapters` and use a number, a unique title word, or pA-B")
    return hits[0]


# ---------------------------------------------------------------- geometry helpers

def order_items(items):
    """Reading order: full-width items split the page; inside a segment left column then right."""
    items = sorted(items, key=lambda i: i["y0"])
    out, seg = [], []

    def flush():
        out.extend(sorted((i for i in seg if i["col"] == 0), key=lambda i: i["y0"]))
        out.extend(sorted((i for i in seg if i["col"] == 1), key=lambda i: i["y0"]))
        seg.clear()

    for it in items:
        if it["col"] == 2:
            flush()
            out.append(it)
        else:
            seg.append(it)
    flush()
    return out


def column_of(rect):
    if rect.width >= CFG["fullwidth"] or (rect.x0 < CFG["col_split"] - 8 and rect.x1 > CFG["col_split"] + 8):
        return 2
    return 0 if (rect.x0 + rect.x1) / 2 < CFG["col_split"] else 1


def fill_info(fill):
    if len(fill) == 1:
        r = g = b = fill[0]
    elif len(fill) == 3:
        r, g, b = fill
    else:
        c, m, y, k = fill
        r, g, b = ((1 - x) * (1 - k) for x in (c, m, y))
    return "#%02x%02x%02x" % tuple(round(v * 255) for v in (r, g, b)), 0.299 * r + 0.587 * g + 0.114 * b, min(r, g, b)


def light_fills(page):
    out = []
    for d in page.get_drawings():
        if not d.get("fill"):
            continue
        r = d["rect"]
        hexc, lum, lo = fill_info(d["fill"])
        if r.width >= 80 and r.width * r.height >= 2500 and lum > 0.55 and lo < 0.985:
            out.append((r, hexc))
    return sorted(out, key=lambda x: x[0].width * x[0].height)


def figure_clusters(page):
    rects = []
    for info in page.get_image_info(xrefs=True):
        r = pymupdf.Rect(info["bbox"]) & page.rect
        if info["xref"] and r.width >= CFG["min_fig"] and r.height >= CFG["min_fig"]:
            rects.append(r)
    merged = True
    while merged:
        merged = False
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                pad = pymupdf.Rect(rects[i].x0 - 6, rects[i].y0 - 6, rects[i].x1 + 6, rects[i].y1 + 6)
                if pad.intersects(rects[j]):
                    rects[i] |= rects.pop(j)
                    merged = True
                    break
            if merged:
                break
    return rects


# ---------------------------------------------------------------- text blocks

def split_groups(lines):
    groups = []
    for line in lines:
        text = clean("".join(s["text"] for s in line["spans"]))
        if BULLET_RE.match(text) or not groups:
            groups.append([line])
        else:
            groups[-1].append(line)
    return groups


def strip_marker(lines):
    """Remove a leading bullet/number from the first line's spans; return the marker or None."""
    first = lines[0]["spans"]
    m = BULLET_RE.match(clean("".join(s["text"] for s in first)))
    if not m:
        return None
    drop = len(m.group(0))
    for s in first:
        text = clean(s["text"])
        cut = min(drop, len(text))
        s["text"], drop = text[cut:], drop - cut
    return m.group(1)


def build_text(lines):
    """Return (html, base_style, span_styles, plain) with <sN> for off-base spans and <sup> for small ones."""
    spans = [s for line in lines for s in line["spans"] if s["text"].strip()]
    chars = Counter()
    sizes = Counter()
    for s in spans:
        chars[(s["font"], s["color"])] += len(s["text"].strip())
        sizes[round(s["size"], 1)] += len(s["text"].strip())
    (bfont, bcolor), _ = chars.most_common(1)[0]
    bsize = sizes.most_common(1)[0][0]
    pieces = []
    for n, line in enumerate(lines):
        for s in line["spans"]:
            text = clean(s["text"])
            if not text:
                continue
            sup = s["size"] < 0.8 * bsize and text.strip() != ""
            pieces.append((text, (s["font"], s["color"]), sup))
        if n + 1 < len(lines):
            prev = "".join(p[0] for p in pieces)
            nxt = clean(lines[n + 1]["spans"][0]["text"]) if lines[n + 1]["spans"] else ""
            hyphen_join = prev.endswith("-") and nxt[:1].islower()
            pieces.append(("" if hyphen_join else " ", (bfont, bcolor), False))
    ids, style_map, out = {}, {}, []
    for text, key, sup in pieces:
        if text.strip() == "":
            out.append(html.escape(text))
            continue
        esc = html.escape(text)
        if sup:
            esc = f"<sup>{esc}</sup>"
        elif key != (bfont, bcolor):
            if key not in ids:
                ids[key] = len(ids) + 1
                style_map[str(ids[key])] = dict(font=key[0], color="#%06x" % key[1])
            esc = f"<s{ids[key]}>{esc}</s{ids[key]}>"
        out.append(esc)
    joined = re.sub(r" {2,}", " ", "".join(out)).strip()
    joined = re.sub(r"</(s\d+|sup)>(\s*)<\1>", r"\2", joined)  # glue adjacent same-style spans
    plain = re.sub(r"\s+", " ", clean("".join(p[0] for p in pieces))).strip()
    base = dict(font=bfont, size=bsize, color="#%06x" % bcolor)
    return joined, base, style_map, plain


def classify(g, fills):
    r = g["rect"]
    base, plain = g["base"], g["plain"]
    size, color = base["size"], int(base["color"][1:], 16)
    fonts = {s["font"] for line in g["lines"] for s in line["spans"] if s["text"].strip()}
    if size >= CFG["decor_size"]:
        return None
    if r.y0 >= CFG["footer_y"] or r.y1 <= CFG["header_y"]:
        return dict(type="footer", translatable=0)
    if size >= CFG["title_size"] and color == CFG["title_color"]:
        return dict(type="chapter_title")
    marker = g.get("marker")
    if size >= CFG["heading_size"]:
        return dict(type="heading", heading_level=2 if size >= CFG["heading_l2"] else 3)
    if size <= CFG["small_size"]:
        return dict(type="footnote")
    if len(g["lines"]) == 1 and size >= 8.5 and all(("Md" in f or "Bd" in f) for f in fonts) and not marker:
        return dict(type="heading", heading_level=3)
    if marker:
        return dict(type="list_item", list_marker=marker)
    cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
    for fr, hexc in fills:
        if fr.x0 - 2 <= cx <= fr.x1 + 2 and fr.y0 - 2 <= cy <= fr.y1 + 2:
            return dict(type="callout", fill=hexc)
    if size >= 9.5 and fonts and all("Roman" in f for f in fonts):
        return dict(type="callout")
    return dict(type="paragraph")


def pinkish(c):
    return c is not None and len(c) == 3 and all(abs(a - b) < 0.04 for a, b in zip(c, CFG["frame_rgb"]))


def darkish(c):
    return c is not None and len(c) == 3 and all(abs(a - b) < 0.04 for a, b in zip(c, (0.137, 0.122, 0.125)))


def line_size(line):
    return max((s["size"] for s in line["spans"] if s["text"].strip()), default=0)


def line_plain(line):
    return re.sub(r"\s+", " ", clean("".join(s["text"] for s in line["spans"]))).strip()


def overlap_x(a, b):
    return max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))


def line_fragments(line):
    """Split a line into fragments at wide horizontal gaps (side-by-side annotations share a PDF line)."""
    frags, cur, last_x1 = [], None, None
    for s in line["spans"]:
        if not s["text"].strip():
            if cur:
                cur["spans"].append(s)
            continue
        r = pymupdf.Rect(s["bbox"])
        if cur is None or r.x0 - last_x1 > CFG["frag_gap"]:
            cur = dict(spans=[], rect=pymupdf.Rect(r))
            frags.append(cur)
        cur["spans"].append(s)
        cur["rect"] |= r
        last_x1 = r.x1
    return frags


def cluster_fragments(frags):
    """Group fragments that are stacked lines of the same text box."""
    parent = list(range(len(frags)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def stacked(a, b):
        gap = b["rect"].y0 - a["rect"].y1
        return -2.0 <= gap <= 3.0 and overlap_x(a["rect"], b["rect"]) >= 0.35 * min(a["rect"].width, b["rect"].width)

    for i, a in enumerate(frags):
        for j, b in enumerate(frags):
            if i != j and stacked(a, b):
                parent[find(i)] = find(j)
    groups = {}
    for i, f in enumerate(frags):
        groups.setdefault(find(i), []).append(f)
    return [sorted(g, key=lambda f: (round(f["rect"].y0), f["rect"].x0)) for g in groups.values()]


def cluster_block(frags, role):
    lines = [dict(spans=f["spans"], bbox=tuple(f["rect"])) for f in frags]
    rect = pymupdf.Rect(frags[0]["rect"])
    for f in frags[1:]:
        rect |= f["rect"]
    html_, base, smap, plain = build_text(lines)
    return dict(type="caption", figure_role=role, align="left" if role == "caption" else "center",
                lines=lines, rect=rect, html=html_, base=base, spans=smap, plain=plain)


def detect_figures(page, lines):
    """Find framed figures (anchored by their 'Fig. N' label), attach titles, annotations and captions,
    and flag the consumed lines. Vector figures are baked into the image as-is."""
    drawings = page.get_drawings()
    imgs = []
    for info in page.get_image_info(xrefs=True):
        r = pymupdf.Rect(info["bbox"]) & page.rect
        if info["xref"] and r.width >= CFG["min_fig"] and r.height >= CFG["min_fig"]:
            imgs.append(r)
    frames = []
    clusters = figure_clusters(page)
    bubbles = [d["rect"] for d in drawings
               if (pinkish(d.get("fill")) or darkish(d.get("fill"))) and 24 <= d["rect"].width <= 200 and 14 <= d["rect"].height <= 140]
    for ln in lines:
        if line_size(ln["line"]) < CFG["label_size"] and FIGLABEL_RE.match(line_plain(ln["line"])):
            c = pymupdf.Point((ln["rect"].x0 + ln["rect"].x1) / 2, (ln["rect"].y0 + ln["rect"].y1) / 2)
            cands = [d["rect"] for d in drawings
                     if (pinkish(d.get("color")) or pinkish(d.get("fill"))) and d["rect"].contains(c)
                     and 100 <= d["rect"].width <= 520 and d["rect"].height >= 50]
            if not cands:  # unframed figure: the label sits just outside its picture
                cands = [cl for cl in clusters if (cl + (-15, -15, 15, 15)).contains(c)]
            if cands:
                ln["used"] = True
                frames.append(dict(frame=max(cands, key=lambda r: r.width * r.height), label=line_plain(ln["line"]), label_ln=ln))
    for cl in clusters:
        if not any(f["frame"].intersects(cl) for f in frames):
            frames.append(dict(frame=cl, label=None))
    figs = []
    for fr in frames:
        F = fr["frame"]
        raster = any(F.intersects(i) for i in imgs)
        zone = pymupdf.Rect(F.x0 - 20, F.y0 - 30, F.x1 + 20, F.y1 + 30)
        cx = (F.x0 + F.x1) / 2
        inside = [ln for ln in lines if not ln["used"] and (ln["rect"] & F).get_area() >= 0.5 * ln["rect"].get_area()]
        cand = [ln for ln in lines if not ln["used"] and ln["rect"].intersects(zone) and 0 < line_size(ln["line"]) <= CFG["caption_max"]
                and len(line_plain(ln["line"])) > 2 and ln["rect"].y0 < CFG["footer_y"]]
        frags = []
        for ln in cand:
            for f in line_fragments(ln["line"]):
                f["src"] = ln
                if f["rect"].intersects(zone):
                    frags.append(f)
        fig = dict(frame=F, label=fr["label"], kind="raster" if raster else "vector", blocks=[], redact=[], extra=[])
        consumed = {id(ln) for ln in inside}
        if raster:
            for cl in cluster_fragments(frags):
                r = pymupdf.Rect(cl[0]["rect"])
                for f in cl[1:]:
                    r |= f["rect"]
                ccx = (r.x0 + r.x1) / 2
                if r.intersects(F + (-3, -3, 3, 3)):
                    in_bubble = any(b.contains(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)) for b in bubbles)
                    centred_top = abs(ccx - cx) <= 0.15 * F.width and r.y0 <= F.y0 + 0.15 * F.height
                    role = "title" if centred_top and not in_bubble else "annotation"
                elif r.y1 <= F.y0 + 2 and F.y0 - r.y1 <= 30 and abs(ccx - cx) <= 0.2 * F.width:
                    role = "title"
                elif r.y0 >= F.y1 - 1 and r.y0 - F.y1 <= 16 and overlap_x(r, F) >= 0.3 * min(r.width, F.width) \
                        and max(f["spans"][0]["size"] for f in cl) <= CFG["small_size"] + 0.6:
                    role = "caption"
                else:
                    continue
                blk = cluster_block(cl, role)
                fig["blocks"].append(blk)
                if role != "caption":
                    fig["redact"].extend(f["rect"] + (0.4, 0.6, -0.4, -0.6) for f in cl)
                consumed |= {id(f["src"]) for f in cl}
        else:
            for cl in cluster_fragments(frags):
                r = pymupdf.Rect(cl[0]["rect"])
                for f in cl[1:]:
                    r |= f["rect"]
                if r.y1 <= F.y0 + 2 and F.y0 - r.y1 <= 30 and abs((r.x0 + r.x1) / 2 - cx) <= 0.2 * F.width:
                    consumed |= {id(f["src"]) for f in cl}
                    fig["extra"].append(r)
        titles = sorted((b for b in fig["blocks"] if b["figure_role"] == "title"), key=lambda b: b["rect"].y0)
        for extra_title in titles[1:]:
            extra_title["figure_role"], extra_title["align"] = "annotation", "center"
        for ln in lines:
            if id(ln) in consumed:
                ln["used"] = True
        R = pymupdf.Rect(F + (-2, -2, 2, 2))
        for blk in fig["blocks"]:
            if blk["figure_role"] == "title":
                R |= blk["rect"] + (-2, -2, 2, 2)
            elif blk["figure_role"] == "annotation":
                c = pymupdf.Point((blk["rect"].x0 + blk["rect"].x1) / 2, (blk["rect"].y0 + blk["rect"].y1) / 2)
                shapes = [b for b in bubbles if b.contains(c)]
                for b in shapes or [blk["rect"] + (-2, -2, 2, 2)]:
                    R |= b + (-1, -1, 1, 1)
        for r in fig["extra"]:
            R |= r + (-2, -2, 2, 2)
        fig["rect"] = R & page.rect
        if raster:
            keep = {id(ln) for ln in inside}
            if fr.get("label_ln"):
                keep.add(id(fr["label_ln"]))
            fig["redact"].extend(ln["rect"] + (0.4, 0.6, -0.4, -0.6) for ln in lines if id(ln) not in keep and ln["rect"].intersects(fig["rect"]))
        figs.append(fig)
    return figs


def extract_page(doc, pdf_page, img_dir, rel_dir):
    page = doc[pdf_page - 1]
    dd = page.get_text("dict", flags=DICT_FLAGS)
    lines = []
    for bi, b in enumerate(dd["blocks"]):
        if b["type"]:
            continue
        for ln in b["lines"]:
            if any(s["text"].strip() for s in ln["spans"]):
                lines.append(dict(line=ln, rect=pymupdf.Rect(ln["bbox"]), bi=bi, used=False))
    figs = detect_figures(page, lines)
    fills = light_fills(page)
    groups = []
    for bi in sorted({ln["bi"] for ln in lines}):
        rest = [ln["line"] for ln in lines if ln["bi"] == bi and not ln["used"]]
        for grp in split_groups(rest):
            rect = pymupdf.Rect(grp[0]["bbox"])
            for ln in grp[1:]:
                rect |= pymupdf.Rect(ln["bbox"])
            marker = strip_marker(grp)
            html_, base, smap, plain = build_text(grp)
            groups.append(dict(lines=grp, rect=rect, html=html_, base=base, spans=smap, plain=plain, marker=marker))
    for f in figs:
        f["col"] = column_of(f["frame"])
        f["y0"] = f["rect"].y0
    fig_rows = order_items(figs)
    blocks, printed = [], None
    for g in groups:
        c = classify(g, fills)
        if c is None:
            continue
        if c["type"] == "footer" and re.fullmatch(r"\d+", g["plain"]):
            printed = g["plain"]
            continue
        g.update(c)
        g["col"] = column_of(g["rect"])
        g["y0"] = g["rect"].y0
        blocks.append(g)
    if all(b["rect"].x0 < CFG["col_split"] + 3 for b in blocks) and not any(f["frame"].x0 > CFG["col_split"] for f in figs):
        for b in blocks:
            b["col"] = 2
        for f in fig_rows:
            f["col"] = 2
    src = page
    if any(f["redact"] for f in fig_rows):
        tmp = pymupdf.open()
        tmp.insert_pdf(doc, from_page=pdf_page - 1, to_page=pdf_page - 1)
        src = tmp[0]
        for f in fig_rows:
            for r in f["redact"]:
                src.add_redact_annot(r, fill=False)
        src.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    for n, f in enumerate(fig_rows, 1):
        name = f"p{pdf_page:03d}-fig{n}.png"
        src.get_pixmap(clip=f["rect"], dpi=CFG["dpi"]).save(img_dir / name)
        f.update(seq=n, file_path=str(rel_dir / name), width=f["rect"].width, height=f["rect"].height)
        for b in f["blocks"]:
            b.update(col=f["col"], y0=b["rect"].y0, figure_seq=n)
            blocks.append(b)
    return blocks, fig_rows, printed


# ---------------------------------------------------------------- commands

def cmd_init(args):
    db = Path(args.db)
    db = db if db.is_absolute() else ROOT / db
    if db.exists():
        die(f"{db} already exists; refusing to modify its schema")
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text())
    conn.close()
    print(f"created {db}")


def cmd_upgrade(args):
    conn = connect(args)
    adds = [
        ("book_figures", "kind", "TEXT NOT NULL DEFAULT 'raster' CHECK (kind IN ('raster', 'vector'))"),
        ("book_figures", "bbox_json", "TEXT"),
        ("book_blocks", "figure_role", "TEXT CHECK (figure_role IN ('title', 'annotation', 'caption'))"),
    ]
    for table, col, ddl in adds:
        if col not in [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
            print(f"added {table}.{col}")
    conn.commit()


def cmd_chapters(args):
    doc = pymupdf.open(find_pdf(args.pdf))
    print(f"{doc.page_count} pages")
    for c in detect_chapters(doc):
        print(f"{c['number'] or '-':>3}  pages {c['start']:>3}-{c['end']:<3}  {c['title']}")


def cmd_extract(args):
    pdf = find_pdf(args.pdf)
    doc = pymupdf.open(pdf)
    ch = pick_chapter(detect_chapters(doc), args.chapter)
    conn = connect(args)
    rel_pdf = str(pdf.relative_to(ROOT)) if pdf.is_relative_to(ROOT) else str(pdf)
    row = conn.execute("SELECT id FROM book_books WHERE source_path=?", (rel_pdf,)).fetchone()
    if row:
        book_id = row["id"]
    else:
        title = (doc.metadata or {}).get("title") or pdf.stem
        book_id = conn.execute(
            "INSERT INTO book_books(title, source_path, source_sha256, page_count) VALUES (?,?,?,?)",
            (title, rel_pdf, sha256(pdf), doc.page_count)).lastrowid
    old = conn.execute("SELECT id FROM book_chapters WHERE book_id=? AND slug=?", (book_id, ch["slug"])).fetchone()
    if old and not args.force:
        die(f"chapter '{ch['slug']}' is already extracted; --force deletes and re-extracts it (ask the user first)")
    carry = {}
    if old:
        cid = old["id"]
        for r in conn.execute(
                "SELECT b.source_html, t.language, t.text_html, t.status, t.model FROM book_translations t "
                "JOIN book_blocks b ON b.id=t.block_id JOIN book_pages p ON p.id=b.page_id WHERE p.chapter_id=?", (cid,)):
            carry[(r[0], r[1])] = (r[2], r[3], r[4])
        pages = [r[0] for r in conn.execute("SELECT id FROM book_pages WHERE chapter_id=?", (cid,))]
        for pid in pages:
            conn.execute("DELETE FROM book_translations WHERE block_id IN (SELECT id FROM book_blocks WHERE page_id=?)", (pid,))
            conn.execute("UPDATE book_blocks SET figure_id=NULL WHERE page_id=?", (pid,))
            conn.execute("DELETE FROM book_blocks WHERE page_id=?", (pid,))
            conn.execute("DELETE FROM book_figures WHERE page_id=?", (pid,))
            conn.execute("DELETE FROM book_pages WHERE id=?", (pid,))
        conn.execute("DELETE FROM book_chapters WHERE id=?", (cid,))
    cid = conn.execute(
        "INSERT INTO book_chapters(book_id, number, slug, title, start_page, end_page) VALUES (?,?,?,?,?,?)",
        (book_id, ch["number"], ch["slug"], ch["title"], ch["start"], ch["end"])).lastrowid
    upload = Path(args.upload_dir)
    upload = upload if upload.is_absolute() else ROOT / upload
    img_dir = upload / ch["slug"]
    img_dir.mkdir(parents=True, exist_ok=True)
    rel_dir = img_dir.relative_to(ROOT) if img_dir.is_relative_to(ROOT) else img_dir
    n_blocks = n_figs = 0
    inserted = []
    for pn in range(ch["start"], ch["end"] + 1):
        blocks, figs, printed = extract_page(doc, pn, img_dir, rel_dir)
        pid = conn.execute("INSERT INTO book_pages(chapter_id, pdf_page, printed_page) VALUES (?,?,?)", (cid, pn, printed)).lastrowid
        fig_ids = {}
        for f in figs:
            fig_ids[f["seq"]] = conn.execute(
                "INSERT INTO book_figures(page_id, seq, file_path, label, kind, bbox_json, col, y0, width_pt, height_pt) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (pid, f["seq"], f["file_path"], f["label"], f["kind"], json.dumps([round(v, 1) for v in f["rect"]]),
                 f["col"], f["y0"], f["width"], f["height"])).lastrowid
        n_figs += len(figs)
        for seq, b in enumerate(order_items(blocks), 1):
            style = dict(base=b["base"], spans=b["spans"], fill=b.get("fill"), align=b.get("align"))
            bid = conn.execute(
                "INSERT INTO book_blocks(page_id, seq, col, y0, type, heading_level, list_marker, figure_id, figure_role,"
                " translatable, source_html, style_json, bbox_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pid, seq, b["col"], b["y0"], b["type"], b.get("heading_level"), b.get("list_marker"),
                 fig_ids.get(b.get("figure_seq")), b.get("figure_role"), b.get("translatable", 1), b["html"],
                 json.dumps(style), json.dumps([round(v, 1) for v in b["rect"]]))).lastrowid
            n_blocks += 1
            if b.get("translatable", 1):
                inserted.append((bid, b["html"]))
    kept = 0
    for bid, src in inserted:
        for (s, lang), (text, status, model) in carry.items():
            if s == src:
                conn.execute("INSERT INTO book_translations(block_id, language, text_html, status, model) VALUES (?,?,?,?,?)",
                             (bid, lang, text, status, model))
                kept += 1
    conn.commit()
    print(f"extracted '{ch['title']}' pages {ch['start']}-{ch['end']}: {n_blocks} blocks, {n_figs} figures -> {rel_dir}")
    if carry:
        print(f"kept {kept} of {len(carry)} translations whose source text is unchanged; run export to translate the rest")


def get_chapter(conn, sel):
    rows = conn.execute("SELECT * FROM book_chapters WHERE number=? OR slug=?", (sel, sel)).fetchall()
    if not rows:
        rows = conn.execute("SELECT * FROM book_chapters WHERE title LIKE ?", (f"%{sel}%",)).fetchall()
    if len(rows) != 1:
        die(f"chapter '{sel}' matched {len(rows)} extracted chapters")
    return rows[0]


def batch_dir(args, ch):
    upload = Path(args.upload_dir)
    upload = upload if upload.is_absolute() else ROOT / upload
    d = upload / ch["slug"] / "translations" / args.lang
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_export(args):
    conn = connect(args)
    ch = get_chapter(conn, args.chapter)
    sql = ("SELECT b.id, b.type, p.pdf_page, b.source_html FROM book_blocks b JOIN book_pages p ON p.id=b.page_id "
           "WHERE p.chapter_id=? AND b.translatable=1 ")
    if not args.all:
        sql += "AND NOT EXISTS (SELECT 1 FROM book_translations t WHERE t.block_id=b.id AND t.language=?) "
    sql += "ORDER BY p.pdf_page, b.seq"
    rows = conn.execute(sql, (ch["id"],) if args.all else (ch["id"], args.lang)).fetchall()
    glossary = [dict(term_en=g["term_en"], term=g["term"], abbr_en=g["abbr_en"], abbr=g["abbr"])
                for g in conn.execute("SELECT * FROM book_glossary WHERE language=? ORDER BY term_en", (args.lang,))]
    d = batch_dir(args, ch)
    for old in d.glob("source-*.json"):
        if not old.with_name(old.name.replace("source-", "translated-")).exists():
            old.unlink()
    used = [int(p.stem.split("-")[1]) for p in d.glob("*-[0-9][0-9][0-9].json")]
    offset = max(used, default=0)
    for n in range(0, len(rows), args.size):
        units = [dict(key=f"block:{r['id']}", page=r["pdf_page"], type=r["type"], source=r["source_html"])
                 for r in rows[n:n + args.size]]
        payload = dict(chapter=ch["title"], language=args.lang, glossary=glossary, units=units)
        (d / f"source-{offset + n // args.size + 1:03d}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"{len(rows)} blocks to translate -> {d} ({-(-len(rows) // args.size)} batches)")


def cmd_import(args):
    conn = connect(args)
    ch = get_chapter(conn, args.chapter)
    d = batch_dir(args, ch)
    files = [f for f in sorted(d.glob("translated-*.json")) if f.with_name(f.name.replace("translated-", "source-")).exists()]
    if not files:
        die(f"no translated-NNN.json with a matching source-NNN.json in {d}")
    src = {}
    for f in d.glob("source-*.json"):
        for u in json.loads(f.read_text())["units"]:
            src[u["key"]] = u["source"]
    ok = 0
    for f in files:
        data = json.loads(f.read_text())
        for g in data.get("glossary", []):
            conn.execute(
                "INSERT INTO book_glossary(language, term_en, term, abbr_en, abbr) VALUES (?,?,?,?,?) "
                "ON CONFLICT(language, term_en) DO UPDATE SET term=excluded.term, abbr_en=excluded.abbr_en, abbr=excluded.abbr",
                (args.lang, g["term_en"], g["term"], g.get("abbr_en"), g.get("abbr")))
        for t in data["translations"]:
            key, text = t["key"], t["text"].strip()
            if not key.startswith("block:") or not text:
                die(f"{f.name}: bad entry {key!r}")
            if not conn.execute("SELECT 1 FROM book_blocks WHERE id=?", (int(key.split(":")[1]),)).fetchone():
                continue  # batch left over from before a re-extraction
            if key in src and sorted(TAG_RE.findall(text)) != sorted(TAG_RE.findall(src[key])):
                die(f"{f.name}: {key} changes the <sN>/<sup> tags of the source")
            conn.execute(
                "INSERT INTO book_translations(block_id, language, text_html, model) VALUES (?,?,?,?) "
                "ON CONFLICT(block_id, language) DO UPDATE SET text_html=excluded.text_html, status='machine', "
                "model=excluded.model, updated_at=CURRENT_TIMESTAMP",
                (int(key.split(":")[1]), args.lang, text, args.model))
            ok += 1
    left = conn.execute(
        "SELECT COUNT(*) FROM book_blocks b JOIN book_pages p ON p.id=b.page_id WHERE p.chapter_id=? AND b.translatable=1 "
        "AND NOT EXISTS (SELECT 1 FROM book_translations t WHERE t.block_id=b.id AND t.language=?)", (ch["id"], args.lang)).fetchone()[0]
    if left == 0:
        conn.execute("UPDATE book_chapters SET status='translated' WHERE id=? AND status='extracted'", (ch["id"],))
    conn.commit()
    print(f"imported {ok} translations; {left} blocks still untranslated")


def font_css(font):
    weight = 700 if "Bd" in font else 500 if ("Md" in font or "Roman" in font) else 300
    italic = ";font-style:italic" if re.search(r"(It|Obl)\b|O$", font) else ""
    return f"font-weight:{weight}{italic}"


def inline_html(text, style):
    def span(m):
        s = style["spans"].get(m.group(2), {})
        return f"<{'/' if m.group(1) else ''}span" + ("" if m.group(1) else f' style="color:{s.get("color", "inherit")};{font_css(s.get("font", ""))}"') + ">"
    return re.sub(r"<(/?)s(\d+)>", span, text)


CSS = """body{margin:0;background:#eee;font-family:'Helvetica Neue',Helvetica,Arial,'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif;color:#231f20}
.chap{max-width:595pt;margin:16px auto;font-weight:400}
.page{width:595pt;margin:16px auto;background:#fff;padding:36pt 43pt;box-sizing:border-box;position:relative}
.pn{position:absolute;top:4px;right:8px;font-size:9px;color:#999}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:22pt;align-items:start}
p,.li{line-height:1.35;margin:0 0 8pt}.li{padding-left:14pt;text-indent:-14pt}.mk{display:inline-block;width:14pt;text-indent:0}
.callout{padding:8pt 10pt;border-radius:10pt}
h2,h3{margin:12pt 0 4pt}
figure{margin:0 0 8pt}figure img{max-width:100%}figcaption{font-size:8pt;text-align:left;margin-top:3pt}
.figbox{position:relative;container-type:inline-size;margin:0 auto;width:100%}
.figbox img{display:block;width:100%;height:auto}
.ann.t{transform:translate(-50%,-100%)}
.ann{position:absolute;transform:translateX(-50%);text-align:center;line-height:1.12;font-weight:300;letter-spacing:-.01em;
 font-family:'Helvetica Neue Condensed','Arial Narrow','Liberation Sans Narrow',Arial,'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif}
.foot{border-top:2px solid #93406d;margin-top:18pt;padding-top:4pt;font-size:8pt;text-align:right;font-style:italic}
.untranslated{outline:1px dashed #d33}
"""


def block_html(b, text, accent="#93406d"):
    style = json.loads(b["style_json"])
    base = style["base"]
    css = f"color:{base['color']};font-size:{base['size']}pt;{font_css(base['font'])}"
    body = inline_html(text, style)
    t = b["type"]
    if t == "chapter_title":
        return f'<h1 class="chap" style="{css}">{body}</h1>'
    if t == "heading":
        return f'<h{b["heading_level"]} style="{css}">{body}</h{b["heading_level"]}>'
    if t == "list_item":
        return f'<p class="li" style="{css}"><span class="mk" style="color:{accent}">{html.escape(b["list_marker"] or "")}</span>{body}</p>'
    if t == "callout":
        bg = f"background:{style['fill']};" if style.get("fill") else ""
        return f'<p class="callout" style="{bg}{css}">{body}</p>'
    if t == "footer":
        return f'<div class="foot">{body}</div>'
    return f'<p style="{css}">{body}</p>'


def figure_html(fig, blocks, tr):
    """Image with titles/annotations overlaid at their original positions; captions go below."""
    name = html.escape(Path(fig["file_path"]).name)
    box = json.loads(fig["bbox_json"]) if fig["bbox_json"] else None
    overlay, below = [], []
    for b in sorted(blocks, key=lambda b: b["y0"]):
        style = json.loads(b["style_json"])
        text = inline_html(tr.get(b["id"], b["source_html"]), style)
        if box and b["figure_role"] in ("title", "annotation"):
            x0, y0, x1, y1 = json.loads(b["bbox_json"])
            w, h = box[2] - box[0], box[3] - box[1]
            base = style["base"]
            cx = ((x0 + x1) / 2 - box[0]) / w * 100
            is_title = b["figure_role"] == "title"
            ww = (0.96 * w if is_title else max((x1 - x0) * 1.4, 50)) / w * 100
            ww = min(ww, 2 * min(cx, 100 - cx))
            top = ((y1 if is_title else y0) - box[1]) / h * 100
            overlay.append(
                f'<div class="ann{" t" if is_title else ""}" style="left:{cx:.2f}%;top:{top:.2f}%;'
                f'width:{ww:.2f}%;font-size:{base["size"] / w * 100:.3f}cqw;color:{base["color"]}">{text}</div>')
        else:
            below.append(f'<div>{text}</div>')
    width = f' style="max-width:{box[2] - box[0]:.1f}pt"' if box else ""
    cap = f'<figcaption>{"".join(below)}</figcaption>' if below else ""
    return f'<figure><div class="figbox"{width}><img src="{name}" alt="{html.escape(fig["label"] or "")}">{"".join(overlay)}</div>{cap}</figure>'


def cmd_render(args):
    conn = connect(args)
    ch = get_chapter(conn, args.chapter)
    upload = Path(args.upload_dir)
    upload = upload if upload.is_absolute() else ROOT / upload
    out_dir = upload / ch["slug"]
    tr = {r["block_id"]: r["text_html"] for r in conn.execute(
        "SELECT t.block_id, t.text_html FROM book_translations t JOIN book_blocks b ON b.id=t.block_id "
        "JOIN book_pages p ON p.id=b.page_id WHERE p.chapter_id=? AND t.language=? AND t.status!='rejected'",
        (ch["id"], args.lang or ""))}
    parts = []
    for pg in conn.execute("SELECT * FROM book_pages WHERE chapter_id=? ORDER BY pdf_page", (ch["id"],)):
        blocks = conn.execute("SELECT * FROM book_blocks WHERE page_id=? ORDER BY seq", (pg["id"],)).fetchall()
        figs = conn.execute("SELECT * FROM book_figures WHERE page_id=? ORDER BY seq", (pg["id"],)).fetchall()
        caps = {}
        items = []
        for b in blocks:
            if b["figure_id"]:
                caps.setdefault(b["figure_id"], []).append(b)
            else:
                items.append(dict(kind="b", row=b, col=b["col"], y0=b["y0"]))
        for f in figs:
            items.append(dict(kind="f", row=f, col=f["col"], y0=f["y0"]))
        cells = []
        for it in order_items(items):
            row = it["row"]
            if it["kind"] == "b":
                text = tr.get(row["id"], row["source_html"])
                h = block_html(row, text)
                if args.lang and row["translatable"] and row["id"] not in tr:
                    h = f'<div class="untranslated">{h}</div>'
            else:
                h = figure_html(row, caps.get(row["id"], []), tr)
            cells.append((it["col"], h))
        body, i = [], 0
        while i < len(cells):
            if cells[i][0] == 2:
                body.append(cells[i][1])
                i += 1
                continue
            cols = ([], [])
            while i < len(cells) and cells[i][0] != 2:
                cols[cells[i][0]].append(cells[i][1])
                i += 1
            body.append(f'<div class="cols"><div>{"".join(cols[0])}</div><div>{"".join(cols[1])}</div></div>')
        label = f"PDF page {pg['pdf_page']}" + (f" / printed {pg['printed_page']}" if pg["printed_page"] else "")
        parts.append(f'<section class="page"><div class="pn">{label}</div>{"".join(body)}</section>')
    name = f"preview.{args.lang}.html" if args.lang else "preview.html"
    lang_attr = args.lang or "en"
    title = html.escape(ch["title"])
    ct = conn.execute("SELECT b.id FROM book_blocks b JOIN book_pages p ON p.id=b.page_id WHERE p.chapter_id=? AND b.type='chapter_title'", (ch["id"],)).fetchone()
    if ct and ct["id"] in tr:
        title = re.sub(r"<[^>]+>", "", tr[ct["id"]])
    (out_dir / name).write_text(
        f'<!doctype html><html lang="{lang_attr}"><meta charset="utf-8"><title>{title}</title>'
        f"<style>{CSS}</style>{''.join(parts)}</html>")
    print(f"wrote {out_dir / name}")


def cmd_status(args):
    conn = connect(args)
    for c in conn.execute("SELECT * FROM book_chapters ORDER BY book_id, start_page"):
        n = conn.execute("SELECT COUNT(*) FROM book_blocks b JOIN book_pages p ON p.id=b.page_id WHERE p.chapter_id=? AND b.translatable=1", (c["id"],)).fetchone()[0]
        langs = conn.execute(
            "SELECT t.language, COUNT(*) n, SUM(t.status='reviewed') r FROM book_translations t JOIN book_blocks b ON b.id=t.block_id "
            "JOIN book_pages p ON p.id=b.page_id WHERE p.chapter_id=? GROUP BY t.language", (c["id"],)).fetchall()
        info = ", ".join(f"{l['language']} {l['n']}/{n} (reviewed {l['r']})" for l in langs) or "no translations"
        print(f"{c['number'] or '-':>3} {c['slug']} [{c['status']}] pages {c['start_page']}-{c['end_page']}: {n} blocks; {info}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="database/books.db")
    ap.add_argument("--pdf")
    ap.add_argument("--upload-dir", default="upload/book")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db").set_defaults(fn=cmd_init)
    sub.add_parser("upgrade-db", help="add columns introduced by newer versions (additive only)").set_defaults(fn=cmd_upgrade)
    sub.add_parser("chapters").set_defaults(fn=cmd_chapters)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("extract")
    p.add_argument("chapter", help="chapter number, unique title word, or pA-B page range")
    p.add_argument("--force", action="store_true", help="delete and re-extract an existing chapter")
    p.set_defaults(fn=cmd_extract)
    p = sub.add_parser("export")
    p.add_argument("chapter")
    p.add_argument("--lang", required=True)
    p.add_argument("--size", type=int, default=40)
    p.add_argument("--all", action="store_true", help="include blocks that already have a translation")
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser("import")
    p.add_argument("chapter")
    p.add_argument("--lang", required=True)
    p.add_argument("--model", default="agent")
    p.set_defaults(fn=cmd_import)
    p = sub.add_parser("render")
    p.add_argument("chapter")
    p.add_argument("--lang", help="omit to render the original")
    p.set_defaults(fn=cmd_render)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
