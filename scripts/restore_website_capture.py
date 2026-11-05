"""Offline recovery: decrypt one sealed capture or asset into a private folder.
No private recovery key or passphrase is ever sent to GitHub or the archive.
"""

import argparse, base64, os, subprocess
from pathlib import Path
from website_sync import ROOT, unseal, atomic, encoded, digest


def restore(vault, key, out, password=None):
    out = Path(out).resolve()
    if out.is_relative_to(ROOT.resolve()):
        raise ValueError("Restore outside the public archive repository")
    if password is None:
        r = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                "museum-of-one",
                "-s",
                "moo-website-sync-recovery-v1",
                "-w",
            ],
            capture_output=True,
        )
        if r.returncode:
            raise ValueError("Recovery passphrase is unavailable from macOS Keychain")
        password = r.stdout.strip()
    value = unseal(Path(vault).read_bytes(), Path(key).read_bytes(), password)
    if "bytes_base64" in value:
        data = base64.b64decode(value["bytes_base64"])
        assert digest(data) == value["sha256"]
    else:
        data = encoded(value)
    atomic(out, data)
    os.chmod(out, 0o600)
    return len(data)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vault", type=Path, required=True)
    p.add_argument("--key", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(
        "Recovered bytes:",
        restore(
            a.vault,
            a.key,
            a.output,
            os.environ.get("MOO_RECOVERY_PASSPHRASE", "").encode() or None,
        ),
    )
