import time
from enum import Enum

import requests

from .config import BACKOFF_BASE, MAX_RETRIES
from .logger import log


class TagCheckResult(Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"


def request_with_retry(url, headers=None, timeout=30):
    """GET request with exponential backoff for transient failures (429, 5xx, timeouts)."""
    last_exception = None
    response = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 429 or response.status_code >= 500:
                wait = BACKOFF_BASE ** attempt
                log.warn(
                    f"  Retryable status {response.status_code} from {url}, "
                    f"retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(wait)
                continue
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_exception = e
            wait = BACKOFF_BASE ** attempt
            log.warn(
                f"  {type(e).__name__} for {url}, "
                f"retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            time.sleep(wait)
        except requests.exceptions.RequestException:
            raise

    if last_exception:
        raise last_exception
    return response
