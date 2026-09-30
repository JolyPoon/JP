"""Build the iBitPay logo SVGs (mark + outlined wordmark lockups).

Usage:  pip install fonttools uharfbuzz && python3 Market/scripts/build_logo.py

The wordmark is shaped with HarfBuzz (so kerning is kept) and converted to
outlines, so the SVGs render the same everywhere without the font installed.
"""
import math
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "assets/fonts/Newsreader-Display-Medium.ttf"
OUT = ROOT / "logo"

INK = "#141413"
IVORY = "#F5F3EC"
CLAY = "#D97757"

WORD = "iBitPay"


# ---------------------------------------------------------------- mark ----
def spark(cx, cy, r_long, r_short, width, color):
    """8-ray asterisk: long rays on the axes, short ones on the diagonals."""
    rays = []
    for i in range(8):
        a = math.radians(i * 45 - 90)
        r = r_long if i % 2 == 0 else r_short
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        rays.append(f"M{cx:.2f} {cy:.2f}L{x:.2f} {y:.2f}")
    return (
        f'<path d="{"".join(rays)}" stroke="{color}" stroke-width="{width}" '
        f'stroke-linecap="round" fill="none"/>'
    )


def candle_i(fg):
    """The stem of the 'i' drawn as a candlestick: wick + body."""
    return (
        f'<path d="M32 31V54.5" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>'
        f'<rect x="25.75" y="35" width="12.5" height="15" rx="2.6" fill="{fg}"/>'
    )


def mark_group(tile, fg):
    return (
        f'<rect width="64" height="64" rx="15" fill="{tile}"/>'
        + spark(32, 16.5, 7.8, 5.4, 3.0, CLAY)
        + candle_i(fg)
    )


# ------------------------------------------------------------ wordmark ----
def wordmark_paths(scale, dx, baseline):
    """Return (list of (svg_path, is_first_i_dot), advance_width) for WORD."""
    font = TTFont(FONT)
    gs = font.getGlyphSet()
    blob = hb.Blob.from_file_path(str(FONT))
    hb_font = hb.Font(hb.Face(blob))
    buf = hb.Buffer()
    buf.add_str(WORD)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf, {"kern": True, "liga": True})

    order = font.getGlyphOrder()
    parts, x = [], 0
    tracking = -12  # font units, slightly tight like a display wordmark
    for idx, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        name = order[info.codepoint]
        # Split contours so the first 'i' can get a clay-coloured dot.
        from fontTools.pens.recordingPen import RecordingPen

        rec = RecordingPen()
        gs[name].draw(rec)
        contours, cur = [], []
        for op, args in rec.value:
            cur.append((op, args))
            if op in ("closePath", "endPath"):
                contours.append(cur)
                cur = []
        for c in contours:
            sp = SVGPathPen(None)
            tp = TransformPen(sp, (scale, 0, 0, -scale, dx + (x + pos.x_offset) * scale, baseline))
            for op, args in c:
                getattr(tp, op)(*args)
            bp = BoundsPen(None)
            for op, args in c:
                getattr(bp, op)(*args)
            is_dot = idx == 0 and name == "i" and bp.bounds and bp.bounds[1] > 400
            parts.append((sp.getCommands(), is_dot))
        x += pos.x_advance + tracking
    return parts, x * scale


def lockup(tile, fg, word_color, dot_color):
    # Mark is 64 high; the wordmark cap height is set to ~0.56 of that.
    font = TTFont(FONT)
    cap = font["OS/2"].sCapHeight or 650
    scale = 36 / cap
    gap = 18
    baseline = 32 + 36 / 2  # centre caps on the tile
    parts, adv = wordmark_paths(scale, 64 + gap, baseline)
    width = math.ceil(64 + gap + adv + 2)
    body = mark_group(tile, fg)
    word = "".join(
        f'<path d="{d}" fill="{dot_color if dot else word_color}"/>' for d, dot in parts
    )
    return width, body + word


def svg(w, h, inner, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{title}"><title>{title}</title>{inner}</svg>\n'
    )


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "ibitpay-mark.svg").write_text(svg(64, 64, mark_group(INK, IVORY), "iBitPay"))
    (OUT / "ibitpay-mark-reversed.svg").write_text(svg(64, 64, mark_group(IVORY, INK), "iBitPay"))

    w, inner = lockup(INK, IVORY, INK, CLAY)
    (OUT / "ibitpay-logo.svg").write_text(svg(w, 64, inner, "iBitPay"))
    w, inner = lockup(IVORY, INK, IVORY, CLAY)
    (OUT / "ibitpay-logo-reversed.svg").write_text(svg(w, 64, inner, "iBitPay"))
    print("wrote", sorted(p.name for p in OUT.glob("*.svg")))


if __name__ == "__main__":
    main()
