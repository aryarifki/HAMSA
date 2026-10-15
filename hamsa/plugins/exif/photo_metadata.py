"""
Photo EXIF & Geolocation Extraction Plugin for Hamsa OSINT Framework.
Extracts camera model, timestamp, and GPS coordinates directly from JPEG binary markers.
Zero external dependencies (pure Python standard library struct/os).
"""

import asyncio
import os
import struct
from typing import Any, Dict, List, Optional, Tuple
from hamsa.core.models import (
    EntityNode,
    PluginMetadata,
    PluginResult,
    RelationEdge,
    RelationType,
    TargetType,
)
from hamsa.plugins.base import BasePlugin

# Standard EXIF TIFF Tags
TAG_MAKE = 0x010F
TAG_MODEL = 0x0110
TAG_SOFTWARE = 0x0131
TAG_DATETIME = 0x0132
TAG_GPS_INFO = 0x8825

# GPS Sub-tags
GPS_LAT_REF = 1
GPS_LAT = 2
GPS_LON_REF = 3
GPS_LON = 4


def _dms_to_decimal(degrees: float, minutes: float, seconds: float, ref: str) -> float:
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ["S", "W"]:
        decimal = -decimal
    return round(decimal, 6)


class ExifMetadataPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="photo_exif_metadata",
        version="0.1.0",
        author="Hamsa Team",
        description="Extracts camera device model, timestamp, and GPS location coordinates from photos.",
        target_types=[TargetType.IMAGE],
        requires_network=False,
    )

    def _parse_rational(self, data: bytes, offset: int, endian: str) -> float:
        num, denom = struct.unpack(f"{endian}II", data[offset : offset + 8])
        return (num / denom) if denom != 0 else 0.0

    def _extract_jpeg_exif(self, file_path: str) -> Dict[str, Any]:
        """Pure Python JPEG APP1 EXIF parser."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")

        exif_data: Dict[str, Any] = {}
        with open(file_path, "rb") as f:
            header = f.read(2)
            if header != b"\xff\xd8":
                return exif_data  # Not a valid JPEG

            while True:
                marker_bytes = f.read(2)
                if len(marker_bytes) < 2:
                    break
                marker, = struct.unpack(">H", marker_bytes)
                if marker == 0xFFDA or marker == 0xFFD9:
                    break  # Start of scan or end of image
                length, = struct.unpack(">H", f.read(2))
                if length < 2:
                    break
                payload = f.read(length - 2)

                # APP1 Marker (EXIF)
                if marker == 0xFFE1 and payload.startswith(b"Exif\x00\x00"):
                    tiff_data = payload[6:]
                    exif_data.update(self._parse_tiff(tiff_data))
                    break
        return exif_data

    def _parse_tiff(self, data: bytes) -> Dict[str, Any]:
        parsed: Dict[str, Any] = {}
        if len(data) < 8:
            return parsed

        endian_marker = data[:2]
        if endian_marker == b"II":
            endian = "<"
        elif endian_marker == b"MM":
            endian = ">"
        else:
            return parsed

        ifd0_offset, = struct.unpack(f"{endian}I", data[4:8])
        if ifd0_offset >= len(data):
            return parsed

        # Parse IFD0
        gps_offset = None
        num_entries, = struct.unpack(f"{endian}H", data[ifd0_offset : ifd0_offset + 2])
        curr = ifd0_offset + 2

        for _ in range(num_entries):
            if curr + 12 > len(data):
                break
            tag, typ, count, val_offset = struct.unpack(f"{endian}HHI4s", data[curr : curr + 12])
            curr += 12

            if tag == TAG_MAKE:
                val_ptr, = struct.unpack(f"{endian}I", val_offset)
                if val_ptr < len(data):
                    parsed["make"] = data[val_ptr : val_ptr + count].decode("utf-8", errors="ignore").strip("\x00 ")
            elif tag == TAG_MODEL:
                val_ptr, = struct.unpack(f"{endian}I", val_offset)
                if val_ptr < len(data):
                    parsed["model"] = data[val_ptr : val_ptr + count].decode("utf-8", errors="ignore").strip("\x00 ")
            elif tag == TAG_DATETIME:
                val_ptr, = struct.unpack(f"{endian}I", val_offset)
                if val_ptr < len(data):
                    parsed["datetime"] = data[val_ptr : val_ptr + count].decode("utf-8", errors="ignore").strip("\x00 ")
            elif tag == TAG_SOFTWARE:
                val_ptr, = struct.unpack(f"{endian}I", val_offset)
                if val_ptr < len(data):
                    parsed["software"] = data[val_ptr : val_ptr + count].decode("utf-8", errors="ignore").strip("\x00 ")
            elif tag == TAG_GPS_INFO:
                gps_offset, = struct.unpack(f"{endian}I", val_offset)

        # Parse GPS Sub-IFD if present
        if gps_offset and gps_offset + 2 <= len(data):
            num_gps, = struct.unpack(f"{endian}H", data[gps_offset : gps_offset + 2])
            gps_curr = gps_offset + 2
            gps_tags: Dict[int, Any] = {}

            for _ in range(num_gps):
                if gps_curr + 12 > len(data):
                    break
                gtag, gtyp, gcount, gval = struct.unpack(f"{endian}HHI4s", data[gps_curr : gps_curr + 12])
                gps_curr += 12
                if gtag in (GPS_LAT_REF, GPS_LON_REF):
                    gps_tags[gtag] = gval[:1].decode("utf-8", errors="ignore")
                elif gtag in (GPS_LAT, GPS_LON):
                    gptr, = struct.unpack(f"{endian}I", gval)
                    if gptr + 24 <= len(data):
                        d = self._parse_rational(data, gptr, endian)
                        m = self._parse_rational(data, gptr + 8, endian)
                        s = self._parse_rational(data, gptr + 16, endian)
                        gps_tags[gtag] = (d, m, s)

            if GPS_LAT in gps_tags and GPS_LAT_REF in gps_tags and GPS_LON in gps_tags and GPS_LON_REF in gps_tags:
                lat_d, lat_m, lat_s = gps_tags[GPS_LAT]
                lon_d, lon_m, lon_s = gps_tags[GPS_LON]
                dec_lat = _dms_to_decimal(lat_d, lat_m, lat_s, gps_tags[GPS_LAT_REF])
                dec_lon = _dms_to_decimal(lon_d, lon_m, lon_s, gps_tags[GPS_LON_REF])
                parsed["latitude"] = dec_lat
                parsed["longitude"] = dec_lon

        return parsed

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        start_time = asyncio.get_event_loop().time()
        file_name = os.path.basename(target)
        root_node_id = f"image:{file_name}"

        root_node = self.create_node(
            node_id=root_node_id,
            node_type=TargetType.IMAGE,
            value=target,
            label=f"Photo: {file_name}",
            attributes={"file_path": target},
        )

        nodes: List[EntityNode] = [root_node]
        edges: List[RelationEdge] = []
        logs: List[str] = [f"Analyzing EXIF metadata from photo: '{target}'"]

        try:
            exif = await asyncio.to_thread(self._extract_jpeg_exif, target)
            device_parts = []
            if exif.get("make"):
                device_parts.append(exif["make"])
            if exif.get("model"):
                device_parts.append(exif["model"])

            device_name = " ".join(device_parts).strip()
            if device_name:
                logs.append(f"Discovered camera hardware: {device_name}")
                dev_id = f"device:{device_name.lower().replace(' ', '_')}"
                dev_node = self.create_node(
                    node_id=dev_id,
                    node_type=TargetType.DEVICE,
                    value=device_name,
                    label=f"Camera: {device_name}",
                    attributes={
                        "make": exif.get("make"),
                        "model": exif.get("model"),
                        "software": exif.get("software"),
                        "timestamp": exif.get("datetime"),
                    },
                )
                nodes.append(dev_node)
                edges.append(
                    self.create_edge(
                        source_id=root_node_id,
                        target_id=dev_id,
                        relation_type=RelationType.CAPTURED_BY,
                        label="Captured With",
                    )
                )

            if "latitude" in exif and "longitude" in exif:
                lat = exif["latitude"]
                lon = exif["longitude"]
                gmaps = f"https://www.google.com/maps?q={lat},{lon}"
                osm = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}"
                logs.append(f"Extracted GPS Coordinates: {lat}, {lon}")

                # Reverse Geocoding via OpenStreetMap Nominatim
                display_address = f"{lat}, {lon}"
                address_details: Dict[str, Any] = {}
                try:
                    from hamsa.utils.http import HttpClient
                    client = HttpClient(timeout=6.0)
                    geo_url = (
                        f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
                    )
                    status, geo_data = await client.get_json(
                        geo_url,
                        headers={"User-Agent": "HamsaOSINT/0.1.0 (contact@hamsa-osint.org)"},
                    )
                    if status == 200 and isinstance(geo_data, dict):
                        display_address = geo_data.get("display_name", display_address)
                        address_details = geo_data.get("address", {})
                        logs.append(f"Resolved physical address: {display_address}")
                except Exception as geo_err:
                    logs.append(f"Geocoding note: {geo_err}")

                loc_id = f"location:{lat}_{lon}"
                label_text = f"GPS: {address_details.get('suburb') or address_details.get('city') or lat}, {lon}"
                loc_node = self.create_node(
                    node_id=loc_id,
                    node_type=TargetType.LOCATION,
                    value=display_address,
                    label=label_text,
                    attributes={
                        "latitude": lat,
                        "longitude": lon,
                        "physical_address": display_address,
                        "address_details": address_details,
                        "google_maps": gmaps,
                        "openstreetmap": osm,
                    },
                    confidence=1.0,
                )
                nodes.append(loc_node)
                edges.append(
                    self.create_edge(
                        source_id=root_node_id,
                        target_id=loc_id,
                        relation_type=RelationType.LOCATED_AT,
                        label="Photo GPS Location",
                    )
                )

            if not device_name and "latitude" not in exif:
                logs.append("No hardware or GPS metadata tags found in file (metadata may have been stripped).")

        except Exception as e:
            logs.append(f"Error parsing image EXIF: {e}")

        duration = asyncio.get_event_loop().time() - start_time
        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
            execution_time_seconds=round(duration, 2),
        )
