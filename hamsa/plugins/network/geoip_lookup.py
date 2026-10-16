"""
Free IP Geolocation & ISP Autonomous System Reconnaissance Plugin for Hamsa OSINT Framework.
Extracts geographic location (latitude/longitude), city, country, ASN, and ISP details
using free public endpoints without API keys (inspired by API-s-for-OSINT).
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


class GeoIPLookupPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="geoip_asn_resolver",
        version="0.1.0",
        author="Hamsa Team",
        description="Resolves physical geolocation, ISP organization, and Autonomous System (ASN) from IP or domain.",
        target_types=[TargetType.IP, TargetType.DOMAIN],
        requires_network=True,
    )

    def __init__(self) -> None:
        super().__init__()
        self.http_client = HttpClient(timeout=7.0, default_delay=0.1)

    async def _resolve_ip(self, target: str) -> Optional[str]:
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
        logs: List[str] = [f"Performing GeoIP & ASN resolution for target: '{target}'"]

        ip_addr = await self._resolve_ip(target)
        if not ip_addr:
            logs.append(f"Could not resolve '{target}' to an IP address.")
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
            attributes={"target": target},
        )
        nodes.append(root_node)

        # Free IP Geolocation via ip-api.com
        geo_url = f"http://ip-api.com/json/{ip_addr}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        try:
            status, data = await self.http_client.get_json(geo_url)
            if status == 200 and isinstance(data, dict) and data.get("status") == "success":
                lat = data.get("lat")
                lon = data.get("lon")
                country = data.get("country", "")
                city = data.get("city", "")
                region = data.get("regionName", "")
                isp = data.get("isp", "")
                org = data.get("org", "")
                asn = data.get("as", "")

                root_node.attributes.update({
                    "country": country,
                    "city": city,
                    "region": region,
                    "isp": isp,
                    "org": org,
                    "asn": asn,
                    "latitude": lat,
                    "longitude": lon,
                })
                logs.append(f"Resolved physical location: {city}, {region}, {country} (Lat: {lat}, Lon: {lon})")
                logs.append(f"Autonomous System / ISP: {asn} ({org or isp})")

                # Create Location Node for Spatial Geofencing
                if lat is not None and lon is not None:
                    loc_id = f"location:{lat}_{lon}"
                    loc_node = self.create_node(
                        node_id=loc_id,
                        node_type=TargetType.LOCATION,
                        value=f"{lat},{lon}",
                        label=f"GPS: {city or country} ({lat}, {lon})",
                        attributes={
                            "latitude": float(lat),
                            "longitude": float(lon),
                            "city": city,
                            "country": country,
                            "source": "GeoIP Resolution",
                        },
                    )
                    nodes.append(loc_node)
                    edges.append(
                        self.create_edge(
                            source_id=root_node_id,
                            target_id=loc_id,
                            relation_type=RelationType.LOCATED_AT,
                            label="Physical Hosting Location",
                        )
                    )

                # Create Organization / ASN Node
                if org or asn:
                    org_name = org or isp or asn
                    org_id = f"organization:{org_name.lower().replace(' ', '_')[:40]}"
                    org_node = self.create_node(
                        node_id=org_id,
                        node_type=TargetType.ORGANIZATION,
                        value=org_name,
                        label=f"ISP: {org_name}",
                        attributes={"asn": asn, "isp": isp, "org": org},
                    )
                    nodes.append(org_node)
                    edges.append(
                        self.create_edge(
                            source_id=root_node_id,
                            target_id=org_id,
                            relation_type=RelationType.OPERATED_BY,
                            label="Autonomous System Operator",
                        )
                    )
            else:
                logs.append(f"GeoIP endpoint message: {data.get('message') if isinstance(data, dict) else 'Not Found'}")
        except Exception as e:
            logs.append(f"GeoIP query note: {e}")

        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
        )
