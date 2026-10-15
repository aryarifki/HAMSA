"""
Upstream Source Manager for Hamsa OSINT Framework.
Downloads, caches, and parses remote community site definitions (WhatsMyName, etc.).
Allows dynamic expansion to 600+ platforms without hardcoding.
"""

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional
from hamsa.utils.formatters import log_error, log_info, log_success

DEFAULT_SOURCES_DIR = os.path.expanduser("~/.hamsa/sources")
WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
WMN_LOCAL_FILE = os.path.join(DEFAULT_SOURCES_DIR, "wmn-data.json")


class SourceManager:
    """Manages external intelligence sources and community site definitions."""

    def __init__(self, storage_dir: str = DEFAULT_SOURCES_DIR) -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.wmn_file = os.path.join(self.storage_dir, "wmn-data.json")

    def update_sources(self, timeout: float = 12.0) -> int:
        """Downloads the latest WhatsMyName dataset and saves it to local cache."""
        log_info(f"Fetching latest site database from WhatsMyName upstream...")
        try:
            req = urllib.request.Request(
                WMN_DATA_URL,
                headers={"User-Agent": "HamsaOSINT/0.1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            sites = data.get("sites", [])
            if not sites:
                raise ValueError("Downloaded file contains no sites.")

            with open(self.wmn_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            log_success(f"Successfully cached {len(sites)} site definitions to: {self.wmn_file}")
            return len(sites)
        except Exception as e:
            log_error(f"Failed to update upstream sources: {e}")
            return 0

    def load_sites(self, category_filter: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Loads cached site definitions. Returns standardized platform objects.
        """
        if not os.path.exists(self.wmn_file):
            return []

        try:
            with open(self.wmn_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            sites = data.get("sites", [])
            standardized = []
            for s in sites:
                # WhatsMyName schema: name, uri_check, e_code, e_string, m_string, cat
                cat = s.get("cat", "general")
                if category_filter and cat.lower() != category_filter.lower():
                    continue

                standardized.append({
                    "name": s.get("name"),
                    "url": s.get("uri_check"),
                    "category": cat,
                    "check_status": s.get("e_code", 200),
                    "error_marker": s.get("e_string"),
                    "valid_marker": s.get("m_string"),
                })

            if limit:
                return standardized[:limit]
            return standardized
        except Exception as e:
            log_error(f"Error loading local site definitions: {e}")
            return []
