"""
HAMSA Dynamic Proxy Rotation & Anti-Block Shield
Manages HTTP/SOCKS5 proxy pools, health monitoring, failure backoff, and quarantine.
Pure Python Standard Library implementation.
"""

import os
import time
import random
import threading
from typing import List, Dict, Optional, Any


class ProxyManager:
    """Manages an active rotating proxy pool with health scoring and quarantine backoff."""

    def __init__(self, proxies_file: Optional[str] = None, quarantine_duration: float = 300.0):
        self.proxies_file = proxies_file or os.getenv("PROXIES_FILE", os.path.expanduser("~/.hamsa/proxies.txt"))
        self.quarantine_duration = quarantine_duration
        self._proxies: List[str] = []
        self._quarantined: Dict[str, float] = {}  # proxy -> unquarantine_timestamp
        self._lock = threading.Lock()
        self._index = 0
        self._load_proxies()

    def _load_proxies(self) -> None:
        """Loads proxy endpoints from environment or file."""
        env_list = os.getenv("HAMSA_PROXY_LIST")
        if env_list:
            self._proxies = [p.strip() for p in env_list.split(",") if p.strip()]
            return

        if os.path.exists(self.proxies_file):
            try:
                with open(self.proxies_file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                    self._proxies = lines
            except Exception:
                self._proxies = []

    def add_proxies(self, proxy_list: List[str]) -> None:
        """Adds a list of proxies to the pool."""
        with self._lock:
            for p in proxy_list:
                clean = p.strip()
                if clean and clean not in self._proxies:
                    self._proxies.append(clean)

    def get_proxy(self, strategy: str = "round_robin") -> Optional[str]:
        """
        Retrieves the next healthy proxy from the pool.
        Strategies: 'round_robin', 'random'.
        Returns None if pool is empty or all proxies are quarantined.
        """
        with self._lock:
            if not self._proxies:
                return None

            now = time.time()
            # Lift quarantine for eligible proxies
            healthy = [
                p for p in self._proxies
                if p not in self._quarantined or now >= self._quarantined[p]
            ]

            if not healthy:
                # If all quarantined, lift the oldest quarantine as fallback
                oldest_proxy = min(self._quarantined, key=self._quarantined.get)
                del self._quarantined[oldest_proxy]
                return oldest_proxy

            if strategy == "random":
                return random.choice(healthy)
            else:
                proxy = healthy[self._index % len(healthy)]
                self._index = (self._index + 1) % len(healthy)
                return proxy

    def record_success(self, proxy: str) -> None:
        """Clears quarantine upon successful request."""
        with self._lock:
            self._quarantined.pop(proxy, None)

    def record_failure(self, proxy: str) -> None:
        """Puts failed proxy into temporary quarantine."""
        with self._lock:
            self._quarantined[proxy] = time.time() + self.quarantine_duration

    def status(self) -> Dict[str, Any]:
        """Returns proxy pool statistics."""
        with self._lock:
            now = time.time()
            active_count = sum(1 for p in self._proxies if p not in self._quarantined or now >= self._quarantined[p])
            return {
                "total_proxies": len(self._proxies),
                "active_healthy": active_count,
                "quarantined": len(self._proxies) - active_count,
                "proxy_list": [p.split("@")[-1] for p in self._proxies]  # Mask credentials
            }


# Global singleton instance
GLOBAL_PROXY_MANAGER = ProxyManager()
