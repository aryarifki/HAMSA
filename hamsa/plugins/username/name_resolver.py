"""
Name Resolution and Search Dorking Plugin for Hamsa OSINT Framework.
Investigates discovered full names across open knowledge bases and generates global web dorks.
Provides unbounded web coverage across the open internet.
"""

import asyncio
import json
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
from hamsa.utils.http import HttpClient


class NameResolverPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="name_dork_resolver",
        version="0.1.0",
        author="Hamsa Team",
        description="Resolves full names against Wikipedia and generates global search engine dorks for unlimited web coverage.",
        target_types=[TargetType.GENERIC],
        rate_limit_delay=0.1,
    )

    def __init__(self) -> None:
        super().__init__()
        self.http_client = HttpClient(timeout=6.0, default_delay=0.05)

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        start_time = asyncio.get_event_loop().time()
        name = target.strip()
        node_id = f"person:{name.lower().replace(' ', '_')}"

        logs: List[str] = [f"Conducting deep open-web name reconnaissance for: '{name}'"]
        nodes: List[EntityNode] = []
        edges: List[RelationEdge] = []

        # 1. Generate targeted global search engine dorks (Unlimited Web Coverage)
        encoded_name = urllib.parse.quote(f'"{name}"')
        google_dork = f"https://www.google.com/search?q={encoded_name}"
        bing_dork = f"https://www.bing.com/search?q={encoded_name}"
        ddg_dork = f"https://duckduckgo.com/?q={encoded_name}"
        linkedin_dork = f"https://www.google.com/search?q=site:linkedin.com/in/+{encoded_name}"
        news_dork = f"https://news.google.com/search?q={encoded_name}"

        root_person_node = self.create_node(
            node_id=node_id,
            node_type=TargetType.GENERIC,
            value=name,
            label=f"Identity: {name}",
            attributes={
                "full_name": name,
                "google_dork": google_dork,
                "bing_dork": bing_dork,
                "duckduckgo_dork": ddg_dork,
                "linkedin_dork": linkedin_dork,
                "news_dork": news_dork,
            },
            confidence=1.0,
        )
        nodes.append(root_person_node)

        # 2. Query open Wikipedia / Knowledge Base API for known public identities
        wiki_url = (
            f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(name)}&limit=3&namespace=0&format=json"
        )
        try:
            status, data = await self.http_client.get_json(
                wiki_url,
                headers={"User-Agent": "HamsaOSINT/0.1.0"},
            )
            if status == 200 and isinstance(data, list) and len(data) >= 4:
                titles = data[1]
                links = data[3]
                for title, link in zip(titles, links):
                    if name.lower() in title.lower():
                        logs.append(f"Discovered public knowledge base entry: {title} ({link})")
                        kb_node_id = f"knowledge:{title.lower().replace(' ', '_')}"
                        kb_node = self.create_node(
                            node_id=kb_node_id,
                            node_type=TargetType.GENERIC,
                            value=link,
                            label=f"Wikipedia: {title}",
                            attributes={"title": title, "url": link, "source": "Wikipedia"},
                        )
                        edge = self.create_edge(
                            source_id=node_id,
                            target_id=kb_node_id,
                            relation_type=RelationType.MENTIONED_IN,
                            label="Documented In",
                        )
                        nodes.append(kb_node)
                        edges.append(edge)
        except Exception as e:
            logs.append(f"Wikipedia API notice: {e}")

        duration = asyncio.get_event_loop().time() - start_time
        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
            execution_time_seconds=round(duration, 2),
        )
