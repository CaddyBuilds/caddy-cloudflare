"""Detects when the official Caddy image was republished after our last build.

Docker Official Images are rebuilt for base OS and Go toolchain fixes without a new
Caddy release. Rebuilding on top of them picks those fixes up.
"""

from .config import CUSTOM_IMAGE, GHCR_IMAGE, OFFICIAL_CADDY_IMAGE, VARIANT_SUFFIXES
from .docker_hub import check_docker_hub_tag, get_images_by_platform
from .ghcr import get_ghcr_created
from .http_client import TagCheckResult
from .logger import log
from .timeutil import parse_timestamp


def check_base_image_updates(docker_tag):
    """Returns True if any variant's official image is newer than our build of it."""
    stale = []
    unknown = []

    for suffix in VARIANT_SUFFIXES:
        tag = f"{docker_tag}{suffix}"
        official = _docker_hub_pushed(OFFICIAL_CADDY_IMAGE, tag)
        ours = _custom_build_time(tag)

        if official is None or ours is None:
            log.warn(f"  Could not compare '{tag}' (official: {official}, ours: {ours}), skipping.")
            unknown.append(tag)
            continue

        log.info(f"  {tag}: official pushed {official.isoformat()}, ours built {ours.isoformat()}")
        if official > ours:
            stale.append(tag)

    if stale:
        log.set_summary("Base Image", f"Updated upstream: {', '.join(stale)}")
    elif unknown:
        log.set_summary("Base Image", f"Unknown: {', '.join(unknown)}")
    else:
        log.set_summary("Base Image", "Up to date")

    return bool(stale)


def _custom_build_time(tag):
    """Returns when our image was built.

    GHCR is preferred because the image config's ``created`` is the build time. Docker Hub
    only knows the push time, which can postdate an upstream re-push that happened while
    our (long, emulated) build was still running.
    """
    if GHCR_IMAGE:
        created = get_ghcr_created(GHCR_IMAGE, tag)
        if created:
            return created
    if CUSTOM_IMAGE:
        return _docker_hub_pushed(CUSTOM_IMAGE, tag)
    return None


def _docker_hub_pushed(image_name, tag):
    """Returns the most recent push among the tag's required platforms, or None.

    The tag-level ``last_updated`` also moves when platforms we don't ship (Windows,
    riscv64) are re-pushed, which would trigger needless rebuilds.
    """
    result, data = check_docker_hub_tag(image_name, tag)
    if result != TagCheckResult.FOUND:
        return None
    pushed = [parse_timestamp(img.get("last_pushed")) for img in get_images_by_platform(data).values()]
    pushed = [p for p in pushed if p]
    return max(pushed) if pushed else None
