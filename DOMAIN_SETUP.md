# GitHub Pages domain setup

Repository target: `MuseumofOne/OSFArchive`

1. Use a public repository so GitHub Pages hosting is available on the free plan.
2. Enable Settings → Pages → Build and deployment → GitHub Actions.
3. Set the custom domain to `archive.museumofone.art`.
4. At the domain’s DNS provider, add or update this record:

| Type | Name | Target |
| --- | --- | --- |
| CNAME | archive | museumofone.github.io |

Keep the main `museumofone.art` website records unchanged. Remove any conflicting record for the archive hostname. GitHub’s certificate provisioning and Enforce HTTPS follow successful DNS validation.

The generated `dist/CNAME` is already set. The build uses `https://archive.museumofone.art` for canonical and structured-data URLs.

No DNS records have been changed by this build. The previous pending Sites custom-domain binding was removed when GitHub Pages was selected.
