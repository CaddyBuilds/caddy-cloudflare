"""Entrypoint for the Caddy release and module update checker.

Usage:
    python -m check_caddy_status
    python -m check_caddy_status --dry-run
"""

import argparse
import sys
from datetime import datetime, timezone

from .config import CUSTOM_IMAGE, GHCR_IMAGE, OFFICIAL_CADDY_IMAGE, REQUIRED_PLATFORMS
from .docker_hub import check_docker_hub_tag, get_platforms_from_tag_data
from .ghcr import check_ghcr_tag
from .github_api import get_latest_caddy_release
from .http_client import TagCheckResult
from .logger import log, set_action_output
from .modules import check_module_updates, save_module_versions


def main():
    parser = argparse.ArgumentParser(description="Check Caddy release status and module updates")
    parser.add_argument("--dry-run", action="store_true", help="Run checks without setting outputs or saving state")
    args = parser.parse_args()
    dry_run = args.dry_run

    start_time = datetime.now(timezone.utc)
    log.info(f"--- Starting Caddy Check at {start_time.isoformat()} ---")
    if dry_run:
        log.info("*** DRY-RUN MODE — no outputs will be set, no files written ***")

    if not REQUIRED_PLATFORMS:
        log.error("Configuration error: REQUIRED_PLATFORMS set is empty.")
        sys.exit(1)
    if not GHCR_IMAGE and not CUSTOM_IMAGE:
        log.error("Configuration error: set GITHUB_REPOSITORY, GHCR_IMAGE, or DOCKERHUB_REPOSITORY_NAME.")
        sys.exit(1)
    log.info(f"Required platforms: {REQUIRED_PLATFORMS}")
    log.info(f"GHCR image: {GHCR_IMAGE or '(not set)'}")
    log.info(f"Docker Hub image: {CUSTOM_IMAGE or '(not set)'}")

    # Step 1: Get latest Caddy release
    latest_gh_tag = get_latest_caddy_release()
    docker_tag = latest_gh_tag.lstrip("v")
    log.set_summary("Caddy Release", latest_gh_tag)

    # Step 2: Check official Caddy image on Docker Hub
    log.info(f"\nStep 1: Checking official image '{OFFICIAL_CADDY_IMAGE}:{docker_tag}'...")
    official_image_ready = _check_official_image(docker_tag)

    if not official_image_ready:
        log.info("Result: Official image is not ready. No build triggered.")
        log.set_summary("Build Decision", "No — official image not ready")
        _set_outputs(needs_build=False, version=latest_gh_tag, reason="none", module_update=False, dry_run=dry_run)
        log.print_summary()
        sys.exit(0)

    # Step 3: Check custom image on GHCR + Docker Hub
    log.info(f"\nStep 2: Checking custom image status...")
    custom_image_complete = _check_custom_image(docker_tag)

    # Step 4: Check module updates
    log.info(f"\nStep 3: Checking module updates...")
    modules_changed, changed_modules, updated_module_state = check_module_updates()
    save_module_versions(updated_module_state, dry_run)

    if modules_changed:
        log.set_summary("Module Changes", ", ".join(m.split("/")[-1] for m in changed_modules))
    else:
        log.set_summary("Module Changes", "None")

    # Step 5: Final decision
    needs_build = False
    build_reason = "none"

    if not custom_image_complete:
        needs_build = True
        build_reason = "new_caddy_version"
    elif modules_changed:
        needs_build = True
        build_reason = "module_update"

    log.set_summary("Build Decision", f"{'Yes' if needs_build else 'No'} (reason: {build_reason})")
    _set_outputs(needs_build=needs_build, version=latest_gh_tag, reason=build_reason, module_update=modules_changed, dry_run=dry_run)
    log.print_summary()

    end_time = datetime.now(timezone.utc)
    log.info(f"\n--- Check finished at {end_time.isoformat()} (Duration: {end_time - start_time}) ---")


def _check_official_image(docker_tag):
    """Returns True if the official Caddy image has all required platforms."""
    result, data = check_docker_hub_tag(OFFICIAL_CADDY_IMAGE, docker_tag)

    if result == TagCheckResult.FOUND:
        found = get_platforms_from_tag_data(data)
        log.info(f"  Found platforms: {found or '{}'}")
        missing = REQUIRED_PLATFORMS - found
        if not missing:
            log.info("  Official image has all required platforms.")
            log.set_summary("Official Image", "Ready (all platforms)")
            return True
        log.info(f"  Official image MISSING platforms: {missing}")
        log.set_summary("Official Image", f"Missing: {missing}")
    elif result == TagCheckResult.NOT_FOUND:
        log.info(f"  Official tag '{docker_tag}' not found.")
        log.set_summary("Official Image", "Not found")
    else:
        log.info(f"  Error checking official image: {data}")
        log.set_summary("Official Image", f"Error: {data}")

    return False


def _check_custom_image(docker_tag):
    """Returns True if the custom image exists with all platforms on GHCR or Docker Hub."""
    custom_complete = False
    ghcr_result = None

    # GHCR (primary)
    if GHCR_IMAGE:
        log.info(f"  Checking GHCR: ghcr.io/{GHCR_IMAGE}:{docker_tag}")
        ghcr_result, ghcr_data = check_ghcr_tag(GHCR_IMAGE, docker_tag)

        if ghcr_result == TagCheckResult.FOUND:
            missing = REQUIRED_PLATFORMS - ghcr_data
            if not missing:
                custom_complete = True
                log.info("  GHCR image complete.")
                log.set_summary("Custom (GHCR)", "Complete")
            else:
                log.info(f"  GHCR image missing: {missing}")
                log.set_summary("Custom (GHCR)", f"Missing: {missing}")
        elif ghcr_result == TagCheckResult.NOT_FOUND:
            log.info("  GHCR tag not found.")
            log.set_summary("Custom (GHCR)", "Not found")
        else:
            log.warn(f"  GHCR check failed: {ghcr_data}")
            log.set_summary("Custom (GHCR)", f"Error: {ghcr_data}")
    else:
        log.info("  GHCR image not configured, skipping.")
        log.set_summary("Custom (GHCR)", "Not configured")

    # Docker Hub (secondary)
    if CUSTOM_IMAGE:
        log.info(f"  Checking Docker Hub: {CUSTOM_IMAGE}:{docker_tag}")
        dh_result, dh_data = check_docker_hub_tag(CUSTOM_IMAGE, docker_tag)

        if dh_result == TagCheckResult.FOUND:
            dh_platforms = get_platforms_from_tag_data(dh_data)
            dh_missing = REQUIRED_PLATFORMS - dh_platforms
            if not dh_missing:
                log.info("  Docker Hub image complete.")
                log.set_summary("Custom (Docker Hub)", "Complete")
                # Fallback if GHCR errored
                if not custom_complete and ghcr_result == TagCheckResult.ERROR:
                    custom_complete = True
                    log.info("  Using Docker Hub as fallback (GHCR errored).")
            else:
                log.info(f"  Docker Hub image missing: {dh_missing}")
                log.set_summary("Custom (Docker Hub)", f"Missing: {dh_missing}")
        elif dh_result == TagCheckResult.NOT_FOUND:
            log.info("  Docker Hub tag not found.")
            log.set_summary("Custom (Docker Hub)", "Not found")
        else:
            log.set_summary("Custom (Docker Hub)", f"Error: {dh_data}")
    else:
        log.info("  Docker Hub image not configured, skipping.")
        log.set_summary("Custom (Docker Hub)", "Not configured")

    return custom_complete


def _set_outputs(needs_build, version, reason, module_update, dry_run):
    set_action_output("NEEDS_BUILD", "true" if needs_build else "false", dry_run)
    set_action_output("LATEST_VERSION", version, dry_run)
    set_action_output("BUILD_REASON", reason, dry_run)
    set_action_output("MODULE_UPDATE", "true" if module_update else "false", dry_run)


if __name__ == "__main__":
    main()
