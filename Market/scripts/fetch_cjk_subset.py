"""Rebuild the Chinese font subset from the characters used in ecard.html.

Noto Sans SC is ~10 MB, so the page ships a subset that only contains the
characters it actually uses. Run this after changing any Chinese text (e.g. the
name or title) so the page keeps the right typeface:

    python3 Market/scripts/fetch_cjk_subset.py
"""
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "ecard.html"
FONTS = ROOT / "assets/fonts"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

FAMILIES = {
    "NotoSansSC-subset.woff2": "Noto+Sans+SC:wght@400;500;600",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        return r.read()


def main():
    text = HTML.read_text(encoding="utf-8")
    chars = sorted(set(re.findall(r"[　-〿一-鿿＀-￯]", text)) | set("·"))
    q = urllib.parse.quote("".join(chars))
    for out, family in FAMILIES.items():
        css = get(f"https://fonts.googleapis.com/css2?family={family}&text={q}").decode()
        url = re.search(r"url\((\S+?)\)", css).group(1)
        (FONTS / out).write_bytes(get(url))
        print(f"{out}: {len(chars)} chars, {(FONTS / out).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
