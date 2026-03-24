import json

import requests

from .config import REQUIRED_PLATFORMS
from .http_client import TagCheckResult, request_with_retry
from .logger import log


def check_ghcr_tag(image_name, tag):
    """Checks if a tag exists on GHCR and returns its platforms.

    Returns:
        tuple: (TagCheckResult, platforms_set_or_error_msg)
    """
    # Get anonymous bearer token
    token_url = f"https://ghcr.io/token?scope=repository:{image_name}:pull"
    try:
        token_resp = request_with_retry(token_url, timeout=30)
        if token_resp.status_code in (403, 404):
            # Package doesn't exist in GHCR (never published)
            return TagCheckResult.NOT_FOUND, None
        if token_resp.status_code != 200:
            msg = f"Failed to get GHCR token: status {token_resp.status_code}"
            log.warn(msg)
            return TagCheckResult.ERROR, msg
        token = token_resp.json().get("token")
        if not token:
            return TagCheckResult.ERROR, "Empty token from GHCR"
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return TagCheckResult.ERROR, f"GHCR token request failed: {e}"

    # Fetch manifest list
    manifest_url = f"https://ghcr.io/v2/{image_name}/manifests/{tag}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": (
            "application/vnd.oci.image.index.v1+json, "
            "application/vnd.docker.distribution.manifest.list.v2+json"
        ),
    }
    try:
        resp = request_with_retry(manifest_url, headers=headers, timeout=30)
        if resp.status_code == 404:
            return TagCheckResult.NOT_FOUND, None
        if resp.status_code != 200:
            return TagCheckResult.ERROR, f"GHCR manifest status {resp.status_code}"

        data = resp.json()
        platforms = set()
        for m in data.get("manifests", []):
            p = m.get("platform", {})
            os_name = p.get("os")
            arch = p.get("architecture")
            variant = p.get("variant")
            if os_name != "linux" or not arch:
                continue
            if arch == "arm" and variant == "v7":
                platform_str = f"{os_name}/{arch}/{variant}"
            else:
                platform_str = f"{os_name}/{arch}"
            if platform_str in REQUIRED_PLATFORMS:
                platforms.add(platform_str)

        return TagCheckResult.FOUND, platforms
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return TagCheckResult.ERROR, f"GHCR manifest request failed: {e}"
