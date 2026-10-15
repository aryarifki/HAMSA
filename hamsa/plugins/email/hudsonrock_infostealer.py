"""
Hudson Rock Infostealer Intelligence Plugin for Hamsa OSINT Framework.
Queries the free Hudson Rock Cavalier API to detect malware compromises,
leaked corporate/user credentials, and infected computer hardware profiles.
"""

import asyncio
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


class HudsonRockInfostealerPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="hudsonrock_infostealer",
        version="0.1.0",
        author="Hamsa Team",
        description="Detects infostealer malware infections (RedLine, Vidar, Lumma) and compromised credentials.",
        target_types=[TargetType.EMAIL],
        requires_api_key=False,
        rate_limit_delay=0.3,
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
        start_time = asyncio.get_event_loop().time()
        email = target.strip().lower()
        root_node_id = f"email:{email}"

        logs: List[str] = [f"Querying Hudson Rock Cavalier API for infostealer infections on '{email}'..."]
        nodes: List[EntityNode] = []
        edges: List[RelationEdge] = []

        url = f"https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email?email={email}"
        try:
            status, data = await self.http_client.get_json(
                url,
                headers={"User-Agent": "HamsaOSINT/0.1.0"},
            )
            if status == 200 and isinstance(data, dict):
                stealers = data.get("stealers", [])
                total_corp = data.get("total_corporate_services", 0)
                total_user = data.get("total_user_services", 0)

                if stealers:
                    logs.append(
                        f"ALERT: Email compromised in {len(stealers)} infostealer infection incident(s)! "
                        f"(User Services: {total_user}, Corporate Services: {total_corp})"
                    )

                    for idx, st in enumerate(stealers[:5], 1):
                        date_comp = st.get("date_compromised", "Unknown Date")
                        comp_name = st.get("computer_name")
                        os_name = st.get("operating_system")
                        antivirus = st.get("antiviruses", [])
                        top_passwords = st.get("top_passwords", [])

                        incident_id = f"infostealer:{email}:{idx}"
                        incident_node = self.create_node(
                            node_id=incident_id,
                            node_type=TargetType.BREACH,
                            value=f"Infostealer Infection ({date_comp})",
                            label=f"Infostealer: {date_comp[:10]}",
                            attributes={
                                "infection_date": date_comp,
                                "total_services": st.get("total_user_services", 0),
                                "operating_system": os_name,
                                "computer_name": comp_name,
                                "antivirus": antivirus,
                                "sample_password_masks": top_passwords,
                            },
                            confidence=1.0,
                        )
                        nodes.append(incident_node)
                        edges.append(
                            self.create_edge(
                                source_id=root_node_id,
                                target_id=incident_id,
                                relation_type=RelationType.EXPOSED_IN,
                                label="Infostealer Compromise",
                            )
                        )

                        # If computer name is identified, map as hardware entity
                        if comp_name and comp_name != "Not Found":
                            dev_id = f"device:pc:{comp_name.lower().replace(' ', '_')}"
                            dev_node = self.create_node(
                                node_id=dev_id,
                                node_type=TargetType.DEVICE,
                                value=comp_name,
                                label=f"Host: {comp_name}",
                                attributes={
                                    "hostname": comp_name,
                                    "operating_system": os_name,
                                },
                            )
                            nodes.append(dev_node)
                            edges.append(
                                self.create_edge(
                                    source_id=incident_id,
                                    target_id=dev_id,
                                    relation_type=RelationType.CAPTURED_BY,
                                    label="Infected Host",
                                )
                            )
                else:
                    logs.append("No recorded infostealer infections found on Hudson Rock.")
            elif status == 404:
                logs.append("Target email not found in infostealer infection logs.")
            else:
                logs.append(f"Hudson Rock API returned status {status}.")
        except Exception as e:
            logs.append(f"Hudson Rock check error: {e}")

        duration = asyncio.get_event_loop().time() - start_time
        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
            execution_time_seconds=round(duration, 2),
        )
