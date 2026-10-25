import json

import requests

from .config import REQUIRED_PLATFORMS
from .http_client import TagCheckResult, request_with_retry
from .logger import log
from .timeutil import parse_timestamp

INDEX_ACCEPT = (
    "application/vnd.oci.image.index.v1+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json"
)
MANIFEST_ACCEPT = (
    "application/vnd.oci.image.manifest.v1+json, "
    "application/vnd.docker.distribution.manifest.v2+json"
)


_tokens = {}


def _get_pull_token(image_name):
    """Gets an anonymous GHCR pull token, cached per image for the run.

    Returns:
        tuple: (token, error). (None, None) means the package was never published.
    """
    if image_name in _tokens:
        return _tokens[image_name], None

    token_url = f"https://ghcr.io/token?scope=repository:{image_name}:pull"
    try:
        token_resp = request_with_retry(token_url, timeout=30)
        if token_resp.status_code in (403, 404):
            return None, None
        if token_resp.status_code != 200:
            return None, f"GHCR token request failed: {token_resp.status_code}"
        token = token_resp.json().get("token")
        if not token:
            return None, "Empty token from GHCR"
        _tokens[image_name] = token
        return token, None
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return None, f"GHCR token request failed: {e}"


def check_ghcr_tag(image_name, tag):
    """Checks if a tag exists on GHCR and returns its platforms.

    Returns:
        tuple: (TagCheckResult, platforms_set_or_error_msg)
    """
    token, error = _get_pull_token(image_name)
    if not token:
        return (TagCheckResult.ERROR, error) if error else (TagCheckResult.NOT_FOUND, None)

    # Fetch manifest list
    manifest_url = f"https://ghcr.io/v2/{image_name}/manifests/{tag}"
    headers = {"Authorization": f"Bearer {token}", "Accept": INDEX_ACCEPT}
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


def get_ghcr_created(image_name, tag):
    """Returns when a GHCR tag was built, from its image config, or None.

    Reads the first linux platform's config — all platforms are built in one run.
    Attestation manifests (platform "unknown") are skipped.
    """
    token, error = _get_pull_token(image_name)
    if not token:
        if error:
            log.warn(f"  GHCR build time lookup failed for '{image_name}:{tag}': {error}")
        return None

    base_url = f"https://ghcr.io/v2/{image_name}"
    auth = {"Authorization": f"Bearer {token}"}
    try:
        index_resp = request_with_retry(f"{base_url}/manifests/{tag}", headers={**auth, "Accept": INDEX_ACCEPT}, timeout=30)
        if index_resp.status_code != 200:
            return None
        digest = next(
            (m["digest"] for m in index_resp.json().get("manifests", []) if m.get("platform", {}).get("os") == "linux"),
            None,
        )
        if not digest:
            return None

        manifest_resp = request_with_retry(f"{base_url}/manifests/{digest}", headers={**auth, "Accept": MANIFEST_ACCEPT}, timeout=30)
        if manifest_resp.status_code != 200:
            return None
        config_digest = manifest_resp.json()["config"]["digest"]

        config_resp = request_with_retry(f"{base_url}/blobs/{config_digest}", headers=auth, timeout=30)
        if config_resp.status_code != 200:
            return None
        return parse_timestamp(config_resp.json().get("created"))
    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        log.warn(f"  GHCR build time lookup failed for '{image_name}:{tag}': {e}")
        return None
