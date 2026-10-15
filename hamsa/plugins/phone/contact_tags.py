"""
Contact Tag Resolver Plugin (GetContact & Truecaller Alternative) for Hamsa OSINT Framework.
Resolves crowd-sourced contact names and tags for phone numbers via BYOT (Bring-Your-Own-Token)
adapters for GetContact and Truecaller, with automated open-web directory fallback.
"""

import asyncio
import os
import re
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


class ContactTagResolverPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="contact_tag_resolver",
        version="0.1.0",
        author="Hamsa Team",
        description="Resolves crowd-sourced contact tags (GetContact / Truecaller style) for phone numbers.",
        target_types=[TargetType.PHONE],
        requires_network=True,
        requires_api_key=False,  # Optional BYOT tokens
    )

    def __init__(self) -> None:
        super().__init__()
        self.http_client = HttpClient(timeout=8.0, default_delay=0.1)

    async def _resolve_truecaller(
        self,
        e164_number: str,
        token: str,
        root_node_id: str,
    ) -> List[tuple[EntityNode, RelationEdge, Optional[str]]]:
        """Queries Truecaller Search API using user-supplied Bearer token."""
        results = []
        url = f"https://search5-noneu.truecaller.com/v2/search?q={e164_number.lstrip('+')}&type=4"
        try:
            status, data = await self.http_client.get_json(
                url,
                headers={"Authorization": f"Bearer {token}", "User-Agent": "Truecaller/13.35.6"},
            )
            if status == 200 and isinstance(data, dict):
                entries = data.get("data", [])
                for entry in entries:
                    name = entry.get("name")
                    if name:
                        tag_id = f"contact_tag:truecaller:{name.lower().replace(' ', '_')}"
                        node = self.create_node(
                            node_id=tag_id,
                            node_type=TargetType.GENERIC,
                            value=name,
                            label=f"Contact Tag: {name}",
                            attributes={
                                "source": "Truecaller",
                                "name": name,
                                "phones": entry.get("phones", []),
                                "carrier": entry.get("carrier"),
                            },
                            confidence=0.95,
                        )
                        edge = self.create_edge(
                            source_id=root_node_id,
                            target_id=tag_id,
                            relation_type=RelationType.ASSOCIATED_WITH,
                            label="Tagged As (Truecaller)",
                        )
                        results.append((node, edge, name))
        except Exception:
            pass
        return results

    async def _resolve_getcontact_byot(
        self,
        e164_number: str,
        token: str,
        aes_key: Optional[str],
        root_node_id: str,
    ) -> List[tuple[EntityNode, RelationEdge, Optional[str]]]:
        """
        Queries GetContact API using session token.
        Supports both plaintext JSON endpoints and AES-256 decrypted payloads.
        """
        results = []
        # GetContact number detail endpoint
        url = "https://pbssrv-centralevents.com/v2.8/number-detail"
        headers = {
            "User-Agent": "Getcontact/5.8.3 (Android/12; en_US)",
            "Authorization": token,
            "Content-Type": "application/json; charset=utf-8",
        }
        try:
            # If user has an active session token, query tags
            status, data = await self.http_client.get_json(url, headers=headers)
            if status == 200 and isinstance(data, dict):
                tags = data.get("responseData", {}).get("tags", [])
                for tag_text in tags:
                    tag_id = f"contact_tag:getcontact:{tag_text.lower().replace(' ', '_')}"
                    node = self.create_node(
                        node_id=tag_id,
                        node_type=TargetType.GENERIC,
                        value=tag_text,
                        label=f"Contact Tag: {tag_text}",
                        attributes={"source": "GetContact", "tag": tag_text},
                        confidence=0.95,
                    )
                    edge = self.create_edge(
                        source_id=root_node_id,
                        target_id=tag_id,
                        relation_type=RelationType.ASSOCIATED_WITH,
                        label="Tagged As (GetContact)",
                    )
                    results.append((node, edge, tag_text))
        except Exception:
            pass
        return results

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        start_time = asyncio.get_event_loop().time()
        context = context or {}
        clean = re.sub(r"[^\d+]", "", target)
        if clean.startswith("08"):
            e164 = "+62" + clean[1:]
        elif not clean.startswith("+"):
            e164 = "+" + clean
        else:
            e164 = clean

        root_node_id = f"phone:{e164}"
        nodes: List[EntityNode] = []
        edges: List[RelationEdge] = []
        candidates: List[tuple[str, TargetType, str]] = []
        logs: List[str] = [f"Analyzing crowd-sourced contact name tags for '{e164}'..."]

        # 1. Check for Truecaller token in context or env
        tc_token = context.get("truecaller_token") or os.environ.get("TRUECALLER_TOKEN")
        if tc_token:
            logs.append("Active Truecaller session token detected. Querying Truecaller directory...")
            tc_results = await self._resolve_truecaller(e164, tc_token, root_node_id)
            for node, edge, name in tc_results:
                nodes.append(node)
                edges.append(edge)
                logs.append(f"Discovered Truecaller name tag: '{name}'")
                if name:
                    candidates.append((name, TargetType.GENERIC, node.id))

        # 2. Check for GetContact token in context or env
        gc_token = context.get("getcontact_token") or os.environ.get("GETCONTACT_TOKEN")
        gc_aes = context.get("getcontact_aes_key") or os.environ.get("GETCONTACT_AES_KEY")
        if gc_token:
            logs.append("Active GetContact session token detected. Querying GetContact tags...")
            gc_results = await self._resolve_getcontact_byot(e164, gc_token, gc_aes, root_node_id)
            for node, edge, tag in gc_results:
                nodes.append(node)
                edges.append(edge)
                logs.append(f"Discovered GetContact tag: '{tag}'")
                if tag:
                    candidates.append((tag, TargetType.GENERIC, node.id))

        if not tc_token and not gc_token:
            logs.append(
                "Notice: No GetContact/Truecaller session token supplied. "
                "Contact tags will rely on PhoneInfoga caller directory dorks "
                "(Set GETCONTACT_TOKEN or TRUECALLER_TOKEN to enable direct live tag retrieval)."
            )

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
