"""Bounded image-header measurements for stable HTML, without decoding pixels.

These dimensions describe the stored image. No rights, creator, GPS or other
embedded metadata is inferred or exported. Unknown formats remain unmeasured.
"""

from functools import lru_cache
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit, unquote


def _orientation(data):
    at = data.find(b"Exif\x00\x00")
    if at < 0:
        return 1
    t = data[at + 6 :]
    endian = "<" if t[:2] == b"II" else ">"
    offset = struct.unpack_from(endian + "I", t, 4)[0]
    count = struct.unpack_from(endian + "H", t, offset)[0]
    for i in range(min(count, 4096)):
        p = offset + 2 + 12 * i
        if struct.unpack_from(endian + "H", t, p)[0] == 274:
            return struct.unpack_from(endian + "H", t, p + 8)[0]
    return 1


@lru_cache(maxsize=4096)
def dimensions(path):
    """Return oriented (width, height), or None for an unknown/bad header."""
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(1024 * 1024)
        size = None
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            size = struct.unpack_from(">II", data, 16)
        elif data[:6] in (b"GIF87a", b"GIF89a"):
            size = struct.unpack_from("<HH", data, 6)
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            kind = data[12:16]
            if kind == b"VP8X":
                size = (
                    int.from_bytes(data[24:27], "little") + 1,
                    int.from_bytes(data[27:30], "little") + 1,
                )
            elif kind == b"VP8L" and data[20] == 47:
                bits = int.from_bytes(data[21:25], "little")
                size = ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
            elif kind == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
                size = tuple(v & 0x3FFF for v in struct.unpack_from("<HH", data, 26))
        elif data.startswith(b"\xff\xd8"):
            at = 2
            while at + 4 < len(data):
                if data[at] != 255:
                    break
                while data[at] == 255:
                    at += 1
                marker = data[at]
                at += 1
                if marker in (0xD9, 0xDA):
                    break
                length = struct.unpack_from(">H", data, at)[0]
                if length < 2:
                    break
                if marker in (
                    0xC0,
                    0xC1,
                    0xC2,
                    0xC3,
                    0xC5,
                    0xC6,
                    0xC7,
                    0xC9,
                    0xCA,
                    0xCB,
                    0xCD,
                    0xCE,
                    0xCF,
                ):
                    height, width = struct.unpack_from(">HH", data, at + 3)
                    size = (width, height)
                    if _orientation(data) in (5, 6, 7, 8):
                        size = (height, width)
                    break
                at += length
        return size if size and all(0 < v <= 1000000 for v in size) else None
    except (OSError, IndexError, ValueError, struct.error):
        return None


def attributes(path):
    size = dimensions(str(path))
    return f' width="{size[0]}" height="{size[1]}"' if size else ""


def enrich_images(html, page, out, origin):
    """Add measured dimensions only to existing same-origin local image files."""

    def image(match):
        tag = match[0]
        if re.search(r"\b(?:width|height)\s*=", tag):
            return tag
        source = re.search(r"\bsrc\s*=\s*([\"\'])(.*?)\1", tag)
        if not source:
            return tag
        url = urlsplit(source[2])
        if url.scheme and url.scheme + "://" + url.netloc != origin:
            return tag
        if source[2].startswith("/") or url.scheme:
            path = out / unquote(url.path).lstrip("/")
        else:
            path = (out / page).parent / unquote(url.path)
        path = path.resolve()
        if not path.is_relative_to(out.resolve()):
            return tag
        return tag[:-1] + attributes(path) + ">"

    return re.sub(r"<img\b[^>]*>", image, html, flags=re.I)
