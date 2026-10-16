"""
Instagram Masked Contact & Profile Lookup Plugin for Hamsa OSINT Framework.
Extracts obfuscated recovery email, obfuscated recovery phone, and account status
directly from Instagram unauthenticated recovery API (inspired by toutatis and InstagramPrivSniffer).
Zero external dependencies.
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


class InstagramLookupPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="instagram_masked_lookup",
        version="0.1.0",
        author="Hamsa Team",
        description="Extracts obfuscated recovery email and masked phone number from Instagram without authentication.",
        target_types=[TargetType.USERNAME],
        requires_network=True,
        rate_limit_delay=0.3,
    )

    def __init__(self) -> None:
        super().__init__()
        self.http_client = HttpClient(timeout=8.0, default_delay=0.2)

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        clean_user = target.strip().lstrip("@").lower()
        root_node_id = f"account:instagram:{clean_user}"
        profile_url = f"https://www.instagram.com/{clean_user}/"

        nodes: List[EntityNode] = []
        edges: List[RelationEdge] = []
        logs: List[str] = [f"Performing unauthenticated Instagram lookup for target '@{clean_user}'"]
        candidates: List[tuple[str, TargetType, str]] = []

        endpoint = "https://i.instagram.com/api/v1/users/lookup/"
        raw_body = json.dumps({"q": clean_user, "skip_recovery": "1"}, separators=(",", ":"))
        signed_payload = f"signed_body=SIGNATURE.{urllib.parse.quote_plus(raw_body)}"

        headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Instagram 101.0.0.15.120 Android (28/9; 480dpi; 1080x2160; Xiaomi; Mi A2; jasmine_sprout; qcom; en_US)",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-IG-App-ID": "124024574287414",
        }

        try:
            status, body, _ = await self.http_client.request(
                endpoint,
                method="POST",
                headers=headers,
                data=signed_payload.encode("utf-8"),
                jitter=False,
            )

            attributes: Dict[str, Any] = {
                "platform": "Instagram",
                "profile_url": profile_url,
                "username": clean_user,
            }

            if status == 200 and body:
                data = json.loads(body.decode("utf-8", errors="replace"))
                user_data = data.get("user") or {}

                obfuscated_email = user_data.get("obfuscated_email")
                obfuscated_phone = user_data.get("obfuscated_phone")
                has_valid_phone = user_data.get("has_valid_phone", False)

                if obfuscated_email:
                    attributes["obfuscated_recovery_email"] = obfuscated_email
                    logs.append(f"Discovered obfuscated recovery email: {obfuscated_email}")
                if obfuscated_phone:
                    attributes["obfuscated_recovery_phone"] = obfuscated_phone
                    logs.append(f"Discovered obfuscated recovery phone: {obfuscated_phone}")

                attributes["has_valid_phone"] = has_valid_phone

                # Create Instagram account node
                ig_node = self.create_node(
                    node_id=root_node_id,
                    node_type=TargetType.GENERIC,
                    value=profile_url,
                    label=f"Instagram: @{clean_user}",
                    attributes=attributes,
                )
                nodes.append(ig_node)

                # If obfuscated email exists, create a masked email lead node
                if obfuscated_email:
                    email_node_id = f"email:{obfuscated_email}"
                    email_node = self.create_node(
                        node_id=email_node_id,
                        node_type=TargetType.EMAIL,
                        value=obfuscated_email,
                        label=f"Masked Email: {obfuscated_email}",
                        attributes={"masked": True, "source": "Instagram Recovery Lookup"},
                    )
                    nodes.append(email_node)
                    edges.append(
                        self.create_edge(
                            source_id=root_node_id,
                            target_id=email_node_id,
                            relation_type=RelationType.ASSOCIATED_WITH,
                            label="Recovery Email Hint",
                        )
                    )

                # If obfuscated phone exists, create a masked phone lead node
                if obfuscated_phone:
                    phone_node_id = f"phone:{obfuscated_phone}"
                    phone_node = self.create_node(
                        node_id=phone_node_id,
                        node_type=TargetType.PHONE,
                        value=obfuscated_phone,
                        label=f"Masked Phone: {obfuscated_phone}",
                        attributes={"masked": True, "source": "Instagram Recovery Lookup"},
                    )
                    nodes.append(phone_node)
                    edges.append(
                        self.create_edge(
                            source_id=root_node_id,
                            target_id=phone_node_id,
                            relation_type=RelationType.ASSOCIATED_WITH,
                            label="Recovery Phone Hint",
                        )
                    )

            elif status == 404:
                logs.append(f"Target '@{clean_user}' not found on Instagram.")
            elif status == 429:
                logs.append("Instagram rate limited public lookup query.")
            else:
                logs.append(f"Instagram lookup returned HTTP status {status}.")

        except Exception as e:
            logs.append(f"Instagram lookup network note: {e}")

        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
        )
