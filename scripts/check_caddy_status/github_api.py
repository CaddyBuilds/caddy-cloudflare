import json
import sys

import requests

from .config import GITHUB_REPO, GITHUB_TOKEN
from .http_client import request_with_retry
from .logger import log


def _github_headers():
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def get_latest_caddy_release():
    """Fetches the latest release tag (e.g. 'v2.9.1') from the Caddy GitHub repo."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    log.info(f"Fetching latest release from {url}")

    if not GITHUB_TOKEN:
        log.warn("No GITHUB_TOKEN found, using unauthenticated request (lower rate limit)")

    try:
        response = request_with_retry(url, headers=_github_headers(), timeout=30)
        response.raise_for_status()
        release = response.json()
        tag_name = release.get("tag_name")
        if not tag_name or not tag_name.startswith("v"):
            log.error(f"Invalid or missing 'tag_name' in response: {tag_name}")
            sys.exit(1)
        log.info(f"Latest Caddy release tag: {tag_name}")
        return tag_name
    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP Error fetching latest release: {e.response.status_code} {e}")
        if 400 <= e.response.status_code < 500:
            log.error(f"Response body: {e.response.text[:500]}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        log.error(f"Network error fetching latest release: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log.error(f"Error decoding GitHub API JSON: {e}")
        sys.exit(1)


def get_latest_commit_sha(repo):
    """Fetches the latest commit SHA for a GitHub repo's default branch.
    Returns None on failure (non-fatal — caller decides how to handle).
    """
    url = f"https://api.github.com/repos/{repo}/commits?per_page=1"
    try:
        response = request_with_retry(url, headers=_github_headers(), timeout=30)
        response.raise_for_status()
        commits = response.json()
        if commits and isinstance(commits, list) and len(commits) > 0:
            return commits[0].get("sha")
        return None
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        log.warn(f"Failed to fetch latest commit for {repo}: {e}")
        return None
