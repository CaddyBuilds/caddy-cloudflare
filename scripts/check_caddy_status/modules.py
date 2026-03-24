import json
from datetime import datetime, timezone

from .config import MODULE_VERSIONS_FILE, MODULES
from .github_api import get_latest_commit_sha
from .logger import log


def load_module_versions():
    """Loads the module version tracking file. Returns empty state if missing/invalid."""
    try:
        with open(MODULE_VERSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("modules"):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"last_checked": "", "modules": {}}


def save_module_versions(state, dry_run=False):
    """Saves the module version tracking file."""
    if dry_run:
        log.info(f"  [DRY-RUN] Would save module versions to {MODULE_VERSIONS_FILE}")
        return

    state["last_checked"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(MODULE_VERSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
        log.info(f"  Saved module versions to {MODULE_VERSIONS_FILE}")
    except OSError as e:
        log.error(f"Failed to save module versions: {e}")


def check_module_updates():
    """Checks if any tracked modules have new commits.

    Returns:
        tuple: (modules_changed, changed_module_names, updated_state)
        First run (empty state) populates SHAs without triggering a build.
    """
    stored = load_module_versions()
    is_first_run = not stored.get("modules")
    updated_state = {"last_checked": "", "modules": {}}
    changed_modules = []

    for mod in MODULES:
        module_name = mod["module"]
        repo = mod["repo"]
        log.info(f"  Checking module: {module_name}")

        current_sha = get_latest_commit_sha(repo)
        if not current_sha:
            log.warn(f"  Could not fetch SHA for {repo}, skipping")
            # Preserve existing entry
            if module_name in stored.get("modules", {}):
                updated_state["modules"][module_name] = stored["modules"][module_name]
            continue

        stored_sha = stored.get("modules", {}).get(module_name, {}).get("last_commit_sha", "")

        updated_state["modules"][module_name] = {
            "repo": repo,
            "last_commit_sha": current_sha,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }

        if is_first_run:
            log.info(f"    First run — recorded SHA: {current_sha[:12]}")
        elif stored_sha and current_sha != stored_sha:
            changed_modules.append(module_name)
            log.info(f"    CHANGED: {stored_sha[:12]} -> {current_sha[:12]}")
        else:
            log.info(f"    Unchanged: {current_sha[:12]}")

    if is_first_run:
        log.info("  First run — populating module SHAs (no build triggered)")
        return False, [], updated_state

    return len(changed_modules) > 0, changed_modules, updated_state
