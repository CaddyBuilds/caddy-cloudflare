import json

import requests

from .config import REQUIRED_PLATFORMS
from .http_client import TagCheckResult, request_with_retry
from .logger import log


def check_docker_hub_tag(image_name, tag):
    """Checks if a tag exists for a Docker Hub image.

    Returns:
        tuple: (TagCheckResult, data_or_error_msg)
    """
    url = f"https://hub.docker.com/v2/repositories/{image_name}/tags/{tag}"
    try:
        response = request_with_retry(url, timeout=45)
        if response.status_code == 200:
            return TagCheckResult.FOUND, response.json()
        elif response.status_code == 404:
            return TagCheckResult.NOT_FOUND, None
        else:
            msg = f"Unexpected status {response.status_code} for '{image_name}:{tag}'"
            log.error(msg)
            return TagCheckResult.ERROR, msg
    except requests.exceptions.RequestException as e:
        msg = f"Request failed for '{image_name}:{tag}': {e}"
        log.error(msg)
        return TagCheckResult.ERROR, msg
    except json.JSONDecodeError as e:
        msg = f"JSON decode error for '{image_name}:{tag}': {e}"
        log.error(msg)
        return TagCheckResult.ERROR, msg


def get_platforms_from_tag_data(tag_data):
    """Extracts required linux platform strings from Docker Hub tag API response."""
    platforms = set()
    if not tag_data or "images" not in tag_data or not isinstance(tag_data["images"], list):
        log.info("  Could not find valid 'images' list in Docker Hub tag data.")
        return platforms

    for img in tag_data["images"]:
        if not isinstance(img, dict):
            continue
        os_name = img.get("os")
        arch = img.get("architecture")
        variant = img.get("variant")

        if os_name != "linux" or not arch:
            continue

        if arch == "arm" and variant == "v7":
            platform_str = f"{os_name}/{arch}/{variant}"
        elif f"{os_name}/{arch}" in REQUIRED_PLATFORMS:
            platform_str = f"{os_name}/{arch}"
        else:
            continue

        if platform_str in REQUIRED_PLATFORMS:
            platforms.add(platform_str)

    return platforms
