# Open on either Mac

Local-only workflow. No deployment, Git push, Ghost upload or DNS operation is performed by portable.py.

Use the explicitly chosen archive folder on the connected drive. Its name and mount point may differ. Never choose a copy by date. Current locations are examples, not bindings. The starting released ZIP is 1.12.8 in `Ghost Theme - 2026-11-05`, superseding the older November 3 folder. Concurrent work then advanced the source to 1.12.9; source/ZIP/receipts require reconciliation before declaring that release authoritative. Consult PORTABILITY-VALIDATION.md. The verified older-release recovery receipt is outside this public repository and must not silently replace newer work.

```sh
cd "/your/selected drive/Digital Archive Library"
python3 scripts/portable.py --root "$PWD" doctor
```

Doctor reports actual macOS, CPU, Python, Node, home and Desktop. Desktop is discovered with macOS Foundation; `MOO_DESKTOP` explicitly overrides it. Install a native Python >=3.12 (3.13 recommended) and Node >=22 (22 is the theme target) from their official distributions if diagnostics show missing dependencies. Git is required. No machine-specific executable path is stored. Never copy `.venv` between computers. Rename any copied environment outside the project, then run setup. Exact Python dependency graph is in requirements-local.lock; each Mac resolves native wheels separately. Theme package-lock and vendored tool/vendor hash locks remain authoritative. Browser release QA additionally requires the pinned optional requirements-theme.lock and its matching Chromium; create a separate local environment, install that lock, then run `python -m playwright install chromium`. Set `PYTHON` to that environment’s Python before `npm run zip`. Missing browser prerequisites fail the full gate; this is separate from public builds.

## Verify a drive mirror before use

Obtain the trusted public release/content manifest and its SHA-256 via the private handoff, separately from the candidate mirror. Identity marker alone is insufficient proof. The manifest covers source, original access PDFs, tools, documentation, dist and the public website capture cache. Git HEAD must match and Git objects pass fsck. Private `.sync-work` vault/state, machine environments, audit evidence and Git objects are excluded from the content hash inventory; retain Git history in the copy nonetheless.

```sh
MANIFEST="/private/handoff/archive-portable-manifest.json"
SHA="the independently checked SHA-256"
python3 scripts/portable.py --root "$PWD" --manifest "$MANIFEST" --sha256 "$SHA" verify
python3 scripts/portable.py --root "$PWD" --manifest "$MANIFEST" --sha256 "$SHA" setup
python3 scripts/portable.py --root "$PWD" --manifest "$MANIFEST" --sha256 "$SHA" build
python3 scripts/portable.py --root "$PWD" --manifest "$MANIFEST" --sha256 "$SHA" check
python3 scripts/portable.py --root "$PWD" --manifest "$MANIFEST" --sha256 "$SHA" preview
```

Preview binds only 127.0.0.1:8765, serves only dist, and rejects symlink escapes. Stop with Control-C. Credentials are not required for reading, discovery, PDFs, metadata generation, preview or builds. These commands never pull remote state or reconcile the live site. Build/check remove publishing-related environment overrides and preserve the production origin. A build may change generated files if public cached inputs changed; verification then fails until the difference is reviewed. Never refresh simply to suppress a failure.

After reviewed local changes, create a NEW manifest outside the public project:

```sh
python3 scripts/portable.py --root "$PWD" --output "/private/handoff/new-reviewed-manifest.json" seal
```

Seal prints the hash. It never replaces an existing manifest. Transfer the hash independently; compare both source and destination against it before work. Use one explicitly selected root; the CLI rejects an argument pointing at a different copy from its own script. Divergence means stop, preserve both copies, compare inventories and resolve intentionally. No sync/merge/deletion is automatic. A simulated mount is not physical drive verification.

## Theme and private local configuration

Optional per-Mac JSON: `~/.config/museum-of-one/local.json`, or `--config /explicit/private/local.json`. Do not put it in the public repository:

```json
{"theme_directory":"Ghost Theme - 2026-11-05","theme_receipt_sha256":"trusted receipt hash from private handoff"}
```

`theme_folder` can override the complete external path. `--theme-folder` overrides either configuration. No fallback searches through Desktop dates. `theme-verify` verifies source file sets, ZIP CRC and every ZIP/source hash, ZIP hash receipt and LATEST. Keep the entire Desktop folder together, including audit evidence; never restore just a ZIP over another source tree.

```sh
python3 scripts/portable.py --root "$PWD" --manifest "$MANIFEST" --sha256 "$SHA" theme-verify
python3 scripts/portable.py --root "$PWD" --manifest "$MANIFEST" --sha256 "$SHA" --output "/selected private drive/Ghost Backups/theme-portable-reviewed" theme-save
python3 scripts/portable.py --root "$PWD" --manifest "$MANIFEST" --sha256 "$SHA" --bundle "/selected private drive/Ghost Backups/theme-portable-reviewed" --output "$HOME/Desktop/Ghost Theme - restored reviewed" theme-restore
```

The last example assumes a standard Desktop: use Doctor's actual Desktop or MOO_DESKTOP for redirected Desktops. Restore verifies an independently trusted receipt hash in the private configuration, then writes only a nonexistent destination. It refuses overwrites, even of older versions. The private receipt, not modification time, identifies the authoritative revision; do not silently substitute an older receipt. Preserve the existing Desktop folder and select the new verified folder explicitly if both exist. No theme installation occurs. Source, uploadable ZIP, checksums, LATEST and release evidence are copied and verified together. Use existing `npm run zip -- /private/new-candidate.zip` inside theme for future packaging; it runs the full release gate and fails if browser prerequisites are absent. Do not bypass this gate or overwrite the current package.

## Private systems and recovery

Never copy credentials into this repo, its public cache or dist. Configure publishing credentials, GitHub authorization and environment permissions separately on each Mac only when publishing is explicitly authorized. Public encryption key in config is not the private recovery key. Private recovery-key passphrase, Keychain items, GitHub private integration installation/token and private-database access remain separate. `website_state.py` and live sync are publishing/remote operations, not setup requirements.

A machine/drive-bound private controller or database must be migrated using its own documented identity, integrity and authorization process: preserve encrypted source and its manifest, export supported settings, provision the target Keychain/account permissions, verify identity and database hashes, test read-only access, then switch deliberately with rollback. This portability tool never launches private controllers, changes bindings, substitutes databases, creates an empty database or disables integrity checks. Missing private access blocks that private integration only. Complete Ghost backups, recovery manifests and private evidence remain outside this repository in the explicitly selected private backup area.

For recovery, retain both the working copy and independent backup, verify the trusted manifest on the restored project, recreate its environment, verify theme bundle separately and test preview before considering any later publication. Git history should be copied intact and fsck checked; a content manifest is not a complete machine backup. Physical MacBook Air, Mac mini, drive filesystem and private credentials require separate on-device tests; consult the portability validation report for measured local results.
