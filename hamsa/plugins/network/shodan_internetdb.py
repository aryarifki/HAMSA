"""
Shodan InternetDB Keyless Network Reconnaissance Plugin for Hamsa OSINT Framework.
Extracts open ports, exposed hostnames, CPE technologies, and known CVE vulnerabilities
directly from the free Shodan InternetDB API without requiring an API key (inspired by theHarvester).
"""

import asyncio
import re
import socket
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


class ShodanInternetDBPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="shodan_internetdb",
        version="0.1.0",
        author="Hamsa Team",
        description="Keyless Shodan InternetDB query for open ports, hostnames, and known CVEs.",
        target_types=[TargetType.DOMAIN, TargetType.IP],
        requires_network=True,
    )

    def __init__(self) -> None:
        super().__init__()
        self.http_client = HttpClient(timeout=7.0, default_delay=0.1)

    async def _resolve_ip(self, target: str) -> Optional[str]:
        # If already an IP address
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target):
            return target
        try:
            clean_host = target.strip().replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
            ip = await asyncio.to_thread(socket.gethostbyname, clean_host)
            return ip
        except Exception:
            return None

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        nodes: List[EntityNode] = []
        edges: List[RelationEdge] = []
        logs: List[str] = [f"Checking Shodan InternetDB for target: '{target}'"]

        ip_addr = await self._resolve_ip(target)
        if not ip_addr:
            logs.append(f"Could not resolve host '{target}' to an IPv4 address.")
            return PluginResult(
                plugin_name=self.metadata.name,
                success=True,
                nodes=nodes,
                edges=edges,
                logs=logs,
            )

        root_node_id = f"ip:{ip_addr}"
        root_node = self.create_node(
            node_id=root_node_id,
            node_type=TargetType.IP,
            value=ip_addr,
            label=f"IP: {ip_addr}",
            attributes={"host": target},
        )
        nodes.append(root_node)

        url = f"https://internetdb.shodan.io/{ip_addr}"
        try:
            status, data = await self.http_client.get_json(url)
            if status == 200 and isinstance(data, dict):
                ports = data.get("ports", [])
                hostnames = data.get("hostnames", [])
                cpes = data.get("cpes", [])
                vulns = data.get("vulns", [])
                tags = data.get("tags", [])

                root_node.attributes.update({
                    "open_ports": ports,
                    "hostnames": hostnames,
                    "cpes": cpes,
                    "cve_vulnerabilities": vulns,
                    "tags": tags,
                })

                logs.append(f"Identified {len(ports)} open port(s): {ports}")
                if hostnames:
                    logs.append(f"Associated hostnames: {hostnames}")
                if vulns:
                    logs.append(f"Discovered {len(vulns)} known CVE vulnerability record(s): {vulns[:5]}")

                # Create vulnerability nodes for top CVEs
                for cve in vulns[:10]:
                    cve_id = f"cve:{cve.lower()}"
                    cve_node = self.create_node(
                        node_id=cve_id,
                        node_type=TargetType.VULNERABILITY,
                        value=cve,
                        label=f"Vulnerability: {cve}",
                        attributes={"cve_id": cve, "source": "Shodan InternetDB"},
                    )
                    nodes.append(cve_node)
                    edges.append(
                        self.create_edge(
                            source_id=root_node_id,
                            target_id=cve_id,
                            relation_type=RelationType.AFFECTED_BY,
                            label="Exposed CVE",
                        )
                    )
            elif status == 404:
                logs.append(f"No exposed ports or services indexed in Shodan InternetDB for {ip_addr}.")
            else:
                logs.append(f"Shodan InternetDB API returned status {status}.")
        except Exception as e:
            logs.append(f"Shodan InternetDB query note: {e}")

        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
        )
