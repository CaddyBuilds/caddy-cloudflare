import os
import sys
import uuid


class CheckLogger:
    """Structured logger for GitHub Actions with summary support."""

    def __init__(self):
        self.events = []
        self._summary = {}

    def info(self, message):
        self.events.append(("INFO", message))
        print(message, file=sys.stdout)

    def warn(self, message):
        self.events.append(("WARN", message))
        print(f"::warning::{message}", file=sys.stdout)

    def error(self, message):
        self.events.append(("ERROR", message))
        print(f"::error::ACTION_SCRIPT::{message}", file=sys.stderr)

    def set_summary(self, key, value):
        self._summary[key] = value

    def print_summary(self):
        lines = ["", "=" * 50, "CHECK SUMMARY", "=" * 50]
        for key, value in self._summary.items():
            lines.append(f"  {key:<25} {value}")
        lines.append("=" * 50)
        self.info("\n".join(lines))

        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            try:
                with open(summary_path, "a", encoding="utf-8") as f:
                    f.write("### Caddy Release Check\n\n")
                    f.write("| Check | Result |\n|-------|--------|\n")
                    for key, value in self._summary.items():
                        f.write(f"| {key} | {value} |\n")
                    f.write("\n")
            except OSError:
                pass


# Singleton logger
log = CheckLogger()


def set_action_output(output_name, value, dry_run=False):
    """Sets a GitHub Action output. In dry-run mode, prints to stdout."""
    output_value = str(value)

    if dry_run:
        log.info(f"  [DRY-RUN] Would set output: {output_name}={output_value}")
        return

    if "GITHUB_OUTPUT" not in os.environ:
        log.warn(f"GITHUB_OUTPUT not found. Cannot set output '{output_name}'.")
        return

    output_path = os.environ["GITHUB_OUTPUT"]
    try:
        with open(output_path, "a", encoding="utf-8") as f:
            if "\n" in output_value:
                delimiter = f"ghadelimiter_{uuid.uuid4()}"
                print(f"{output_name}<<{delimiter}", file=f)
                print(output_value, file=f)
                print(delimiter, file=f)
            else:
                print(f"{output_name}={output_value}", file=f)
    except OSError as e:
        log.error(f"Error writing to GITHUB_OUTPUT: {e}")
        sys.exit(1)
