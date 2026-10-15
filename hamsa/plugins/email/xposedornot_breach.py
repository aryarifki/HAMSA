"""
XposedOrNot Breach Checker Plugin for Hamsa OSINT Framework.
Queries public XposedOrNot API to correlate email addresses with known breach incidents.
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


class XposedOrNotBreachPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="xposedornot_breach",
        version="0.1.0",
        author="Hamsa Team",
        description="Checks email exposure in public breaches via the free XposedOrNot API.",
        target_types=[TargetType.EMAIL],
        requires_api_key=False,
        rate_limit_delay=0.3,
    )

    def __init__(self) -> None:
        super().__init__()
        self.http_client = HttpClient(timeout=10.0)

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        start_time = asyncio.get_event_loop().time()
        email = target.strip().lower()
        root_node_id = f"email:{email}"

        root_node = self.create_node(
            node_id=root_node_id,
            node_type=TargetType.EMAIL,
            value=email,
            label=email,
            attributes={"domain": email.split("@")[-1] if "@" in email else ""},
        )

        nodes: List[EntityNode] = [root_node]
        edges: List[RelationEdge] = []
        logs: List[str] = [f"Querying XposedOrNot breach database for '{email}'..."]

        url = f"https://api.xposedornot.com/v1/check-email/{email}"
        try:
            status, data = await self.http_client.get_json(url)
            if status == 200 and isinstance(data, dict):
                breaches_raw = data.get("breaches", [])
                # Breaches can be list of lists or list of dicts depending on response
                breach_names = []
                if isinstance(breaches_raw, list):
                    for item in breaches_raw:
                        if isinstance(item, list) and item:
                            breach_names.append(str(item[0]))
                        elif isinstance(item, str):
                            breach_names.append(item)

                if breach_names:
                    logs.append(f"Found exposure in {len(breach_names)} breach incidents: {', '.join(breach_names[:5])}")
                    for b_name in breach_names:
                        breach_id = f"breach:{b_name.lower().replace(' ', '_')}"
                        breach_node = self.create_node(
                            node_id=breach_id,
                            node_type=TargetType.BREACH,
                            value=b_name,
                            label=f"Breach: {b_name}",
                            attributes={"breach_title": b_name},
                            confidence=1.0,
                        )
                        edge = self.create_edge(
                            source_id=root_node_id,
                            target_id=breach_id,
                            relation_type=RelationType.EXPOSED_IN,
                            label="Exposed In",
                        )
                        nodes.append(breach_node)
                        edges.append(edge)
                else:
                    logs.append("No breach records found on XposedOrNot for this email.")
            elif status == 404:
                logs.append("Email address not found in any recorded breaches on XposedOrNot.")
            else:
                logs.append(f"XposedOrNot API returned HTTP status {status}.")
        except Exception as e:
            logs.append(f"Warning: Failed to query XposedOrNot: {e}")

        candidates: List[tuple[str, TargetType, str]] = []
        if "@" in email:
            local_part = email.split("@")[0].strip()
            generic_words = {"admin", "support", "info", "contact", "sales", "help", "hello", "team", "office"}
            if len(local_part) >= 3 and local_part.lower() not in generic_words:
                candidates.append((local_part, TargetType.USERNAME, root_node_id))
                logs.append(f"Derived potential username handle from email: '{local_part}'")

        duration = asyncio.get_event_loop().time() - start_time
        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
            candidate_targets=candidates,
            execution_time_seconds=round(duration, 2),
        )
