"""
Phone Presence and Line-Type Classifier Plugin for Hamsa OSINT Framework.
Analyzes phone numbers for line type (Mobile, Landline, VoIP) and generates platform presence pivot points.
"""

import asyncio
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

# Indonesian Landline Area Codes
ID_LANDLINE_AREA_CODES = {
    "021": "Jakarta / Tangerang / Bekasi / Depok",
    "022": "Bandung",
    "031": "Surabaya",
    "024": "Semarang",
    "0274": "Yogyakarta",
    "0361": "Denpasar (Bali)",
    "061": "Medan",
    "0711": "Palembang",
    "0411": "Makassar",
}


class PhonePresencePlugin(BasePlugin):
    metadata = PluginMetadata(
        name="phone_presence_and_linetype",
        version="0.1.0",
        author="Hamsa Team",
        description="Classifies phone line type (Mobile, Landline, Toll-Free) and constructs direct social presence pivots.",
        target_types=[TargetType.PHONE],
        requires_network=False,
    )

    def _classify_line_type(self, raw_phone: str) -> tuple[str, str]:
        clean = re.sub(r"[^\d]", "", raw_phone)
        if clean.startswith("62"):
            clean = "0" + clean[2:]

        # Check toll-free / premium
        if clean.startswith(("0800", "0809", "1500")):
            return "Toll-Free / VoIP", "Commercial Service"

        # Check landline area codes
        for code, area in ID_LANDLINE_AREA_CODES.items():
            if clean.startswith(code):
                return "Fixed Landline", f"Fixed Telephone Line ({area})"

        # Check mobile cellular prefix
        if clean.startswith(("081", "082", "083", "085", "087", "088", "089")):
            return "Mobile Cellular", "Standard GSM/LTE Mobile Line"

        return "Standard / Unclassified", "Unclassified Line"

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        start_time = asyncio.get_event_loop().time()
        clean_target = re.sub(r"[^\d+]", "", target)
        if clean_target.startswith("08"):
            e164 = "+62" + clean_target[1:]
        elif not clean_target.startswith("+"):
            e164 = "+" + clean_target
        else:
            e164 = clean_target

        root_node_id = f"phone:{e164}"
        line_type, line_desc = self._classify_line_type(target)

        logs: List[str] = [
            f"Classified phone '{target}' line-type: {line_type} ({line_desc})",
            "Generating social presence and identity pivot records...",
        ]

        nodes: List[EntityNode] = []
        edges: List[RelationEdge] = []

        # 1. Line Type Node
        lt_id = f"linetype:{line_type.lower().replace(' ', '_').replace('/', '_')}"
        lt_node = self.create_node(
            node_id=lt_id,
            node_type=TargetType.GENERIC,
            value=line_type,
            label=f"Line Type: {line_type}",
            attributes={"line_type": line_type, "description": line_desc},
        )
        nodes.append(lt_node)
        edges.append(
            self.create_edge(
                source_id=root_node_id,
                target_id=lt_id,
                relation_type=RelationType.ASSOCIATED_WITH,
                label="Line Classification",
            )
        )

        # 2. WhatsApp Direct Pivot
        wa_url = f"https://api.whatsapp.com/send/?phone={e164.lstrip('+')}"
        wa_id = f"presence:whatsapp:{e164.lstrip('+')}"
        wa_node = self.create_node(
            node_id=wa_id,
            node_type=TargetType.GENERIC,
            value=wa_url,
            label="WhatsApp Presence Link",
            attributes={
                "platform": "WhatsApp",
                "direct_chat_url": wa_url,
                "phone_number": e164,
            },
        )
        nodes.append(wa_node)
        edges.append(
            self.create_edge(
                source_id=root_node_id,
                target_id=wa_id,
                relation_type=RelationType.ASSOCIATED_WITH,
                label="Instant Messenger Presence",
            )
        )

        # 3. Telegram Direct Pivot
        tg_url = f"https://t.me/+{e164.lstrip('+')}"
        tg_id = f"presence:telegram:{e164.lstrip('+')}"
        tg_node = self.create_node(
            node_id=tg_id,
            node_type=TargetType.GENERIC,
            value=tg_url,
            label="Telegram Contact Link",
            attributes={
                "platform": "Telegram",
                "direct_profile_url": tg_url,
                "phone_number": e164,
            },
        )
        nodes.append(tg_node)
        edges.append(
            self.create_edge(
                source_id=root_node_id,
                target_id=tg_id,
                relation_type=RelationType.ASSOCIATED_WITH,
                label="Instant Messenger Presence",
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
