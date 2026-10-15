"""
Asynchronous HTTP utility client with User-Agent rotation, proxy support, and jitter delay.
Uses standard library urllib wrapped in asyncio.to_thread to maintain zero external dependencies.
"""

import asyncio
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


class HttpClient:
    """Lightweight async HTTP client with anti-fingerprint and stealth capabilities."""

    def __init__(
        self,
        timeout: float = 10.0,
        proxy: Optional[str] = None,
        default_delay: float = 0.2,
    ) -> None:
        self.timeout = timeout
        self.proxy = proxy
        self.default_delay = default_delay

    def _sync_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
    ) -> Tuple[int, bytes, Dict[str, str]]:
        req_headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Connection": "close",
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

        handlers = []
        if self.proxy:
            handlers.append(urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy}))
        opener = urllib.request.build_opener(*handlers)

        try:
            with opener.open(req, timeout=self.timeout) as resp:
                status_code = resp.status
                body = resp.read()
                resp_headers = dict(resp.headers)
                return status_code, body, resp_headers
        except urllib.error.HTTPError as e:
            body = e.read()
            return e.code, body, dict(e.headers)
        except Exception as e:
            raise RuntimeError(f"HTTP request failed for {url}: {e}")

    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
        jitter: bool = True,
    ) -> Tuple[int, bytes, Dict[str, str]]:
        """Asynchronously execute HTTP request with jitter and exponential backoff on 429/failures."""
        max_retries = 3
        for attempt in range(max_retries):
            if jitter and self.default_delay > 0:
                delay = self.default_delay + random.uniform(0.05, 0.2)
                await asyncio.sleep(delay)

            try:
                status, body, resp_headers = await asyncio.to_thread(self._sync_request, url, method, headers, data)
                if status == 429 and attempt < max_retries - 1:
                    retry_after_str = resp_headers.get("Retry-After", "")
                    try:
                        retry_after = float(retry_after_str)
                    except ValueError:
                        retry_after = 2.0 ** (attempt + 1)
                    await asyncio.sleep(min(retry_after, 10.0))
                    continue
                return status, body, resp_headers
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"HTTP request failed after {max_retries} attempts for {url}: {e}")
                await asyncio.sleep(1.0 * (attempt + 1))
        return 500, b"", {}

    async def get_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Optional[Any]]:
        """Helper to fetch and parse JSON."""
        status_code, body, _ = await self.request(url, method="GET", headers=headers)
        if not body:
            return status_code, None
        try:
            parsed = json.loads(body.decode("utf-8", errors="replace"))
            return status_code, parsed
        except Exception:
            return status_code, None
