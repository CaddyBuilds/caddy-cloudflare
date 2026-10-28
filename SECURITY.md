# Security Policy

## Supported versions

Only images for the latest Caddy release are rebuilt: `latest`, `2`, `2.Y`, `2.Y.Z` and
their `-alpine` and `-slim` variants. Tags for older Caddy versions stay published but no
longer receive fixes, so upgrade to the latest release to get them.

## How fixes reach the images

These images are Caddy plus its DNS module, exactly as upstream ships them. We don't pin
or patch dependency versions; fixes arrive through rebuilds.

- **Go modules inside the `caddy` binary** (for example `golang.org/x/net`) are fixed when
  Caddy or the module releases an update. The daily check builds new Caddy releases and
  module commits automatically.
- **Alpine packages** are fixed when the base image is republished. `slim` follows Alpine
  through [caddy-base](https://github.com/CaddyBuilds/caddy-base) and is usually rebuilt the
  day after. The default tags follow the official `caddy` image and are rebuilt once it is
  republished, which can take longer. Use `slim` for faster OS fixes.

## Known vulnerabilities

[Trivy](https://trivy.dev) scans the published `latest` and `slim` images daily and after
every build. The summary of the latest
[Scan Images run](https://github.com/CaddyBuilds/caddy-cloudflare/actions/workflows/scan-images.yml)
lists every known finding with the version that fixes it. A finding listed there is already
known and will clear on the rebuild that picks up the fix, so there is no need to open an
issue for it.

## Reporting a vulnerability

- **In Caddy, the DNS module, a Go dependency or Alpine:** report it to that project, for
  example through [Caddy's security policy](https://github.com/caddyserver/caddy/security/policy).
  Once upstream releases a fix, the images pick it up automatically.
- **In this repository** (the `Dockerfile`, the workflows, or how images are built and
  published): report it privately with **Report a vulnerability** on the
  [Security tab](https://github.com/CaddyBuilds/caddy-cloudflare/security). Please don't open a public
  issue.
