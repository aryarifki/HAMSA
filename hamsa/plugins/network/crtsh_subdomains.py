"""
Certificate Transparency Subdomain Discovery Plugin for Hamsa OSINT Framework.
Passively harvests issued SSL/TLS certificates and subdomains via crt.sh without touching target infrastructure
(inspired by amass and theHarvester).
"""

import asyncio
from typing import Any, Dict, List, Optional, Set
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


class CrtshSubdomainPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="crtsh_certificate_transparency",
        version="0.1.0",
        author="Hamsa Team",
        description="Discovers organizational subdomains passively via public Certificate Transparency logs (crt.sh).",
        target_types=[TargetType.DOMAIN],
        requires_network=True,
    )

    def __init__(self) -> None:
        super().__init__()
        self.http_client = HttpClient(timeout=10.0, default_delay=0.2)

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        clean_domain = target.strip().replace("https://", "").replace("http://", "").split("/")[0].split(":")[0].lower()
        root_node_id = f"domain:{clean_domain}"

        nodes: List[EntityNode] = []
        edges: List[RelationEdge] = []
        logs: List[str] = [f"Querying Certificate Transparency logs for domain: '{clean_domain}'"]

        root_node = self.create_node(
            node_id=root_node_id,
            node_type=TargetType.DOMAIN,
            value=clean_domain,
            label=f"Domain: {clean_domain}",
            attributes={"domain": clean_domain},
        )
        nodes.append(root_node)

        url = f"https://crt.sh/?q=%.{clean_domain}&output=json"
        subdomains: Set[str] = set()

        try:
            status, certs = await self.http_client.get_json(url)
            if status == 200 and isinstance(certs, list):
                for cert in certs:
                    name_value = cert.get("name_value", "")
                    for entry in name_value.split("\n"):
                        sub = entry.strip().lower().lstrip("*.")
                        if sub.endswith(clean_domain) and sub != clean_domain and len(sub) > len(clean_domain):
                            subdomains.add(sub)

                logs.append(f"Discovered {len(subdomains)} unique passive subdomain certificate record(s).")

                # Limit creation of sub-nodes to top 15 to avoid graph bloat
                for sub in sorted(subdomains)[:15]:
                    sub_id = f"domain:{sub}"
                    sub_node = self.create_node(
                        node_id=sub_id,
                        node_type=TargetType.DOMAIN,
                        value=sub,
                        label=f"Subdomain: {sub}",
                        attributes={"parent_domain": clean_domain, "source": "crt.sh Certificate Transparency"},
                    )
                    nodes.append(sub_node)
                    edges.append(
                        self.create_edge(
                            source_id=root_node_id,
                            target_id=sub_id,
                            relation_type=RelationType.DERIVED_FROM,
                            label="Issued Certificate",
                        )
                    )
            else:
                logs.append(f"Certificate Transparency API returned status {status}.")
        except Exception as e:
            logs.append(f"Certificate Transparency query note: {e}")

        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
        )
