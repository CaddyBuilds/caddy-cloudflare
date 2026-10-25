from datetime import datetime, timezone


def parse_timestamp(value):
    """Parses an RFC 3339 timestamp from a registry API into an aware UTC datetime, or None.

    Relies on Python 3.11+ ``fromisoformat``, which accepts a trailing ``Z`` and truncates
    fractional seconds beyond microseconds (GHCR returns nanoseconds).
    """
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    # Naive values would make comparisons raise TypeError; registries use UTC.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
