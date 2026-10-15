"""
PhoneInfoga Footprint & Advanced Search Dorking Plugin for Hamsa OSINT Framework.
Implements PhoneInfoga's multi-format number permutation and Google/DuckDuckGo search dorking methodology.
"""

import asyncio
import re
import urllib.parse
from typing import Any, Dict, List, Optional
from hamsa.core.models import (
    EntityNode,
    PluginMetadata,
    PluginResult,
    RelationEdge,
    RelationType,
    TargetType,
)
from hamsa.plugins.base import BasePlugin


class PhoneInfogaDorksPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="phone_infoga_footprint",
        version="0.1.0",
        author="Hamsa Team",
        description="Generates PhoneInfoga multi-format permutations and advanced search engine reconnaissance dorks.",
        target_types=[TargetType.PHONE],
        requires_network=False,
    )

    def _generate_permutations(self, clean_number: str) -> List[str]:
        """Generates common formatting permutations used across the web."""
        num = clean_number.lstrip("+")
        permutations = [f"+{num}"]

        if num.startswith("62"):
            local = "0" + num[2:]
            permutations.append(local)
            # Hyphenated (e.g. 0812-3456-7890)
            if len(local) >= 10:
                permutations.append(f"{local[:4]}-{local[4:8]}-{local[8:]}")
                permutations.append(f"{local[:4]} {local[4:8]} {local[8:]}")
        elif len(num) == 11 and num.startswith("1"):
            # US format (e.g. 1-202-555-0123)
            permutations.append(f"({num[1:4]}) {num[4:7]}-{num[7:]}")
            permutations.append(f"{num[1:4]}-{num[4:7]}-{num[7:]}")

        return list(dict.fromkeys(permutations))

    def _build_dork_url(self, query: str) -> str:
        return f"https://www.google.com/search?q={urllib.parse.quote(query)}"

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        start_time = asyncio.get_event_loop().time()
        clean = re.sub(r"[^\d+]", "", target)
        if clean.startswith("08"):
            clean = "+62" + clean[1:]
        elif not clean.startswith("+"):
            clean = "+" + clean

        root_node_id = f"phone:{clean}"
        permutations = self._generate_permutations(clean)

        logs: List[str] = [
            f"Synthesized {len(permutations)} number permutations: {', '.join(permutations[:3])}...",
            "Constructing PhoneInfoga reconnaissance dork categories...",
        ]

        nodes: List[EntityNode] = []
        edges: List[RelationEdge] = []

        # Primary formats for query
        primary_q = f'"{permutations[0]}"'
        if len(permutations) > 1:
            primary_q += f' OR "{permutations[1]}"'

        # 1. Social Network Footprint Dorks
        social_query = f"({primary_q}) (site:facebook.com OR site:instagram.com OR site:linkedin.com OR site:twitter.com OR site:x.com OR site:tiktok.com)"
        social_url = self._build_dork_url(social_query)
        soc_id = f"dork:social:{clean.lstrip('+')}"
        soc_node = self.create_node(
            node_id=soc_id,
            node_type=TargetType.GENERIC,
            value=social_url,
            label="PhoneInfoga: Social Network Dork",
            attributes={
                "category": "social_footprint",
                "search_query": social_query,
                "google_search_url": social_url,
            },
        )
        nodes.append(soc_node)
        edges.append(
            self.create_edge(
                source_id=root_node_id,
                target_id=soc_id,
                relation_type=RelationType.ASSOCIATED_WITH,
                label="Social Footprint Dork",
            )
        )

        # 2. Document & Paste Leak Dorks
        leak_query = f"({primary_q}) (filetype:pdf OR filetype:xlsx OR filetype:csv OR site:pastebin.com OR site:ghostbin.com)"
        leak_url = self._build_dork_url(leak_query)
        leak_id = f"dork:leaks:{clean.lstrip('+')}"
        leak_node = self.create_node(
            node_id=leak_id,
            node_type=TargetType.GENERIC,
            value=leak_url,
            label="PhoneInfoga: Document Leak Dork",
            attributes={
                "category": "document_and_pastes",
                "search_query": leak_query,
                "google_search_url": leak_url,
            },
        )
        nodes.append(leak_node)
        edges.append(
            self.create_edge(
                source_id=root_node_id,
                target_id=leak_id,
                relation_type=RelationType.ASSOCIATED_WITH,
                label="Document Leak Dork",
            )
        )

        # 3. Reputation & Directory Dorks
        rep_query = f"({primary_q}) (site:truecaller.com OR site:sync.me OR site:tellows.com OR site:whocalledme.com)"
        rep_url = self._build_dork_url(rep_query)
        rep_id = f"dork:reputation:{clean.lstrip('+')}"
        rep_node = self.create_node(
            node_id=rep_id,
            node_type=TargetType.GENERIC,
            value=rep_url,
            label="PhoneInfoga: Caller Directory Dork",
            attributes={
                "category": "reputation_directory",
                "search_query": rep_query,
                "google_search_url": rep_url,
            },
        )
        nodes.append(rep_node)
        edges.append(
            self.create_edge(
                source_id=root_node_id,
                target_id=rep_id,
                relation_type=RelationType.ASSOCIATED_WITH,
                label="Caller Directory Dork",
            )
        )

        duration = asyncio.get_event_loop().time() - start_time
        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
            execution_time_seconds=round(duration, 2),
        )
