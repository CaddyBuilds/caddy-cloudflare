
# Caddy Cloudflare

[![Build](https://github.com/caddybuilds/caddy-cloudflare/actions/workflows/check-caddy-release.yml/badge.svg)](https://github.com/caddybuilds/caddy-cloudflare/actions/workflows/check-caddy-release.yml)
[![License: MIT](https://img.shields.io/github/license/caddybuilds/caddy-cloudflare)](LICENSE)

> A fully integrated Caddy Docker image featuring Cloudflare DNS-01 ACME validation

Automated, multi-platform Docker builds of [Caddy](https://caddyserver.com/) with Cloudflare DNS and proxy IP trust modules baked in.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Included Modules](#included-modules)
- [Usage](#usage)
  - [Docker Pull](#docker-pull)
  - [Caddyfile Examples](#caddyfile-examples)
- [Configuration](#configuration)
  - [Creating a Cloudflare API Token](#creating-a-cloudflare-api-token)
  - [ACME DNS Challenge](#acme-dns-challenge)
- [Tags](#tags)
- [Platform Support](#platform-support)
- [Troubleshooting](#troubleshooting)
- [How It Works](#how-it-works)
- [Building Your Own Image](#building-your-own-image)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Automated Builds** -- Daily checks for new Caddy releases with automatic image builds.
- **Module Update Detection** -- Tracks upstream module commits and rebuilds when dependencies change.
- **Base Image Tracking** -- Rebuilds when the official Caddy image is republished with OS or Go toolchain fixes.
- **Cloudflare DNS-01 Integration** -- Automatic SSL certificate management via DNS challenges.
- **Cloudflare IP Trust** -- Real client IPs preserved when proxying through Cloudflare.
- **Multi-Platform** -- Supports `amd64`, `arm64`, `arm/v7` (Raspberry Pi), `ppc64le`, and `s390x`.
- **Alpine-Based** -- Built on the official Caddy image, which uses Alpine Linux. A `slim` variant drops the stock binary.
- **Fork-Friendly** -- Image names derived automatically from your GitHub repository.

## Quick Start

Pull the image and set up a `docker-compose.yml`:

```yaml
services:
  caddy:
    image: ghcr.io/caddybuilds/caddy-cloudflare:latest
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - $PWD/Caddyfile:/etc/caddy/Caddyfile
      - $PWD/site:/srv
      - caddy_data:/data
      - caddy_config:/config
    environment:
      - CLOUDFLARE_API_TOKEN=your_cloudflare_api_token

volumes:
  caddy_data:
    external: true
  caddy_config:
```

> Defining the data volume as [external](https://docs.docker.com/compose/compose-file/compose-file-v3/#external) ensures `docker-compose down` does not delete it. Create it manually with `docker volume create caddy_data`.

Replace `your_cloudflare_api_token` with your actual token. See [Creating a Cloudflare API Token](#creating-a-cloudflare-api-token) for setup instructions, and [Caddyfile Examples](#caddyfile-examples) for configuration samples.

## Included Modules

These modules are compiled into Caddy at build time using [xcaddy](https://github.com/caddyserver/xcaddy). No additional installation is needed.

| Module | Purpose | Repository |
|--------|---------|------------|
| `caddy-dns/cloudflare` | DNS-01 ACME challenge provider for Cloudflare | [caddy-dns/cloudflare](https://github.com/caddy-dns/cloudflare) |
| `caddy-cloudflare-ip` | Automatically trust Cloudflare proxy IP ranges for correct client IPs | [WeidiDeng/caddy-cloudflare-ip](https://github.com/WeidiDeng/caddy-cloudflare-ip) |
| `caddy-combine-ip-ranges` | Combine IP ranges from multiple sources (e.g. Cloudflare plus your own) for `trusted_proxies` | [fvbommel/caddy-combine-ip-ranges](https://github.com/fvbommel/caddy-combine-ip-ranges) |
| `caddy-ratelimit` | Rate limit requests per real client IP, even behind Cloudflare's proxy | [mholt/caddy-ratelimit](https://github.com/mholt/caddy-ratelimit) |

## Usage

### Docker Pull

```sh
docker pull ghcr.io/caddybuilds/caddy-cloudflare:latest
docker pull caddybuilds/caddy-cloudflare:latest
```

See [Quick Start](#quick-start) for a full docker-compose setup.

### Caddyfile Examples

#### Global DNS Configuration

Set the ACME DNS challenge provider globally so it applies to all sites:

```
{
  acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}
}

example.com {
    root * /usr/share/caddy
    file_server
    encode gzip
}

another-example.com {
    reverse_proxy localhost:8080
}
```

#### Per-Site DNS Configuration

Configure DNS challenge individually per site:

```
example.com {
    root * /usr/share/caddy
    file_server
    encode gzip

    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
}

another-example.com {
    reverse_proxy localhost:8080

    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
}
```

#### Cloudflare IP Trust

Trust Cloudflare's proxy IPs to preserve real client IPs in logs and headers:

```
{
  acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}

  servers {
    trusted_proxies cloudflare
    client_ip_headers Cf-Connecting-Ip
  }
}

example.com {
    root * /usr/share/caddy
    file_server
    encode gzip
}
```

With this setup:
- Requests proxied through Cloudflare will correctly populate `X-Forwarded-For` headers.
- Access logs will show the **real client IP** instead of Cloudflare's edge server IPs.

#### Cloudflare-Only Access

Reject requests that reach your origin directly instead of through Cloudflare's proxy:

```
{
  acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}

  servers {
    trusted_proxies cloudflare
    client_ip_headers Cf-Connecting-Ip
  }
}

example.com {
    @notCloudflare vars {vars.client_ip} {remote_host}
    abort @notCloudflare

    reverse_proxy localhost:8080
}
```

With this setup:
- Caddy only reads `Cf-Connecting-Ip` when the connecting IP is in Cloudflare's published ranges, which `caddy-cloudflare-ip` keeps up to date. For any other connection the client IP equals the connecting IP, so the matcher catches it. No hardcoded IP list is needed ([approach suggested on the Caddy forum](https://caddy.community/t/why-remote-ip-can-not-parse-cloudflare-or-cloudfront-ip-which-from-a-plugin/33351)).
- Direct requests have their connection closed. Use `respond @notCloudflare 403` instead of `abort` if you prefer an explicit error.
- Certificate issuance is unaffected, since the DNS-01 challenge does not use inbound HTTP.
- Not for [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) setups: tunneled traffic arrives from your local `cloudflared`, not Cloudflare's IPs, so every request would be rejected.

Requires an image from `v2.11.0` or later (see [Tags](#tags)). Add the matcher to each site block you want to protect. This checks the source IP only; for stronger guarantees, also restrict ports 80/443 to Cloudflare at your firewall, or use [Authenticated Origin Pulls](https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/).

#### Rate Limiting

Limit how many requests each visitor can make, keyed on their real IP rather than Cloudflare's:

```
{
  acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}
  order rate_limit before basic_auth

  servers {
    trusted_proxies cloudflare
    client_ip_headers Cf-Connecting-Ip
  }
}

example.com {
    rate_limit {
        zone per_client {
            key    {client_ip}
            events 100
            window 1m
        }
    }

    reverse_proxy localhost:8080
}
```

With this setup:
- Each client gets 100 requests per minute; further requests receive `429 Too Many Requests` with a `Retry-After` header.
- `{client_ip}` resolves to the visitor's IP via `trusted_proxies cloudflare`. Without it, every visitor behind the same Cloudflare edge would share one limit.
- `order rate_limit before basic_auth` is required because `rate_limit` is not a standard Caddy directive.

Older images do not include this module and will fail with `rate_limit is not a registered directive`; check yours with the command in [Verifying Modules](#verifying-modules). See the [module documentation](https://github.com/mholt/caddy-ratelimit) for multiple zones, request matchers, and distributed limits.

## Configuration

### Creating a Cloudflare API Token

To use the Cloudflare DNS challenge provider, create an API token with the necessary permissions:

1. **Log in to Cloudflare** at [dash.cloudflare.com](https://dash.cloudflare.com).

2. **Navigate to API Tokens**:
   - Click your profile icon > "My Profile" > "API Tokens" in the sidebar.

3. **Create a Custom Token**:
   - Click "Create Token", then under "Custom Token" click "Get started".

4. **Configure Token Permissions**:
   - Name: `Caddy DNS-01 Challenge` (or similar)
   - Permissions:
     - **Zone - Zone - Read**: Allows reading DNS zones.
     - **Zone - DNS - Edit**: Allows editing DNS records (required for DNS-01 challenge).

5. **Specify Zone Resources**:
   - **Include - All Zones**: For access to all your zones, or
   - **Include - Specific Zone**: Select only the zone(s) you need.

6. **Create and Store the Token**:
   - Review your settings, click "Create Token", and copy the generated token to a secure location.

7. **Set the Environment Variable**:
   - Add `CLOUDFLARE_API_TOKEN` to your deployment environment. See [Quick Start](#quick-start) for the docker-compose example.

### ACME DNS Challenge

To configure the [ACME DNS challenge](https://caddyserver.com/docs/automatic-https#dns-challenge) provider for all ACME transactions, add the following to your Caddyfile:

```
{
   acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}
}
```

This is equivalent to specifying the provider in the [tls directive's ACME issuer](https://caddyserver.com/docs/caddyfile/directives/tls#acme) configuration. See [Caddyfile Examples](#caddyfile-examples) for full samples.

## Tags

The image is available on [GitHub Container Registry](https://github.com/caddybuilds/caddy-cloudflare/pkgs/container/caddy-cloudflare) and Docker Hub. There are two images, default and slim, each under a few tags:

| Tags | Image |
|------|-------|
| `latest`, `<version>`, `<major>.<minor>`, `<major>` | Default |
| `alpine`, `<version>-alpine`, `<major>.<minor>-alpine`, `<major>-alpine` | Default (same image, see below) |
| `slim`, `<version>-slim`, `<major>.<minor>-slim`, `<major>-slim` | Slim |

`<version>` pins a release (e.g. `2.11.7`), `<major>.<minor>` follows the latest patch (e.g. `2.11`) and `<major>` the latest release (e.g. `2`). Slim tags exist from `2.11.7` onward.

### Default or slim?

Both run the same Caddy binary with the same modules. They differ only in the image underneath.

| | Default | Slim |
|---|---|---|
| Built on | The official [Caddy image](https://hub.docker.com/_/caddy) | [caddy-base](https://github.com/CaddyBuilds/caddy-base#the-caddy-base-image): the official image without its Caddy binary |
| Download size (amd64) | about 43 MB | about 24 MB |
| Caddy binaries inside | Two: the stock one stays in a lower layer, ours replaces it on top | One: ours |
| Rebuilt for base fixes when | The official Caddy image is republished | Alpine is republished (caddy-base rebuilds, then slim follows) |

Everything else is the same: Alpine, packages, default Caddyfile, `/data` and `/config`, ports, command, platforms, and permission to bind ports 80 and 443 as a non-root user.

Use **slim** for a smaller image. Use **default** if you want to stay on the Docker Official Image exactly as Caddy ships it.

### Why `alpine` tags point to the same image

This follows the official Caddy image. On Linux, `caddy:latest`, `caddy:2.11.7` and `caddy:2.11.7-alpine` are all the same Alpine image. The plain tags also include Windows builds, which is the only reason both exist. We only build Linux images, so the `-alpine` tags are aliases: a setup that uses `caddy:2.11.7-alpine` can switch to `caddy-cloudflare:2.11.7-alpine` without changing anything else.

> **Note:** Starting from `v2.11.0`, the image includes the `caddy-cloudflare-ip` and `caddy-combine-ip-ranges` modules by default.

### Why did a digest change?

Images are rebuilt without a new Caddy version when a module gets new commits or a base image is republished with OS or Go fixes (the official Caddy image for the default tags, the caddy-base image for `slim`). Each rebuild is logged under **Rebuilds** in that version's [GitHub Release](https://github.com/caddybuilds/caddy-cloudflare/releases), and the reason is stored in the image labels:

```sh
docker inspect --format '{{ index .Config.Labels "caddy-build.reason" }}: {{ index .Config.Labels "caddy-build.details" }}' ghcr.io/caddybuilds/caddy-cloudflare:latest
```

## Platform Support

The image is built for the following platforms:

- **linux/amd64** -- Standard x86_64 (desktops, servers)
- **linux/arm64** -- ARM 64-bit (modern ARM servers, Apple Silicon via emulation)
- **linux/arm/v7** -- ARM 32-bit (Raspberry Pi 3+)
- **linux/ppc64le** -- 64-bit PowerPC Little Endian
- **linux/s390x** -- 64-bit IBM System z

### Alpine

Both images are built on [Alpine Linux](https://alpinelinux.org/): the default through the official Caddy image, slim through caddy-base. Alpine uses musl libc instead of glibc, which may cause compatibility issues with some software. Additional tools (git, bash, etc.) are not included by default.

### Raspberry Pi

The `linux/arm/v7` build supports Raspberry Pi 3 and later. No special configuration is needed beyond having Docker installed on a compatible OS (such as Raspberry Pi OS).

## Troubleshooting

### DNS Resolution Errors

If you encounter `solving challenges: presenting for challenge: adding temporary record for zone xyz.: got error status: HTTP 403`, try setting custom DNS resolvers:

```
tls {
    dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    resolvers 1.1.1.1
}
```

### Verifying Modules

To confirm the bundled modules are loaded:

```sh
docker run --rm ghcr.io/caddybuilds/caddy-cloudflare:latest caddy list-modules | grep -E "cloudflare|combine|rate_limit"
```

### Official Resources

- [caddy-dns/cloudflare troubleshooting guide](https://github.com/caddy-dns/cloudflare?tab=readme-ov-file#troubleshooting)
- [Caddy ACME DNS challenge docs](https://caddyserver.com/docs/automatic-https#dns-challenge)

## How It Works

The build pipeline is fully automated via GitHub Actions and shared with the other CaddyBuilds images through [caddy-base](https://github.com/CaddyBuilds/caddy-base). This repo holds only what is specific to this image: the `Dockerfile` (module list), `caddy-image.json` (title, description, verified module) and two thin workflows that call the shared ones.

1. **Daily release check** -- A scheduled workflow queries the GitHub API for new [Caddy releases](https://github.com/caddyserver/caddy/releases) and verifies the official Docker image is available with all required platforms before triggering a build.

2. **Module update detection** -- The pipeline reads the module list from the `Dockerfile` and tracks each module's latest commit SHA in `module-versions.json`. If any module has new commits, a rebuild is triggered even without a new Caddy release.

3. **Base image tracking** -- Docker Official Images republish existing Caddy versions for base OS and Go toolchain fixes. The check compares when the official image was last pushed with when ours was built, and rebuilds if upstream is newer.

4. **Multi-platform build** -- The shared workflow builds the image for all supported architectures. Images are pushed to GitHub Container Registry (primary) and optionally Docker Hub.

5. **Fork-friendly** -- Image names are derived from the `GITHUB_REPOSITORY` environment variable, so forks produce correctly named images without any configuration changes.

6. **Failure notifications** -- If a build fails, a GitHub issue is automatically created for visibility.

## Building Your Own Image

### Prerequisites

- GitHub account
- Docker Hub account (optional, for pushing to Docker Hub)
- GitHub Secrets configured:
  - `GITHUB_TOKEN` (automatically available in GitHub Actions)
  - `DOCKERHUB_USERNAME` (optional)
  - `DOCKERHUB_TOKEN` (optional)
  - `DOCKERHUB_REPOSITORY_NAME` (optional, to customize the Docker Hub repository name)

### Setup Instructions

1. **[Fork this repository](https://github.com/caddybuilds/caddy-cloudflare/fork)** to your GitHub account.

2. **Set up GitHub Secrets** (optional, for Docker Hub):
   - Navigate to `Settings` > `Secrets and variables` > `Actions`.
   - Add `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, and optionally `DOCKERHUB_REPOSITORY_NAME`.

3. **Enable GitHub Actions**:
   - Go to the `Actions` tab. If prompted, click "I understand my workflows, go ahead and enable them".

4. **Customize the modules** (optional):
   - Add or change `--with` lines in the `Dockerfile`; the daily check follows the list from there. Adjust the title and description in `caddy-image.json` if you like.

5. **Trigger a build** (optional):
   - In the `Actions` tab, select `Build and Push Docker Image` and click `Run workflow`.

6. **Pull your image**:
   ```sh
   docker pull ghcr.io/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME:latest
   ```

Use the image in your docker-compose setup as shown in the [Quick Start](#quick-start), replacing the image name with your own.

## Contributing

Feel free to open issues or submit pull requests if you have any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
