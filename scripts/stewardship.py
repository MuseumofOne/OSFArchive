"""Measured SHA-256 fixity and recovery evidence for the archive (stdlib only).

Refresh a baseline deliberately after reviewed additions, then verify it. Verification
never silently replaces expected hashes. The evidence report is excluded from its
own inventory. Backups contain only inventoried files and a recovery manifest.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = "data/stewardship.json"
SCHEMA_VERSION = 1


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def content_paths(root):
    """Preserve source snapshots, editorial datasets and unmodified reading PDFs."""
    root = Path(root)
    paths = sorted(set(root.glob("data/**/*.json")) | set(root.glob("dist/assets/documents/*.pdf")))
    return [p for p in paths if p.is_file() and not p.is_symlink()
            and p.relative_to(root).as_posix() != REPORT]


def inventory(root):
    root = Path(root)
    return [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size,
             "sha256": sha256(p),
             "role": ("repository_source_snapshot" if p.relative_to(root).as_posix().startswith("data/source/")
                      else "original_pdf_access_copy" if p.suffix.lower() == ".pdf" else "editorial_dataset")}
            for p in content_paths(root)]


def inventory_digest(rows):
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def new_report():
    return {"schema_version": SCHEMA_VERSION, "algorithm": "SHA-256", "inventory": [], "events": [],
            "scope": "Repository source snapshots, editorial JSON datasets, and original PDF access copies.",
            "exclusions": ["data/stewardship.json", "Generated website pages, reader engine, and cover images"],
            "storage": {"working_copy": "Current archive build environment",
                        "upstream_sources": "Original deposits remain at Zenodo; website source is held by the site platform.",
                        "offsite_backup_status": "No independent offsite backup of this preservation package has been recorded."}}


def read_report(root):
    p = Path(root) / REPORT
    return json.loads(p.read_text()) if p.exists() else new_report()


def save_report(root, report):
    p = Path(root) / REPORT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


def refresh_inventory(root, report):
    rows = inventory(root)
    if not rows:
        raise ValueError("Preservation inventory is empty")
    report["inventory"] = rows
    report["inventory_sha256"] = inventory_digest(rows)
    report["baseline_created_at"] = utc_now()
    report["events"].append({"at": utc_now(), "event": "baseline_refreshed", "status": "recorded",
                             "file_count": len(rows), "inventory_sha256": report["inventory_sha256"]})
    return rows


def verify_inventory(root, report):
    expected = {r["path"]: r for r in report.get("inventory", [])}
    current = {r["path"]: r for r in inventory(root)}
    missing = sorted(set(expected) - set(current))
    added = sorted(set(current) - set(expected))
    changed = sorted(p for p in set(expected) & set(current)
                     if expected[p]["sha256"] != current[p]["sha256"] or expected[p]["bytes"] != current[p]["bytes"])
    valid = bool(expected) and not (missing or added or changed)
    event = {"at": utc_now(), "event": "fixity_check", "status": "passed" if valid else "failed",
             "algorithm": "SHA-256", "file_count": len(expected), "checked_files": len(set(expected) & set(current)),
             "missing": missing, "added": added, "changed": changed,
             "inventory_sha256": inventory_digest(report.get("inventory", []))}
    report["events"].append(event)
    report["last_check"] = event.copy()
    return event


def _safe_member_path(name):
    p = PurePosixPath(name)
    if p.is_absolute() or not p.parts or ".." in p.parts or "\\" in name:
        raise ValueError("Unsafe preservation package member")
    return p


def restore_and_verify(package, expected):
    """Extract only regular inventoried members into a fresh isolated directory."""
    expected = {r["path"]: r for r in expected}
    recovered = set()
    with tempfile.TemporaryDirectory(prefix="moo-restore-") as tmp:
        destination = Path(tmp)
        with tarfile.open(package, "r:gz") as archive:
            for member in archive:
                safe = _safe_member_path(member.name)
                if not member.isfile():
                    raise ValueError("Preservation package contains a non-regular member")
                if member.name == "preservation-manifest.json":
                    continue
                if member.name not in expected or member.name in recovered:
                    raise ValueError("Unexpected or duplicate preservation package member")
                if member.size != expected[member.name]["bytes"]:
                    raise ValueError("Restored content has an unexpected byte length")
                target = destination.joinpath(*safe.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError("Unreadable preservation package member")
                with source, target.open("wb") as output:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(block)
                row = expected[member.name]
                if target.stat().st_size != row["bytes"] or sha256(target) != row["sha256"]:
                    raise ValueError("Restored content failed fixity verification")
                recovered.add(member.name)
        if recovered != set(expected):
            raise ValueError("Preservation package is incomplete")
    return {"status": "passed", "files_restored": len(recovered), "algorithm": "SHA-256",
            "method": "Extracted into an isolated temporary directory; every restored file compared with the baseline."}


def create_backup(root, report, destination):
    """Create a local package, then actually restore it and compare every hash."""
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination == root or root in destination.parents:
        raise ValueError("Preservation package must be outside the source repository")
    if verify_inventory(root, report)["status"] != "passed":
        raise ValueError("Backup requires a passing fixity check")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="moo-package-") as tmp:
        manifest = Path(tmp) / "preservation-manifest.json"
        manifest.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "created_at": utc_now(),
                                        "algorithm": "SHA-256", "inventory": report["inventory"],
                                        "inventory_sha256": report["inventory_sha256"]}, indent=2) + "\n")
        with tarfile.open(destination, "w:gz") as archive:
            archive.add(manifest, arcname="preservation-manifest.json", recursive=False)
            for row in report["inventory"]:
                _safe_member_path(row["path"])
                archive.add(root / row["path"], arcname=row["path"], recursive=False)
    recovery = restore_and_verify(destination, report["inventory"])
    event = {"at": utc_now(), "event": "backup_and_restoration_test", "status": "passed",
             "package_filename": destination.name, "package_bytes": destination.stat().st_size,
             "package_sha256": sha256(destination), "inventory_sha256": report["inventory_sha256"],
             "storage_scope": "Local execution environment, outside the source repository; not an independent offsite backup.",
             "restoration": recovery}
    report["events"].append(event)
    report["backup"] = event.copy()
    return event


def build_stewardship_page(records, write, layout, origin):
    """Builder integration: emit a public evidence page and downloadable reports."""
    report = read_report(ROOT)
    e = lambda value: escape(str(value), quote=True)
    last = report.get("last_check", {})
    rows = report.get("inventory", [])
    pdfs = [r for r in rows if r["role"] == "original_pdf_access_copy"]
    sources = [r for r in rows if r["role"] == "repository_source_snapshot"]
    backup = report.get("backup", {})
    recovery = backup.get("restoration", {})
    recovery_status = recovery.get("status", "Not yet recorded")
    if backup and backup.get("inventory_sha256") != report.get("inventory_sha256"):
        recovery_status = "Previous baseline only; current baseline requires a recovery test"
    head = '<div class="page-head"><div class="breadcrumb"><a href="index.html">Library</a> / Stewardship</div><div class="eyebrow">Preservation register / Measured evidence</div><h1>Keep the record intact.</h1><p>File fixity, provenance and a tested route to recovery for the Museum of One Digital Archive Library.</p></div>'
    content = head + '<section class="item-section"><h2>Current preservation evidence</h2><dl class="metadata">'
    fields = [("Integrity check", last.get("status", "Not yet recorded")), ("Last measured check", last.get("at", "Not yet recorded")),
              ("Algorithm", "SHA-256"), ("Inventoried files", len(rows)), ("Repository source snapshots", len(sources)),
              ("Unmodified PDF access copies", len(pdfs)), ("Catalogue records", len(records)),
              ("Recovery test", recovery_status),
              ("Files restored and verified", recovery.get("files_restored", 0)),
              ("Recovery test date", backup.get("at", "Not yet recorded"))]
    content += ''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in fields) + '</dl></section>'
    content += '<section class="item-section reading"><h2>What these checks establish</h2><p>A baseline records each source snapshot, editorial JSON dataset and original PDF access copy by relative filename, byte length and SHA-256 digest. Verification compares the current bytes with that baseline and reports missing, added or changed files. The report is excluded from its own inventory so checks can be appended without changing the content baseline.</p><p>The recorded recovery test built a compressed preservation package outside the source repository, extracted it into a new temporary directory and compared every restored file with the baseline. The generated local recovery copy is held outside the source repository. Independent offsite-copy evidence, where recorded below, is separately verified and scoped. Preservation packages are not published as downloads.</p><p>The original deposits remain accessible through <a href="https://zenodo.org/">Zenodo</a>, and the website source is held by the site platform. Those separate services provide source provenance; they do not establish that an independently administered backup of the complete archive has been made. The inventory covers source and catalogue content, rather than a complete disk image or every website dependency.</p><p>Future checks use <code>python scripts/stewardship.py --verify</code>. After reviewed additions, an explicit baseline refresh records the changed scope. A scheduled workflow can run the same verification; a timetable alone is not evidence of a completed check.</p></section>'
    offsite=report.get('offsite_backup') or {}
    if not offsite:
        content+='<p>The local recovery copy is not an independent offsite backup. No external round-trip verification has been recorded for this baseline.</p>'
    if offsite:
        current=offsite.get('inventory_sha256')==report.get('inventory_sha256')
        content+='<section class="item-section"><h2>Independent offsite backup</h2><dl class="metadata">'
        evidence=[('Provider',offsite.get('provider')),('Access',offsite.get('access')),('Current baseline','Matched' if current else 'An earlier baseline; refresh required'),('Round-trip check', 'Downloaded package checksum matched' if offsite.get('downloaded_package_checksum_match') else 'Not verified'),('Restoration',offsite.get('round_trip_restoration',{}).get('status')),('Files restored',offsite.get('round_trip_restoration',{}).get('files_restored')),('Verification recorded',offsite.get('verified_at')),('Package SHA-256',offsite.get('package_sha256'))]
        content+=''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k,v in evidence)+'</dl><p>'+e(offsite.get('scope',''))+'</p><p>The package was retrieved from the independent service and restored into an isolated temporary directory. Every restored content hash was compared with the recorded baseline. Private backup links and account identifiers are omitted from this public register.</p></section>'
    content += '<section class="item-section"><h2>Preservation event log</h2><div class="table-scroll"><table class="inventory-table"><thead><tr><th scope="col">UTC date</th><th scope="col">Event</th><th scope="col">Result</th><th scope="col">Files</th></tr></thead><tbody>'
    for event in reversed(report.get("events", [])):
        count = event.get("file_count", event.get("restoration", {}).get("files_restored", "—"))
        content += f'<tr><td>{e(event["at"])}</td><td>{e(event["event"].replace("_", " "))}</td><td>{e(event["status"])}</td><td>{e(count)}</td></tr>'
    content += '</tbody></table></div><p><a class="text-link" href="metadata/stewardship.json" download>Download the full evidence register (JSON) ↓</a> · <a href="metadata/fixity-sha256.txt" download>SHA-256 manifest ↓</a></p></section>'
    content += '<section class="item-section"><h2>File-level fixity inventory</h2><p>Source-relative filenames identify the preserved content. Digests support byte-level comparison; they do not establish the factual accuracy, authorship or long-term readability of a work.</p><details><summary>Inspect all '+str(len(rows))+' inventoried files</summary><div class="table-scroll"><table class="inventory-table"><thead><tr><th scope="col">Relative filename</th><th scope="col">Bytes</th><th scope="col">SHA-256</th></tr></thead><tbody>'
    content += ''.join(f'<tr><td><code>{e(r["path"])}</code></td><td>{r["bytes"]:,}</td><td><code style="overflow-wrap:anywhere">{e(r["sha256"])}</code></td></tr>' for r in rows)
    content += '</tbody></table></div></details></section>'
    write('stewardship.html', layout('Preservation & stewardship', 'Measured SHA-256 checks, original source files and tested local recovery for the Museum of One Digital Archive Library.', content, 'stewardship.html'))
    write('metadata/stewardship.json', json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    write('metadata/fixity-sha256.txt', ''.join(f'{r["sha256"]}  {r["path"]}\n' for r in rows))
    return ['stewardship.html']


def scheduled_workflow():
    """Suggested workflow; installation and actual run history are separate evidence."""
    return '''name: Archive fixity
on:
  schedule:
    - cron: '17 6 * * 1'
  workflow_dispatch:
permissions:
  contents: read
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python scripts/stewardship.py --verify
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: archive-fixity-evidence
          path: data/stewardship.json
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--inventory', '--refresh', action='store_true', help='Explicitly establish or refresh a reviewed baseline')
    parser.add_argument('--verify', action='store_true', help='Compare bytes with the existing baseline; never rebaseline silently')
    parser.add_argument('--backup', type=Path, help='Explicit private destination outside the project (required with --backup)')
    parser.add_argument('--workflow', action='store_true', help='Print a suggested scheduled GitHub Actions workflow')
    args = parser.parse_args(argv)
    if args.workflow:
        print(scheduled_workflow())
        return 0
    if not (args.inventory or args.verify or args.backup):
        parser.error('Choose --inventory, --verify, or --backup')
    report = read_report(args.root)
    result = 0
    try:
        if args.inventory:
            refresh_inventory(args.root, report)
        if args.verify:
            result = 0 if verify_inventory(args.root, report)['status'] == 'passed' else 1
        if args.backup and result == 0:
            create_backup(args.root, report, args.backup)
    except (OSError, ValueError, tarfile.TarError) as error:
        report['events'].append({'at': utc_now(), 'event': 'operation_failed', 'status': 'failed', 'error_type': type(error).__name__})
        print(f'Preservation operation failed ({type(error).__name__}); existing baseline retained.')
        result = 1
    save_report(args.root, report)
    print(json.dumps({'status': 'passed' if result == 0 else 'failed', 'files': len(report.get('inventory', [])),
                      'last_check': report.get('last_check', {}).get('at'),
                      'restoration': report.get('backup', {}).get('restoration', {}).get('status')}))
    return result


if __name__ == '__main__':
    raise SystemExit(main())
