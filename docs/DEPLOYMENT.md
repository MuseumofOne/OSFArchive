# Deployment, installation and rollback

**Current publication:** the archive and native Ghost 1.12.0 entrance were published on 4 November 2026 after explicit authorization. See [current deployment status](../DEPLOYMENT-STATUS.md) for live addresses, HTTPS evidence, tests and the exact CMS scope. The staging authorization notes below record the earlier preparation phase; they are not a current deployment hold.

## Staging status and authorization

The implementation is staged on `integration/ghost-archive-consolidation`; production deployment, DNS changes and overwriting live services are not authorized by the current task. The commands below are a runbook for a later authorized release, not actions already performed.

The historical handoff inspection recorded:

- Remote repository: `https://github.com/MuseumofOne/OSFArchive`.
- Repository visibility: private. GitHub Pages: disabled.
- Repository creation/visibility/Pages administration previously returned HTTP 403 to the connected integration, despite code-write access.
- Intended origin: `https://archive.museumofone.art`; the hostname was not resolving.
- Ghost remains the existing institutional website at `https://www.museumofone.art`.
- The earlier cloud environment could not access the Mac Desktop or T7. That filesystem limitation is now resolved: the archive is verified at `/Volumes/T7-Shield/Digital Archive Library`, and the actual Desktop 1.11.10 theme was inspected as the prepared 1.12.0 baseline.

Repository administration and public hosting must be rechecked before release; the historical access failure is not proof of current account state. A repository owner must provide appropriate administration access or perform the visibility/Pages settings steps when needed. Do not purchase hosting, create a second CMS or assume a private repository is eligible for free Pages. GitHub's current plan terms and usage limits apply. Publishing the repository also publishes its history: review the full history and files for confidential material before changing visibility.

## Pre-release package

1. Preserve the current main revision, source package and the original functioning Ghost theme ZIP. The archive inspection baseline is `31dec12d74e0147ac1b50a4fbd22b52de38da33b`; select the actual latest successful release when rolling back later.
2. Inspect the branch diff. Run the build, static checks, Python/Node tests and fixity verification described in [MAINTENANCE.md](MAINTENANCE.md). Resolve failures; do not silently rebaseline unexpected content changes.
3. Check `SITE_ORIGIN` and the generated canonicals, JSON-LD, sitemap, asset paths and `dist/CNAME`. The default origin is the intended custom hostname. For a temporary GitHub project preview, rebuild with its full project origin; do not publish mismatched custom-domain canonicals accidentally.
4. Verify that only public material is present in the source, history, generated output and integration feed. Keep credentials and private storage receipts outside the repository.
5. Record the tested commit, test results, environment limits and rollback reference. Browser/mobile/accessibility and live CORS checks remain separate from local static checks.

## GitHub Pages release

After explicit release authorization and repository-owner access:

1. Make the reviewed repository public if required for the free GitHub Pages plan.
2. In repository **Settings → Pages → Build and deployment**, select **GitHub Actions**.
3. Set the repository `SITE_ORIGIN` variable to `https://archive.museumofone.art` for the custom-domain release. The builder already defaults to that origin.
4. Release the tested branch to `main` using the institution's chosen review process. `.github/workflows/pages.yml` validates and packages `dist/`, then configures and deploys Pages. Its existing `configure-pages` enablement step cannot overcome missing repository-administration permission. Main pushes and manual workflow dispatch can publish; do not use either before authorization.
5. Inspect both the validation job and deployment job. A successful artifact upload is not a successful deployment. Record the final deployment URL and commit.

The integrity workflow verifies content on relevant pushes/manual dispatch. Its presence is not evidence of a scheduled backup service or a completed independent restoration.

## DNS and HTTPS

The archive uses a subdomain of the already-owned domain; no additional domain purchase is needed. Do not edit production DNS until explicitly authorized. Once authorized and Pages is ready, set the custom domain to `archive.museumofone.art` in Pages and configure the DNS record:

| Type | Host/name | Target |
| --- | --- | --- |
| CNAME | `archive` | `museumofone.github.io` |

Preserve the main website's existing records. Review a conflicting record at the archive hostname before changing it. Follow GitHub's domain-verification guidance and certificate provisioning process; enable **Enforce HTTPS** after validation succeeds. The generated `dist/CNAME` already names `archive.museumofone.art`. Do not add server-specific header or redirect files expecting GitHub Pages to apply them automatically.

After DNS propagation, verify the actual HTTPS origin, certificate, canonical URLs, asset paths, reader workers, PDFs, sitemap and robots response. Fetch `metadata/research-discovery.v2.json` from a browser running on the actual Ghost origin; keep the v1 endpoint compatible where used. Confirm public CORS behavior and safe network-failure fallback rather than assuming the custom hostname behaves like another GitHub URL.

## Ghost entrance: preparation and installation

The actual latest Desktop baseline has now been inspected, and the native 1.12.0 revision is prepared locally. The production installation and hosting hold remain in force. See [GHOST_INTEGRATION.md](GHOST_INTEGRATION.md) for current capability and exact validation limits.

1. Preserve the verified original 1.11.10 source/ZIP and current active theme identity before promoting a replacement. Keep the current theme source, candidate ZIP, checksums and evidence together in the existing Desktop theme folder; complete Ghost backups belong separately outside the public archive repository.
2. Inspect all templates, partials, assets, package requirements, routes, navigation, search, structured data and existing archive/Omeka links. Record representative baseline pages and mobile/search behavior. The source and local settings snapshot confirm the existing `/digital-archive-library/` page entrance. Its prepared slug-specific native template needs no new route. No `/archive/` alias has been added.
3. Review the prepared native theme entrance with institutional context, supported collections, verified records, direct archive links and the v2 shared discovery and passage snapshots. Replace all active Omeka links, embeds and metadata destinations with the new archive, keeping former URLs only as migration history. Keep Ghost's header/footer/mobile conventions and global search. Do not use an iframe or duplicate navigation entries. Bundle a validated index snapshot for fallback and mount the entrance controller only on the native container; global search also consumes the shared module.
4. Review the extracted token specification in the prepared theme's `docs/ARCHIVE-DESIGN.md`. Keep the independent archive's own runtime CSS and archival hierarchy.
5. Validate with the Ghost-compatible theme checker for the installed Ghost version, template checks and a representative staging browser test. Check existing pages, publication metadata, navigation, search, mobile menu and archive results. Do not invent a successful Ghost test result if no staging runtime is available.
6. Produce the complete updated theme ZIP with a diff and installation notes only after its ordinary full release gate passes. A separately encoded review/transfer candidate must be marked prepared and explicitly record the unexecuted full legacy browser gate and unavailable exact Ghost runtime; it is not a deployment-ready package. Only after explicit authorization, upload/install it through Ghost's theme administration. If a Ghost page, navigation change or routes update is required, preserve its existing configuration and apply only the tested change.
7. Verify both directions of navigation, active states, accessibility, native entrance, canonical destinations and bundled fallback. Remote feed refresh remains disabled until actual public HTTPS/CORS checks pass, then requires a separately reviewed configuration revision.

The archive remains independently usable if Ghost is unavailable. The Ghost entrance retains a useful link and bundled index if the archive refresh fails.

## Rollback and failure recovery

If archive validation fails, do not deploy. Retain the previous public release and fix the branch. If Pages administration or deployment fails, preserve the validated artifact and job evidence; resolve access/settings rather than declaring the site live.

For a bad archive release, identify the last tested commit and review a revert or release of that revision. Rebuild with the same canonical origin, run all checks and redeploy through the normal workflow after authorization. Prefer a reversible commit over force-pushing or deleting history. Preserve newly issued stable identifiers and document any withdrawn record rather than silently recycling its accession.

For a Ghost regression, reactivate/upload the preserved previous working theme. Restore only the specific changed route/navigation configuration if necessary. Do not restore or overwrite publication content as a theme rollback. Confirm representative pages, global search and mobile navigation after recovery.

DNS rollback is a separate authorized change. Record the prior values before any edit. Do not remove a previously functioning custom domain or modify the main site's DNS to fix an unrelated build failure.

Recover missing/corrupt archive source or PDFs from a verified backup into an isolated location, compare all recorded hashes, restore the source checkout/release dependencies and run the complete build checks before publishing. A successfully restored content package is not proof that DNS, GitHub administration or Ghost has been restored.

## Release acceptance evidence

Record actual results for static build/exports, public HTTPS, canonical and sitemap checks, record/reader URLs, both sites' navigation/search, cross-origin index refresh, mobile/keyboard behavior and the active Ghost package. Any missing source access, live service access, browser environment or external response must remain an explicit limitation. This runbook does not certify completion of those checks.
