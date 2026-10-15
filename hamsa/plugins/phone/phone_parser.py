"""
Phone Intelligence and Carrier Parser Plugin for Hamsa OSINT Framework.
Normalizes phone numbers, determines international country code, resolves carrier, and creates intel links.
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

# Country calling code mappings
COUNTRY_CODES = {
    "62": "Indonesia",
    "1": "United States / Canada",
    "44": "United Kingdom",
    "60": "Malaysia",
    "65": "Singapore",
    "61": "Australia",
    "81": "Japan",
    "91": "India",
    "49": "Germany",
    "33": "France",
    "86": "China",
}

# Indonesian prefix lookup for carriers
INDONESIAN_CARRIERS = {
    ("0811", "0812", "0813", "0821", "0822", "0823", "0852", "0853", "0851"): "Telkomsel",
    ("0814", "0815", "0816", "0855", "0856", "0857", "0858"): "Indosat Ooredoo Hutchison",
    ("0817", "0818", "0819", "0859", "0877", "0878"): "XL Axiata",
    ("0831", "0832", "0833", "0838"): "Axis (XL Axiata)",
    ("0895", "0896", "0897", "0898", "0899"): "Tri (Indosat Ooredoo Hutchison)",
    ("0881", "0882", "0883", "0884", "0885", "0886", "0887", "0888", "0889"): "Smartfren",
}


class PhoneParserPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="phone_intelligence_parser",
        version="0.1.0",
        author="Hamsa Team",
        description="Normalizes phone numbers, extracts country/carrier, and generates direct investigation pivot links.",
        target_types=[TargetType.PHONE],
        requires_network=False,
    )

    def _normalize(self, raw_phone: str) -> str:
        clean = re.sub(r"[^\d+]", "", raw_phone)
        if clean.startswith("08"):
            clean = "+62" + clean[1:]
        elif not clean.startswith("+"):
            clean = "+" + clean
        return clean

    def _resolve_carrier(self, clean_number: str) -> Optional[str]:
        if clean_number.startswith("+62"):
            local_format = "0" + clean_number[3:]
            prefix4 = local_format[:4]
            for prefixes, carrier in INDONESIAN_CARRIERS.items():
                if prefix4 in prefixes:
                    return carrier
        return None

    def _resolve_country(self, clean_number: str) -> str:
        num = clean_number.lstrip("+")
        for length in (3, 2, 1):
            code = num[:length]
            if code in COUNTRY_CODES:
                return COUNTRY_CODES[code]
        return "Unknown Country"

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        start_time = asyncio.get_event_loop().time()
        normalized = self._normalize(target)
        root_node_id = f"phone:{normalized}"

        country = self._resolve_country(normalized)
        carrier = self._resolve_carrier(normalized)

        root_node = self.create_node(
            node_id=root_node_id,
            node_type=TargetType.PHONE,
            value=normalized,
            label=f"Phone: {normalized}",
            attributes={
                "original_input": target,
                "e164_format": normalized,
                "country": country,
                "carrier": carrier or "Unidentified",
                "whatsapp_link": f"https://wa.me/{normalized.lstrip('+')}",
                "telegram_link": f"https://t.me/+{normalized.lstrip('+')}",
            },
        )

        nodes: List[EntityNode] = [root_node]
        edges: List[RelationEdge] = []
        logs: List[str] = [f"Normalized phone '{target}' to E.164: '{normalized}' (Country: {country})"]

        # Add country node
        country_id = f"location:{country.lower().replace(' ', '_')}"
        country_node = self.create_node(
            node_id=country_id,
            node_type=TargetType.LOCATION,
            value=country,
            label=f"Country: {country}",
            attributes={"country_name": country},
        )
        nodes.append(country_node)
        edges.append(
            self.create_edge(
                source_id=root_node_id,
                target_id=country_id,
                relation_type=RelationType.LOCATED_AT,
                label="Country of Origin",
            )
        )

        # Add carrier node if resolved
        if carrier:
            logs.append(f"Identified telecommunication operator: {carrier}")
            carrier_id = f"carrier:{carrier.lower().replace(' ', '_')}"
            carrier_node = self.create_node(
                node_id=carrier_id,
                node_type=TargetType.GENERIC,
                value=carrier,
                label=f"Carrier: {carrier}",
                attributes={"telecom_operator": carrier},
            )
            nodes.append(carrier_node)
            edges.append(
                self.create_edge(
                    source_id=root_node_id,
                    target_id=carrier_id,
                    relation_type=RelationType.OPERATED_BY,
                    label="Operated By",
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
