"""Read-only Ghost -> static archive reconciliation. Never imports an Admin API client.
Runtime content is ignored by Git. Historical captures are AES-GCM/RSA-OAEP
sealed to an offline recovery key; the runner only needs the public key.
"""

from __future__ import annotations
import argparse, base64, copy, fcntl, gzip, hashlib, json, os, re, shutil, tempfile, time
from datetime import datetime, timezone
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError
from website_metadata import describe

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://www.museumofone.art"
STORAGE = "https://storage.ghost.io/c/b5/1f/b51fbd98-6416-4011-90f9-a06bf0b40d7c"
ASSET_MIMES = {
    ".ico": "image/vnd.microsoft.icon",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".csv": "text/csv",
    ".json": "application/json",
    ".txt": "text/plain",
    ".zip": "application/zip",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def is_upload(u):
    p = urlsplit(u)
    if u.startswith(STORAGE + "/"):
        return p.path[len(urlsplit(STORAGE).path) :].startswith(
            ("/content/files/", "/content/images/", "/content/media/")
        )
    return p.netloc in (
        "www.museumofone.art",
        "the-museum-of-one.ghost.io",
    ) and p.path.startswith(("/content/files/", "/content/images/", "/content/media/"))


def encoded(x):
    return json.dumps(
        x, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def digest(x):
    return hashlib.sha256(x if isinstance(x, bytes) else encoded(x)).hexdigest()


def now():
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        f.write(data)
        name = f.name
    os.replace(name, path)


class FetchFailure(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        a, b = urlsplit(req.full_url), urlsplit(newurl)
        if (
            b.scheme == "https"
            and b.hostname in ("www.museumofone.art", "the-museum-of-one.ghost.io")
            and a.path == b.path
            and a.query == b.query
        ):
            return super().redirect_request(req, fp, code, msg, headers, newurl)
        if (
            b.scheme == "https"
            and newurl.startswith(STORAGE + "/")
            and b.path == urlsplit(STORAGE).path + a.path
            and a.query == b.query
        ):
            return super().redirect_request(req, fp, code, msg, headers, newurl)
        raise FetchFailure("Redirect refused")


class Fetcher:
    def __init__(self, sleep=time.sleep):
        self.sleep = sleep
        self.opener = build_opener(NoRedirect())
        self.cache = {}
        self.asset_bytes = 0
        self.response_headers = {}
        self.asset_index = {}
        self.reused_assets = 0

    def get(self, url, limit=8000000):
        if urlsplit(url).scheme != "https" or urlsplit(url).hostname not in (
            "www.museumofone.art",
            "the-museum-of-one.ghost.io",
            "storage.ghost.io",
            "api.github.com",
        ):
            raise FetchFailure("Unapproved source host")
        if urlsplit(url).hostname == "storage.ghost.io" and not url.startswith(
            STORAGE + "/"
        ):
            raise FetchFailure("Unapproved storage tenant")
        for attempt in range(4):
            try:
                with self.opener.open(
                    Request(
                        url,
                        headers={
                            "User-Agent": "MuseumOfOne-WebsiteArchiveSync/1.0",
                            "Accept": "application/json,text/html",
                            "Cache-Control": "no-cache",
                        },
                    ),
                    timeout=30,
                ) as r:
                    body = r.read(limit + 1)
                    if len(body) > limit:
                        raise FetchFailure("Response exceeds size limit")
                    self.response_headers[url] = dict(r.headers)
                    return body
            except HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise FetchFailure("Source HTTP " + str(e.code)) from None
            except (URLError, TimeoutError, OSError):
                if attempt == 3:
                    raise FetchFailure("Source request failed") from None
            self.sleep(min(2**attempt, 8))
        raise FetchFailure("Source request failed")


    def document_language(self, url):
        """Read only the public page head; absence is not a capture failure."""
        if not url.startswith(ORIGIN + "/"):
            return None
        try:
            with self.opener.open(Request(url, headers={
                "User-Agent": "MuseumOfOne-WebsiteArchiveSync/1.0",
                "Accept": "text/html",
            }), timeout=5) as response:
                if response.geturl() != url or response.headers.get_content_type() != "text/html":
                    return None
                parser = DocumentLanguage()
                parser.feed(response.read(32768).decode("utf-8", errors="replace"))
                return parser.language
        except (FetchFailure, URLError, OSError):
            return None


class DocumentLanguage(HTMLParser):
    language = None

    def handle_starttag(self, tag, attrs):
        if tag == "html":
            value = (dict(attrs).get("lang") or "").strip()
            if re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", value):
                self.language = value


class SourceHead(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.meta = []
        self.buffer = None
        self.feed(html or "")

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("type") == "application/ld+json":
            self.buffer = ""
        if tag == "meta" and a.get("content") is not None:
            self.meta.append(
                {
                    "name": a.get("name") or a.get("property") or "",
                    "content": a["content"],
                }
            )

    def handle_data(self, value):
        if self.buffer is not None:
            self.buffer += value

    def handle_endtag(self, tag):
        if tag != "script" or self.buffer is None:
            return
        try:
            value = json.loads(self.buffer)

            def walk(x):
                if isinstance(x, list):
                    for v in x:
                        walk(v)
                elif isinstance(x, dict):
                    for k, v in x.items():
                        if k in (
                            "license",
                            "inLanguage",
                            "identifier",
                            "publisher",
                            "contributor",
                            "version",
                            "copyrightNotice",
                            "isPartOf",
                        ):
                            self.meta.append(
                                {
                                    "name": "JSON-LD " + k,
                                    "content": json.dumps(
                                        v, ensure_ascii=False, separators=(",", ":")
                                    ),
                                }
                            )
                        elif k in ("@graph", "mainEntity", "hasPart"):
                            walk(v)

            walk(value)
        except (ValueError, TypeError):
            pass
        self.buffer = None


class Readable(HTMLParser):
    allowed = set(
        "p div section article span h1 h2 h3 h4 h5 h6 ul ol li blockquote pre code strong em b i u s sub sup br hr table thead tbody tfoot tr td th caption figure figcaption dl dt dd a".split()
    )
    blocked = set(
        "script style iframe object embed form input button select textarea svg canvas audio video".split()
    )

    def __init__(self, html, base=ORIGIN + "/"):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.parts = []
        self.text = []
        self.links = []
        self.skip = []
        self.feed(html or "")
        self.close()

    def handle_starttag(self, t, attrs):
        a = dict(attrs)
        if t in ("audio", "video", "source", "iframe", "embed") and a.get("src"):
            u = self.safe(a["src"])
            if u:
                self.links.append({"url": u, "role": t, "label": "Source " + t})
                self.parts.append(
                    '<p><a href="'
                    + escape(u, quote=True)
                    + '">Source '
                    + t
                    + "</a></p>"
                )
        if self.skip:
            if t in self.blocked and t not in ("input", "embed"):
                self.skip.append(t)
            return
        if t in self.blocked:
            if t not in ("input", "embed"):
                self.skip.append(t)
            return
        if t == "img":
            u = self.safe(a.get("src"))
            label = a.get("alt") or "Source image"
            if u:
                self.parts.append(
                    '<p><a href="'
                    + escape(u, quote=True)
                    + '">'
                    + escape(label)
                    + " — image at source</a></p>"
                )
                self.links.append({"url": u, "role": "image", "label": label})
            return
        if t not in self.allowed:
            return
        attrs_out = ""
        if t == "a":
            u = self.safe(a.get("href"))
            if u:
                attrs_out = (
                    ' href="' + escape(u, quote=True) + '" rel="noopener noreferrer"'
                )
                self.links.append(
                    {"url": u, "role": "link", "label": a.get("title", "")}
                )
        for k in ("id", "colspan", "rowspan", "lang", "dir"):
            if a.get(k) and re.fullmatch(r"[\w.:-]{1,120}", a[k]):
                attrs_out += " " + k + '="' + escape(a[k], quote=True) + '"'
        self.parts.append("<" + t + attrs_out + ">")

    def handle_endtag(self, t):
        if self.skip:
            if t == self.skip[-1]:
                self.skip.pop()
            return
        if t in self.allowed and t not in ("br", "hr"):
            self.parts.append("</" + t + ">")
        if t in ("p", "div", "li", "h1", "h2", "h3", "tr"):
            self.text.append("\n")

    def handle_data(self, s):
        if not self.skip:
            self.parts.append(escape(s))
            self.text.append(s)

    def safe(self, u):
        if not u:
            return ""
        u = urljoin(self.base, u)
        p = urlsplit(u)
        if p.scheme in ("https", "mailto") and not p.username and not p.password:
            return u
        return ""


def fetch_collection(fetcher, policy):
    home = fetcher.get(ORIGIN + "/").decode()
    match = re.search(
        r'/ghost/api/content/[^"<>]*[?&]key=([0-9a-f]+)', unescape(home)
    ) or re.search(r'contentKey["\x27]?\s*[:=]\s*["\x27]([0-9a-f]+)', home)
    if not match:
        raise FetchFailure("Public Content API configuration unavailable")
    key = match.group(1)
    rows = []
    seen = set()
    for kind in ("posts", "pages"):
        page = 1
        while page:
            query = urlencode(
                {
                    "key": key,
                    "filter": "visibility:public",
                    "formats": "html,plaintext",
                    "include": "authors,tags",
                    "limit": 100,
                    "page": page,
                    "order": "id asc",
                }
            )
            # Never print request URLs: Content API keys stay in request memory.
            j = json.loads(
                fetcher.get(
                    policy["content_api_origin"]
                    + "/ghost/api/content/"
                    + kind
                    + "/?"
                    + query
                )
            )
            items = j[kind]
            for row in items:
                rid = row.get("id")
                if (
                    not isinstance(rid, str)
                    or not re.fullmatch("[a-f0-9]{24}", rid)
                    or rid in seen
                ):
                    raise FetchFailure("Duplicate or invalid Ghost ID")
                seen.add(rid)
                rows.append({"kind": kind[:-1], "record": row})
            pagination = j["meta"]["pagination"]
            next_page = pagination.get("next")
            if next_page is not None and (
                not isinstance(next_page, int) or next_page <= page
            ):
                raise FetchFailure("Invalid pagination")
            page = next_page
            if len(rows) > policy["max_records"]:
                raise FetchFailure("Source record limit exceeded")
    return rows


FIELDS = (
    "id",
    "title",
    "html",
    "custom_excerpt",
    "excerpt",
    "published_at",
    "updated_at",
    "url",
    "canonical_url",
    "meta_title",
    "meta_description",
    "og_title",
    "og_description",
    "twitter_title",
    "twitter_description",
    "feature_image",
    "feature_image_alt",
    "feature_image_caption",
)


def eligible(r, at):
    u = urlsplit(r.get("url") or "")
    return (
        r.get("visibility") == "public"
        and r.get("status", "published") == "published"
        and r.get("published_at")
        and r["published_at"] <= at
        and u.scheme == "https"
        and u.netloc == "www.museumofone.art"
        and not u.query
        and not u.fragment
        and bool(r.get("title"))
        and isinstance(r.get("html"), str)
    )


def metadata(r, kind):
    m = {k: r.get(k) for k in FIELDS}
    m["kind"] = kind
    m["creators"] = [
        {"name": a["name"], "role": "Credited website author", "url": a.get("url")}
        for a in r.get("authors", [])
        if a.get("name")
    ]
    m["subjects"] = [
        t["name"]
        for t in r.get("tags", [])
        if t.get("visibility") == "public" and t.get("name")
    ]
    m["source_declared_metadata"] = SourceHead(r.get("codeinjection_head")).meta
    # No author emails, account fields, internal tags, keys, script code or subscribers.
    return m


def seal(value, public_key, cache_key=None):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = serialization.load_pem_public_key(public_key)
    aes = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    plain = gzip.compress(encoded(value), mtime=0)
    wrapped = key.encrypt(
        aes,
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None
        ),
    )
    envelope = {
        "format": "moo-rsa-oaep-aes256gcm-v1",
        "wrapped_key": base64.b64encode(wrapped).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(
            AESGCM(aes).encrypt(nonce, plain, b"moo-website-sync-v1")
        ).decode(),
    }
    if cache_key:
        n = os.urandom(12)
        envelope["runtime_nonce"] = base64.b64encode(n).decode()
        envelope["runtime_wrapped_key"] = base64.b64encode(
            AESGCM(cache_key).encrypt(n, aes, b"moo-asset-cache-v1")
        ).decode()
    return encoded(envelope)


def unseal(blob, private_key, password):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    x = json.loads(blob)
    key = serialization.load_pem_private_key(private_key, password)
    aes = key.decrypt(
        base64.b64decode(x["wrapped_key"]),
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None
        ),
    )
    return json.loads(
        gzip.decompress(
            AESGCM(aes).decrypt(
                base64.b64decode(x["nonce"]),
                base64.b64decode(x["ciphertext"]),
                b"moo-website-sync-v1",
            )
        )
    )


def cache_key():
    value = os.environ.get("MOO_ASSET_CACHE_KEY")
    if not value:
        return None
    try:
        key = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError:
        raise FetchFailure("Asset-cache key format invalid") from None
    if len(key) != 32:
        raise FetchFailure("Asset-cache key length invalid")
    return key


def open_cached_asset(path, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    x = json.loads(path.read_bytes())
    aes = AESGCM(key).decrypt(
        base64.b64decode(x["runtime_nonce"]),
        base64.b64decode(x["runtime_wrapped_key"]),
        b"moo-asset-cache-v1",
    )
    value = json.loads(
        gzip.decompress(
            AESGCM(aes).decrypt(
                base64.b64decode(x["nonce"]),
                base64.b64decode(x["ciphertext"]),
                b"moo-website-sync-v1",
            )
        )
    )
    b = base64.b64decode(value["bytes_base64"])
    if digest(b) != value["sha256"]:
        raise FetchFailure("Cached asset hash mismatch")
    return b


def attachment_records(parser, root, fetcher, policy, work):
    known = (
        {r["sha256"]: r for r in json.loads((root / "data/readers.json").read_text())}
        if (root / "data/readers.json").exists()
        else {}
    )
    out = []
    seen = set()
    for link in parser.links:
        u = link["url"]
        p = urlsplit(u)
        if u in seen or not (
            link["role"] == "image"
            or "/content/files/" in p.path
            or "/content/media/" in p.path
            or re.search(r"\.(pdf|docx?|zip|csv|xlsx?|png|jpe?g|webp)$", p.path, re.I)
        ):
            continue
        seen.add(u)
        item = {
            **link,
            "storage": "external_link_only",
            "availability": "not_checked",
            "reason": "Third-party or unreviewed reuse rights; no local preservation claim.",
        }
        if is_upload(u):
            try:
                cache = getattr(fetcher, "cache", {})
                if u in cache:
                    item.update(cache[u])
                    out.append(item)
                    continue
                prior = getattr(fetcher, "asset_index", {}).get(digest(u.encode()))
                reused = False
                if prior and prior.get("etag") and cache_key():
                    try:
                        with fetcher.opener.open(
                            Request(
                                u,
                                method="HEAD",
                                headers={
                                    "User-Agent": "MuseumOfOne-ArchiveAssetCheck/1.0",
                                    "Cache-Control": "no-cache",
                                },
                            ),
                            timeout=30,
                        ) as response:
                            etag = response.headers.get("ETag")
                        if etag and etag == prior["etag"] and prior.get("sha256"):
                            b = open_cached_asset(
                                work / "vault/assets" / (prior["sha256"] + ".json"),
                                cache_key(),
                            )
                            reused = True
                            fetcher.reused_assets += 1
                    except Exception:
                        reused = False
                if not reused:
                    b = fetcher.get(u, policy["max_attachment_bytes"])
                h = digest(b)
                if h in known:
                    r = known[h]
                    local = root / "dist/assets/documents" / (r["id"] + ".pdf")
                    assert digest(local.read_bytes()) == h
                    item.update(
                        storage="existing_verified_archive_file",
                        archive_path="assets/documents/" + r["id"] + ".pdf",
                        sha256=h,
                        bytes=len(b),
                        availability="available",
                        reason="Exact bytes match an existing reviewed reading copy; its edition rights/exclusions remain applicable.",
                    )
                else:
                    if (
                        getattr(fetcher, "asset_bytes", 0) + len(b)
                        > policy["max_total_asset_bytes"]
                    ):
                        item.update(
                            availability="deferred",
                            reason="Per-run asset budget reached; source link retained for review.",
                        )
                        out.append(item)
                        continue
                    suffix = Path(p.path).suffix.lower()
                    if suffix in (".pem", ".key", ".p12", ".pfx", ".env"):
                        item.update(
                            availability="withheld",
                            reason="Potential credential/key material is excluded from automatic archival publication.",
                        )
                        cache[u] = item
                        out.append(item)
                        continue
                    if suffix not in (
                        ".ico",
                        ".tif",
                        ".tiff",
                        ".pdf",
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp",
                        ".gif",
                        ".avif",
                        ".mp3",
                        ".mp4",
                        ".m4a",
                        ".wav",
                        ".ogg",
                        ".webm",
                        ".mov",
                        ".csv",
                        ".json",
                        ".txt",
                        ".zip",
                        ".docx",
                        ".xlsx",
                    ):
                        suffix = ".bin"
                        path = "assets/website-captures/" + h + suffix
                        atomic(work / "public" / path, b)
                        fetcher.asset_bytes = getattr(fetcher, "asset_bytes", 0) + len(
                            b
                        )
                        item.update(
                            storage="local_archival_file",
                            archive_path=path,
                            sha256=h,
                            bytes=len(b),
                            mime_type="application/octet-stream",
                            availability="available",
                            reason="Original site-uploaded bytes preserved as an inert binary download; original filename and source URL retained. Not executed by the archive.",
                        )
                    elif (
                        getattr(fetcher, "asset_bytes", 0) + len(b)
                        > policy["max_total_asset_bytes"]
                    ):
                        item.update(
                            availability="deferred",
                            reason="Per-run asset budget reached; source link retained for review.",
                        )
                    else:
                        path = "assets/website-captures/" + h + suffix
                        atomic(work / "public" / path, b)
                        fetcher.asset_bytes = getattr(fetcher, "asset_bytes", 0) + len(
                            b
                        )
                        item.update(
                            storage="local_archival_file",
                            archive_path=path,
                            sha256=h,
                            bytes=len(b),
                            mime_type=ASSET_MIMES[suffix],
                            availability="available",
                            reason="Public site-uploaded asset captured under the site owner’s archive instruction. Original rights, credits and third-party exceptions remain applicable; no new licence is granted.",
                        )
                cache[u] = {
                    k: v for k, v in item.items() if k not in ("url", "role", "label")
                }
                fetcher.cache = cache
                if item.get("sha256") and item["storage"] == "local_archival_file":
                    etag = (
                        (prior or {}).get("etag")
                        if reused
                        else getattr(fetcher, "response_headers", {})
                        .get(u, {})
                        .get("ETag")
                    )
                    fetcher.asset_index[digest(u.encode())] = {**cache[u], "etag": etag}
            except (FetchFailure, OSError, AssertionError):
                item.update(
                    availability="failed",
                    reason="Attachment could not be verified; retry at next reconciliation.",
                )
        out.append(item)
    return out


def reconcile(
    rows,
    state,
    root,
    work,
    policy,
    fetcher,
    *,
    at=None,
    dry=False,
    previous_projection=(),
):
    at = at or now()
    state = copy.deepcopy(state or {"schema_version": 1, "records": {}})
    records = state["records"]
    public = []
    changes = []
    seen = set()
    urls = set()
    excluded = []
    issues = []
    prior = {
        r["url"]: "website:" + digest(r["url"].encode())[:24]
        for r in previous_projection
    }
    key = (root / policy["public_key"]).read_bytes()
    fetcher.asset_index = copy.deepcopy(state.get("asset_index", {}))
    # The reviewed snapshot seeds existing records. New and revised pages are
    # checked directly, and transient evidence gaps are retried on the next run.
    evidence_file = root / "data/website-language-evidence.json"
    reviewed = json.loads(evidence_file.read_text()) if evidence_file.is_file() else {"records": {}}
    for entry in rows:
        r = entry["record"]
        rid = r.get("id", "")
        if not re.fullmatch("[a-f0-9]{24}", rid) or rid in seen:
            raise FetchFailure("Invalid or duplicate source ID")
        seen.add(rid)
        if not eligible(r, at):
            excluded.append({"reason": "Not an eligible public published record"})
            continue
        if r["url"] in urls:
            raise FetchFailure("Two Ghost records use the same canonical website URL")
        urls.add(r["url"])
        source = metadata(r, entry["kind"])
        h = digest(source)
        old = records.get(rid)
        action = (
            "missing"
            if old is None
            else "outdated"
            if old.get("content_hash") != h or old.get("access_status") != "public"
            else "unchanged"
        )
        if (
            old
            and r.get("updated_at")
            and old.get("source_modified")
            and r.get("updated_at") < old["source_modified"]
        ):
            raise FetchFailure("Out-of-order source revision; no checkpoint downgrade")
        changes.append(
            {
                "source_id": rid,
                "source_url": r["url"],
                "action": action,
                "content_hash": h,
            }
        )
        if dry:
            candidate = Readable(r["html"], r["url"])
            changes[-1]["candidate_uploads"] = [
                link["url"] for link in candidate.links if is_upload(link["url"])
            ]
            continue
        parser = Readable(r["html"], r["url"])
        if r.get("feature_image"):
            parser.links.append(
                {
                    "url": r["feature_image"],
                    "role": "image",
                    "label": r.get("feature_image_alt")
                    or " ".join("".join(Readable(r.get("feature_image_caption")).text).split())
                    or "Source feature image",
                }
            )
        assets = attachment_records(parser, root, fetcher, policy, work)
        warnings = []
        declared = source["source_declared_metadata"]
        values = lambda name: [
            v["content"] for v in declared if v["name"].lower() == name
        ]
        summary = (
            r.get("custom_excerpt")
            or r.get("meta_description")
            or r.get("excerpt")
            or ""
        )
        if not source["creators"]:
            warnings.append("No credited website author supplied")
        language = (values("dc.language") or values("citation_language") or [None])[0]
        if not language:
            supplied = values("json-ld inlanguage")
            if supplied:
                try:
                    language = json.loads(supplied[0])
                except ValueError:
                    language = supplied[0]
        document = (old or {}).get("document_language")
        if not document or document["content_hash"] != h:
            checked = reviewed["records"].get(source["url"], {})
            if checked.get("language") and checked.get("source_modified") == source["updated_at"]:
                document = {"language": checked["language"], "checked_at": reviewed["reviewed"], "content_hash": h}
            else:
                observe = getattr(fetcher, "document_language", None)
                value = observe(source["url"]) if observe else None
                document = {"language": value, "checked_at": at, "content_hash": h} if value else None
        if not language and not document:
            warnings.append("Language not explicitly supplied for this web record")
        m = (
            copy.deepcopy(old)
            if old
            else {
                "archive_id": "web-" + rid,
                "discovery_id": prior.get(
                    r["url"], "website:" + digest(r["url"].encode())[:24]
                ),
                "first_captured_at": at,
                "original_published_at": r["published_at"],
                "revisions": [],
            }
        )
        for asset in assets:
            if asset["storage"] == "local_archival_file":
                archive_blob = work / "vault/assets" / (asset["sha256"] + ".json")
                if (
                    not archive_blob.exists()
                    or cache_key()
                    and "runtime_wrapped_key"
                    not in json.loads(archive_blob.read_bytes())
                ):
                    payload = (work / "public" / asset["archive_path"]).read_bytes()
                    atomic(
                        archive_blob,
                        seal(
                            {
                                "sha256": asset["sha256"],
                                "bytes_base64": base64.b64encode(payload).decode(),
                                "original_url": asset["url"],
                            },
                            key,
                            cache_key(),
                        ),
                    )
        asset_signature = digest(assets)
        if action != "unchanged" or m.get("asset_signature") != asset_signature:
            rev = {
                "captured_at": at,
                "source_modified": r.get("updated_at"),
                "content_hash": h,
                "vault_path": "vault/"
                + rid
                + "/"
                + digest((h + asset_signature).encode())
                + ".json",
            }
            capsule = {
                "source": source,
                "readable_html": "".join(parser.parts),
                "attachments": assets,
                "capture": rev,
            }
            atomic(work / rev["vault_path"], seal(capsule, key))
            m["revisions"].append(rev)
        capture = m["revisions"][-1]
        m.update(
            access_status="public",
            source_modified=r.get("updated_at"),
            content_hash=h,
            asset_signature=asset_signature,
            document_language=document,
            last_verified_at=at,
        )
        records[rid] = m
        state["asset_index"] = fetcher.asset_index
        atomic(work / "state.json", encoded(state))
        atomic(
            work / "progress.json",
            encoded(
                {
                    "completed_records": len(public) + 1,
                    "source_records": len(rows),
                    "at": at,
                }
            ),
        )
        curated = (
            json.loads((root / "data/catalogue.json").read_text())
            if (root / "data/catalogue.json").exists()
            else []
        )
        public.append(
            {
                "descriptive_metadata": describe(source, language, summary, curated),
                "source": source,
                "archive_id": m["archive_id"],
                "discovery_id": m["discovery_id"],
                "first_captured_at": m["first_captured_at"],
                "original_published_at": m["original_published_at"],
                "capture": capture,
                "revision_count": len(m["revisions"]),
                "readable_html": "".join(parser.parts),
                "text": " ".join("".join(parser.text).split()),
                "summary": summary,
                "language": language,
                "document_language": {k: document[k] for k in ("language", "checked_at")} if document else None,
                "attachments": assets,
                "validation_issues": warnings,
            }
        )
        issues.extend({"source_id": rid, "issue": v} for v in warnings)
    for rid, m in records.items():
        if not any(p["source"]["id"] == rid for p in public) and not dry:
            if m.get("access_status") == "public":
                changes.append(
                    {
                        "source_id": rid,
                        "action": "withdraw",
                        "reason": "No eligible current source; public serving stops; ciphertext retained",
                    }
                )
            m["access_status"] = "withheld"
            m["last_verified_at"] = at
    if not dry:
        atomic(work / "state.json", encoded(state))
        atomic(work / "public/current.json", encoded(public))
    report = {
        "schema_version": 1,
        "checked_at": at,
        "mode": "dry" if dry else "apply",
        "source_records": len(rows),
        "eligible_records": len(public)
        if not dry
        else sum(c["action"] in ("missing", "outdated", "unchanged") for c in changes),
        "changes": changes,
        "excluded": excluded,
        "validation_issues": issues,
        "reused_asset_downloads": getattr(fetcher, "reused_assets", 0),
        "stored_uploaded_files": len(
            {a["sha256"] for p in public for a in p["attachments"] if a.get("sha256")}
        ),
        "linked_external_assets": len(
            {
                a["url"]
                for p in public
                for a in p["attachments"]
                if a["storage"] == "external_link_only"
            }
        ),
        "failed_attachments": sum(
            a["availability"] == "failed" for p in public for a in p["attachments"]
        ),
        "field_ownership": "Source projection only; existing curated data untouched",
    }
    atomic(work / "report.json", encoded(report))
    return state, public, report


def projection(public):
    return {
        "schema_version": 1,
        "source": "Live public Ghost Content API reconciliation",
        "reviewed": now()[:10],
        "records": [
            {
                "ghost_id": p["source"]["id"],
                "discovery_id": p["discovery_id"],
                "archive_url": "https://archive.museumofone.art/website/"
                + p["archive_id"]
                + ".html",
                "url": p["source"]["url"],
                "title": p["source"]["title"],
                "text": p["text"],
                "summary": p["summary"],
                "record_type": p["source"]["kind"],
                "date": p["source"]["published_at"][:10],
                "date_role": "website_publication",
                "website_modified": p["source"]["updated_at"],
                "source_url": p["source"]["url"],
                "reviewed": p["capture"]["captured_at"][:10],
                "public": True,
                "status": "published",
                "source_sha256": p["capture"]["content_hash"],
                "authors": [x["name"] for x in p["source"]["creators"]],
                "tags": p["source"]["subjects"],
            }
            for p in public
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, default=ROOT / ".sync-work")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fixtures", type=Path)
    args = ap.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    with (work / "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        policy = json.loads((ROOT / "config/website-sync.json").read_text())
        fetcher = Fetcher()
        state = (
            json.loads((work / "state.json").read_text())
            if (work / "state.json").exists()
            else None
        )
        old = json.loads((ROOT / "data/source/ghost-discovery.json").read_text()).get(
            "records", []
        )
        try:
            if not args.dry_run and (work / "public").exists():
                shutil.rmtree(work / "public")
            rows = (
                json.loads(args.fixtures.read_text())
                if args.fixtures
                else fetch_collection(fetcher, policy)
            )
            state, public, report = reconcile(
                rows,
                state,
                ROOT,
                work,
                policy,
                fetcher,
                dry=args.dry_run,
                previous_projection=old,
            )
        except (FetchFailure, ValueError, KeyError) as e:
            # Fail closed for runtime website copies on a source-wide verification failure.
            report = {
                "mode": "suspended",
                "checked_at": now(),
                "source_records": None,
                "eligible_records": 0,
                "error": type(e).__name__,
                "safe_reason": str(e),
                "message": "Source collection could not be completely verified. No current web content is served; encrypted state retained.",
            }
            if not (work / "state.json").exists():
                atomic(
                    work / "state.json",
                    encoded(state or {"schema_version": 1, "records": {}}),
                )
            atomic(work / "public/current.json", b"[]")
            atomic(work / "report.json", encoded(report))
            public = []
        if not args.dry_run:
            atomic(work / "public/discovery.json", encoded(projection(public)))
        print(
            json.dumps(
                {
                    k: report.get(k)
                    for k in (
                        "mode",
                        "source_records",
                        "eligible_records",
                        "failed_attachments",
                        "error",
                        "safe_reason",
                    )
                }
            )
        )


if __name__ == "__main__":
    main()
