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


class CircuitBreaker:
    """
    Resilience Circuit Breaker pattern (inspired by atdork).
    Protects against IP bans and rate-limit loops by temporarily opening circuits to failing hosts.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_counts: Dict[str, int] = {}
        self.last_failure_time: Dict[str, float] = {}
        self.open_circuits: set[str] = set()

    def can_request(self, host: str) -> bool:
        if host in self.open_circuits:
            now = time.time()
            if now - self.last_failure_time.get(host, 0) > self.recovery_timeout:
                # Transition to half-open: allow probe
                self.open_circuits.remove(host)
                self.failure_counts[host] = 0
                return True
            return False
        return True

    def record_success(self, host: str) -> None:
        self.failure_counts[host] = 0
        self.open_circuits.discard(host)

    def record_failure(self, host: str) -> None:
        self.failure_counts[host] = self.failure_counts.get(host, 0) + 1
        self.last_failure_time[host] = time.time()
        if self.failure_counts[host] >= self.failure_threshold:
            self.open_circuits.add(host)


class AdaptiveDelay:
    """
    Adaptive delay with randomized exponential jitter (inspired by atdork).
    """
    @staticmethod
    def calculate(base_delay: float, failure_count: int, max_delay: float = 10.0) -> float:
        backoff = base_delay * (1.5 ** min(failure_count, 5))
        jitter = random.uniform(0.05, 0.25)
        return min(backoff + jitter, max_delay)


GLOBAL_CIRCUIT_BREAKER = CircuitBreaker()


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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Linux"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "close",
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

        handlers = []
        active_proxy = self.proxy
        if not active_proxy:
            try:
                from hamsa.core.proxy import GLOBAL_PROXY_MANAGER
                active_proxy = GLOBAL_PROXY_MANAGER.get_proxy()
            except Exception:
                active_proxy = None

        if active_proxy:
            # Handle SOCKS5 / HTTP proxy
            proxy_url = active_proxy
            if proxy_url.startswith("socks5://") or proxy_url.startswith("socks5h://"):
                try:
                    import socks  # type: ignore
                    import socket
                    parsed = urllib.parse.urlparse(proxy_url)
                    socks.set_default_proxy(socks.SOCKS5, parsed.hostname, parsed.port or 9050)
                    socket.socket = socks.socksocket
                except ImportError:
                    pass
            handlers.append(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))

        opener = urllib.request.build_opener(*handlers)

        try:
            with opener.open(req, timeout=self.timeout) as resp:
                status_code = resp.status
                body = resp.read()
                resp_headers = dict(resp.headers)
                if active_proxy and not self.proxy:
                    try:
                        from hamsa.core.proxy import GLOBAL_PROXY_MANAGER
                        GLOBAL_PROXY_MANAGER.record_success(active_proxy)
                    except Exception:
                        pass
                return status_code, body, resp_headers
        except urllib.error.HTTPError as e:
            body = e.read()
            return e.code, body, dict(e.headers)
        except Exception as e:
            if active_proxy and not self.proxy:
                try:
                    from hamsa.core.proxy import GLOBAL_PROXY_MANAGER
                    GLOBAL_PROXY_MANAGER.record_failure(active_proxy)
                except Exception:
                    pass
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

    async def check_wayback_snapshot(self, target_url: str) -> Optional[Dict[str, Any]]:
        """
        Passively checks the Wayback Machine availability API for an archived snapshot
        without directly hitting or fingerprinting the target server.
        """
        api_url = f"https://archive.org/wayback/available?url={urllib.parse.quote(target_url)}"
        try:
            status, data = await self.get_json(api_url)
            if status == 200 and isinstance(data, dict) and "archived_snapshots" in data:
                closest = data["archived_snapshots"].get("closest")
                if closest and closest.get("available"):
                    return {
                        "available": True,
                        "url": closest.get("url"),
                        "timestamp": closest.get("timestamp"),
                        "status": closest.get("status"),
                    }
        except Exception:
            pass
        return None
