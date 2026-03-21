import os
from pathlib import Path

# GitHub
GITHUB_REPO = "caddyserver/caddy"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Derive image names from GITHUB_REPOSITORY (e.g. "CaddyBuilds/caddy-cloudflare")
# This makes the script work for any fork without configuration.
_github_repository = os.environ.get("GITHUB_REPOSITORY", "").lower()

# Docker Hub — override with DOCKERHUB_REPOSITORY_NAME if set, else fall back to repo
OFFICIAL_CADDY_IMAGE = "library/caddy"
CUSTOM_IMAGE = os.environ.get("DOCKERHUB_REPOSITORY_NAME", "") or _github_repository

# GHCR — always matches the GitHub repo
GHCR_IMAGE = os.environ.get("GHCR_IMAGE", "") or _github_repository

# Platforms required in both official and custom images
REQUIRED_PLATFORMS = {
    "linux/amd64",
    "linux/arm64",
    "linux/arm/v7",
    "linux/ppc64le",
    "linux/s390x",
}

# Modules built into the Docker image — must match Dockerfile
MODULES = [
    {"module": "github.com/caddy-dns/cloudflare", "repo": "caddy-dns/cloudflare"},
    {"module": "github.com/WeidiDeng/caddy-cloudflare-ip", "repo": "WeidiDeng/caddy-cloudflare-ip"},
    {"module": "github.com/fvbommel/caddy-combine-ip-ranges", "repo": "fvbommel/caddy-combine-ip-ranges"},
]

# Path to module version tracking file (repo root)
MODULE_VERSIONS_FILE = Path(__file__).resolve().parent.parent.parent / "module-versions.json"

# HTTP retry settings
MAX_RETRIES = 3
BACKOFF_BASE = 2
