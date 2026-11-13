"""Publish the tracked styles used by the archive and its Ghost explorer."""

from functools import lru_cache
from hashlib import sha256


STYLES = (
    'style.css', 'archive-identity.css', 'institutional.css', 'archival-design.css',
    'archive-explorer.css', 'website-captures.css', 'book-reader.css', 'evidence.css',
)
THEME_COLOR = '#20231e'
VIEWPORT = 'width=device-width,initial-scale=1'


def source(root, name):
    return root / 'assets/styles' / name


@lru_cache(maxsize=None)
def asset_url(root, name):
    version = sha256(source(root, name).read_bytes()).hexdigest()[:12]
    return f'assets/{name}?v={version}'


def publish_styles(root, out):
    styles = {name: source(root, name).read_bytes() for name in STYLES}
    target = out / 'assets'
    target.mkdir(parents=True, exist_ok=True)
    for name, content in styles.items():
        (target / name).write_bytes(content)
