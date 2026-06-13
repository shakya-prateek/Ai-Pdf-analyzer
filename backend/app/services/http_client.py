import json
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

import certifi


TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def load_json(
    request: urllib.request.Request,
    *,
    timeout: int = 30,
    retries: int = 2,
) -> dict[str, Any]:
    if not request.has_header("User-agent"):
        request.add_header("User-Agent", "DocuScope/1.0")
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
                context=TLS_CONTEXT,
            ) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt == retries:
                raise
        except urllib.error.URLError:
            if attempt == retries:
                raise
        time.sleep(0.6 * (2 ** attempt))
    raise RuntimeError("Remote request failed")
