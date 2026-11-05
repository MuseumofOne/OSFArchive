"""Non-secret Actions summary; full current reconciliation is in the archive."""

import json
from pathlib import Path
from collections import Counter

p = Path(".sync-work/report.json")
if p.exists():
    r = json.loads(p.read_text())
    print("## Website archive reconciliation\n")
    print("Mode:", r.get("mode"))
    print("\nEligible public records:", r.get("eligible_records"))
    print("\nChanges:", dict(Counter(x["action"] for x in r.get("changes", []))))
    print("\nStored uploaded files:", r.get("stored_uploaded_files", 0))
    print("\nFailed attachments:", r.get("failed_attachments", 0))
    print("\nNo Ghost publications or settings are written by this workflow.")
