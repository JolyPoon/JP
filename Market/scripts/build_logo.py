"""Build the iBitPay logo pack: SVG (all shapes filled, no strokes), PDF, EPS, PNG.

Usage:
    pip install fonttools uharfbuzz cairosvg
    python3 Market/scripts/build_logo.py

Every shape is a filled outline (strokes are converted to capsule paths and the
wordmark is converted from the font), so the files open the same in
Illustrator / Figma / Sketch / CorelDRAW without the fonts installed.
"""
import math
from pathlib import Path

import cairosvg
import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "assets/fonts"
OUT = ROOT / "logo"

INK = "#141413"
IVORY = "#F5F3EC"
CLAY = "#D97757"
BLACK = "#000000"
WHITE = "#FFFFFF"

WORD = "iBitPay"
SANS = FONTS / "Geist-SemiBold.ttf"
SERIF = FONTS / "Newsreader-Display-Medium.ttf"


# ------------------------------------------------------------ geometry ----
def capsule(x0, y0, x1, y1, h):
    """A stroked line with round caps, as a filled outline (half-width h)."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * h, dx / L * h
    f = lambda v: f"{v:.3f}".rstrip("0").rstrip(".")
    return (
        f"M{f(x0 + nx)} {f(y0 + ny)}L{f(x1 + nx)} {f(y1 + ny)}"
        f"A{f(h)} {f(h)} 0 0 0 {f(x1 - nx)} {f(y1 - ny)}"
        f"L{f(x0 - nx)} {f(y0 - ny)}A{f(h)} {f(h)} 0 0 0 {f(x0 + nx)} {f(y0 + ny)}Z"
    )


def spark_path(cx=32, cy=16.5, r_long=7.8, r_short=5.4, width=3.0):
    """8-ray spark (the 'AI' dot of the i): long rays on the axes, short on diagonals."""
    d = ""
    for i in range(8):
        a = math.radians(i * 45 - 90)
        r = r_long if i % 2 == 0 else r_short
        d += capsule(cx, cy, cx + r * math.cos(a), cy + r * math.sin(a), width / 2)
    return d


def candle_path():
    """The stem of the i drawn as a candlestick: wick + rounded body."""
    wick = capsule(32, 31, 32, 54.5, 1.3)
    x, y, w, h, r = 25.75, 35, 12.5, 15, 2.6
    # Drawn counter-clockwise, same winding as the capsules, so the overlap
    # with the wick stays filled under the nonzero rule (no hole).
    body = (
        f"M{x + r} {y}A{r} {r} 0 0 0 {x} {y + r}V{y + h - r}A{r} {r} 0 0 0 {x + r} {y + h}"
        f"H{x + w - r}A{r} {r} 0 0 0 {x + w} {y + h - r}V{y + r}A{r} {r} 0 0 0 {x + w - r} {y}Z"
    )
    return wick + body


TILE = "M15 0H49A15 15 0 0 1 64 15V49A15 15 0 0 1 49 64H15A15 15 0 0 1 0 49V15A15 15 0 0 1 15 0Z"
GLYPH_BOX = (21.2, 5.7, 21.6, 51.6)  # tight box around spark + candle, with 1 unit margin


def icon(tile, spark, candle, dx=0, dy=0, s=1):
    t = f' transform="translate({dx} {dy}) scale({s})"' if (dx or dy or s != 1) else ""
    parts = [f'<path d="{TILE}" fill="{tile}"/>'] if tile else []
    parts += [f'<path d="{spark_path()}" fill="{spark}"/>', f'<path d="{candle_path()}" fill="{candle}"/>']
    return f"<g{t}>{''.join(parts)}</g>"


# ------------------------------------------------------------ wordmark ----
def wordmark(font_path, cap_px, x, baseline, color, dot_color, tracking):
    """Shape WORD with HarfBuzz (kerning kept) and return (svg, bounds)."""
    font = TTFont(font_path)
    gs = font.getGlyphSet()
    scale = cap_px / font["OS/2"].sCapHeight
    face = hb.Face(hb.Blob.from_file_path(str(font_path)))
    buf = hb.Buffer()
    buf.add_str(WORD)
    buf.guess_segment_properties()
    hb.shape(hb.Font(face), buf, {"kern": True, "liga": True})
    order = font.getGlyphOrder()
    xh = font["OS/2"].sxHeight

    main, dot, adv = "", "", 0
    bounds = [math.inf, math.inf, -math.inf, -math.inf]
    for idx, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        name = order[info.codepoint]
        rec = DecomposingRecordingPen(gs)  # some glyphs (e.g. Geist 'i') are built from components
        gs[name].draw(rec)
        contours, cur = [], []
        for op, args in rec.value:
            cur.append((op, args))
            if op in ("closePath", "endPath"):
                contours.append(cur)
                cur = []
        m = (scale, 0, 0, -scale, x + (adv + pos.x_offset) * scale, baseline)
        for c in contours:
            sp, bp = SVGPathPen(None), BoundsPen(None)
            tp, tb = TransformPen(sp, m), TransformPen(bp, m)
            for op, args in c:
                getattr(tp, op)(*args)
                getattr(tb, op)(*args)
            gb = BoundsPen(None)
            for op, args in c:
                getattr(gb, op)(*args)
            # The first glyph's dot (contour sitting above x-height) gets the clay accent.
            if idx == 0 and name == "i" and gb.bounds[1] > xh * 0.8:
                dot += sp.getCommands()
            else:
                main += sp.getCommands()
            b = bp.bounds
            bounds = [min(bounds[0], b[0]), min(bounds[1], b[1]), max(bounds[2], b[2]), max(bounds[3], b[3])]
        adv += pos.x_advance + tracking
    svg = f'<path d="{main}" fill="{color}"/><path d="{dot}" fill="{dot_color}"/>'
    return svg, bounds


def svg_doc(box, inner, title="iBitPay"):
    x, y, w, h = box
    f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(x)} {f(y)} {f(w)} {f(h)}" '
        f'width="{f(w * 8)}" height="{f(h * 8)}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{inner}</svg>\n"
    )


def horizontal(font, cap, tracking, tile, fg, word, dot):
    gap = 17
    w_svg, b = wordmark(font, cap, 64 + gap, 32 + cap / 2, word, dot, tracking)
    top, bottom = min(0, b[1]), max(64, b[3])
    return svg_doc((0, top, math.ceil(b[2] + 1), bottom - top), icon(tile, CLAY, fg) + w_svg)


def stacked(font, cap, tracking, tile, fg, word, dot):
    # measure first, then centre the wordmark under the icon
    _, b = wordmark(font, cap, 0, 0, word, dot, tracking)
    ww = b[2] - b[0]
    width = max(64, ww) + 8
    base = 64 + 16 + cap
    w_svg, b2 = wordmark(font, cap, (width - ww) / 2 - b[0], base, word, dot, tracking)
    return svg_doc((0, 0, width, math.ceil(b2[3] + 2)), icon(tile, CLAY, fg, dx=(width - 64) / 2) + w_svg)


# ---------------------------------------------------------------- main ----
def main():
    files = {
        # 图标（方块底）
        "ibitpay-icon-ink": svg_doc((0, 0, 64, 64), icon(INK, CLAY, IVORY)),
        "ibitpay-icon-ivory": svg_doc((0, 0, 64, 64), icon(IVORY, CLAY, INK)),
        # 图形（无底，只有火花 + K 线）
        "ibitpay-glyph-color": svg_doc(GLYPH_BOX, icon(None, CLAY, INK)),
        "ibitpay-glyph-color-reversed": svg_doc(GLYPH_BOX, icon(None, CLAY, IVORY)),
        "ibitpay-glyph-black": svg_doc(GLYPH_BOX, icon(None, BLACK, BLACK)),
        "ibitpay-glyph-white": svg_doc(GLYPH_BOX, icon(None, WHITE, WHITE)),
        # 横版组合（科技感无衬线字标，主推）
        "ibitpay-logo": horizontal(SANS, 31, -14, INK, IVORY, INK, CLAY),
        "ibitpay-logo-reversed": horizontal(SANS, 31, -14, IVORY, INK, IVORY, CLAY),
        # 竖版组合
        "ibitpay-logo-stacked": stacked(SANS, 24, -14, INK, IVORY, INK, CLAY),
        "ibitpay-logo-stacked-reversed": stacked(SANS, 24, -14, IVORY, INK, IVORY, CLAY),
        # 横版组合（衬线字标，备选）
        "ibitpay-logo-serif": horizontal(SERIF, 36, -12, INK, IVORY, INK, CLAY),
        "ibitpay-logo-serif-reversed": horizontal(SERIF, 36, -12, IVORY, INK, IVORY, CLAY),
    }
    for sub in ("svg", "pdf", "eps", "png"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    for name, doc in files.items():
        svg = OUT / "svg" / f"{name}.svg"
        svg.write_text(doc)
        cairosvg.svg2pdf(url=str(svg), write_to=str(OUT / "pdf" / f"{name}.pdf"))
        cairosvg.svg2eps(url=str(svg), write_to=str(OUT / "eps" / f"{name}.eps"))
        # PNG：图标 1024 px 高，组合 512 px 高（透明底）
        h = 1024 if ("icon" in name or "glyph" in name) else 512
        cairosvg.svg2png(url=str(svg), write_to=str(OUT / "png" / f"{name}.png"), output_height=h)
    print(f"wrote {len(files)} logos x (svg, pdf, eps, png) to {OUT}")


if __name__ == "__main__":
    main()
