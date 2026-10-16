"""
HAMSA Graph Intelligence Analytics Engine
Algorithms for Shortest Path Correlation (Dijkstra/BFS), Entity Centrality Scoring,
Bridge/Brokerage Detection, and Cluster Decomposition.
Pure Python Standard Library implementation.
"""

import math
from collections import deque
from typing import Dict, List, Any, Optional, Set, Tuple

from hamsa.core.graph import KnowledgeGraph
from hamsa.core.models import EntityNode, RelationEdge, TargetType


class GraphAnalyticsEngine:
    """Forensic graph analytics engine for complex entity correlation."""

    @classmethod
    def find_shortest_path(
        cls,
        graph: KnowledgeGraph,
        source_id: str,
        target_id: str
    ) -> Dict[str, Any]:
        """
        Finds the shortest relational path between two entities using bidirectional BFS.
        Returns the connecting chain of nodes and edges with a forensic narrative.
        """
        if source_id not in graph.nodes:
            return {"found": False, "error": f"Source entity '{source_id}' not found in graph."}
        if target_id not in graph.nodes:
            return {"found": False, "error": f"Target entity '{target_id}' not found in graph."}

        if source_id == target_id:
            return {
                "found": True,
                "hops": 0,
                "nodes": [graph.nodes[source_id].to_dict()],
                "edges": [],
                "narrative": f"Source and target are identical: {source_id}"
            }

        # Build undirected adjacency map: node_id -> list of (neighbor_id, edge)
        adj: Dict[str, List[Tuple[str, RelationEdge]]] = {nid: [] for nid in graph.nodes}
        for edge in graph.edges:
            adj.setdefault(edge.source_id, []).append((edge.target_id, edge))
            adj.setdefault(edge.target_id, []).append((edge.source_id, edge))

        # Standard BFS
        queue = deque([(source_id, [source_id], [])])
        visited = {source_id}

        while queue:
            current_id, path_nodes, path_edges = queue.popleft()

            if current_id == target_id:
                # Path found!
                node_objs = [graph.nodes[nid].to_dict() for nid in path_nodes if nid in graph.nodes]
                edge_objs = [e.to_dict() for e in path_edges]

                # Construct explanatory narrative
                narrative_steps = []
                for i in range(len(path_nodes) - 1):
                    s_label = graph.nodes[path_nodes[i]].label or path_nodes[i]
                    t_label = graph.nodes[path_nodes[i+1]].label or path_nodes[i+1]
                    e_label = path_edges[i].label or path_edges[i].relation_type.value
                    narrative_steps.append(f"[{s_label}] ──({e_label})──► [{t_label}]")

                return {
                    "found": True,
                    "hops": len(path_edges),
                    "node_ids": path_nodes,
                    "nodes": node_objs,
                    "edges": edge_objs,
                    "narrative": " ➔ ".join(narrative_steps)
                }

            for neighbor_id, edge in adj.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path_nodes + [neighbor_id], path_edges + [edge]))

        return {
            "found": False,
            "hops": -1,
            "nodes": [],
            "edges": [],
            "narrative": f"No relational path found connecting '{source_id}' and '{target_id}'."
        }

    @classmethod
    def compute_centrality(cls, graph: KnowledgeGraph) -> Dict[str, Any]:
        """
        Computes Degree Centrality and Bridge Scores to identify key coordinators (kingpins).
        """
        total_nodes = len(graph.nodes)
        if total_nodes <= 1:
            return {"top_actors": [], "key_bridges": []}

        degrees: Dict[str, int] = {nid: 0 for nid in graph.nodes}
        type_connections: Dict[str, Set[str]] = {nid: set() for nid in graph.nodes}

        for edge in graph.edges:
            degrees[edge.source_id] = degrees.get(edge.source_id, 0) + 1
            degrees[edge.target_id] = degrees.get(edge.target_id, 0) + 1

            s_node = graph.nodes.get(edge.source_id)
            t_node = graph.nodes.get(edge.target_id)
            if s_node and t_node:
                type_connections[edge.source_id].add(t_node.type.value)
                type_connections[edge.target_id].add(s_node.type.value)

        # Ranked list of top actors by degree centrality
        ranked_actors = []
        for nid, deg in sorted(degrees.items(), key=lambda x: x[1], reverse=True):
            node = graph.nodes.get(nid)
            if not node:
                continue
            normalized_score = round(deg / max(1, total_nodes - 1), 3)
            ranked_actors.append({
                "node_id": nid,
                "label": node.label or node.value,
                "type": node.type.value,
                "degree": deg,
                "centrality_score": normalized_score,
                "connected_entity_types": list(type_connections.get(nid, set()))
            })

        # Key bridges: nodes that connect multiple distinct entity types (e.g., Phone linking Username & Email)
        bridges = [
            actor for actor in ranked_actors
            if len(actor["connected_entity_types"]) >= 2 and actor["degree"] >= 2
        ]

        return {
            "total_entities": total_nodes,
            "total_relations": len(graph.edges),
            "top_actors": ranked_actors[:10],
            "key_bridges": bridges[:5]
        }

    @classmethod
    def detect_clusters(cls, graph: KnowledgeGraph) -> List[Dict[str, Any]]:
        """
        Decomposes the knowledge network into connected components (sub-clusters).
        Allows investigators to isolate separate rings of suspects.
        """
        adj: Dict[str, Set[str]] = {nid: set() for nid in graph.nodes}
        for edge in graph.edges:
            adj.setdefault(edge.source_id, set()).add(edge.target_id)
            adj.setdefault(edge.target_id, set()).add(edge.source_id)

        visited = set()
        clusters = []

        for nid in graph.nodes:
            if nid not in visited:
                cluster_nodes = []
                queue = deque([nid])
                visited.add(nid)

                while queue:
                    curr = queue.popleft()
                    cluster_nodes.append(curr)
                    for nbr in adj.get(curr, set()):
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)

                # Collect cluster details
                types_in_cluster = set()
                for c_nid in cluster_nodes:
                    node = graph.nodes.get(c_nid)
                    if node:
                        types_in_cluster.add(node.type.value)

                clusters.append({
                    "cluster_id": f"cluster_{len(clusters) + 1}",
                    "size": len(cluster_nodes),
                    "node_ids": cluster_nodes,
                    "entity_types": list(types_in_cluster),
                    "lead_node": cluster_nodes[0]
                })

        clusters.sort(key=lambda x: x["size"], reverse=True)
        return clusters


class SpatialFilterEngine:
    """
    Forensic Spatial & Geofencing Filter Engine.
    Provides computational geometry algorithms for GPS coordinates extracted from
    EXIF metadata, IP geolocations, and physical tracker nodes:
      1. Haversine Circular Radius Query (Great-Circle Distance)
      2. Axis-Aligned Bounding Box (AABB) with Antimeridian support
      3. Ray-Casting Point-in-Polygon (PIP) for arbitrary geofence boundaries
    Zero external C-extension dependencies (100% Python standard library).
    """

    EARTH_RADIUS_KM: float = 6371.0088

    @classmethod
    def haversine_distance_km(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates Great-Circle distance between two points on Earth in kilometers using the Haversine formula.
        """
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
        )
        # Clamp to avoid floating point precision overflow
        a = min(1.0, max(0.0, a))
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(cls.EARTH_RADIUS_KM * c, 4)

    @classmethod
    def is_within_radius(
        cls,
        lat: float,
        lon: float,
        center_lat: float,
        center_lon: float,
        radius_km: float,
    ) -> Tuple[bool, float]:
        """
        Checks if (lat, lon) is within a circular radius of (center_lat, center_lon).
        Returns (is_inside, distance_km).
        """
        dist = cls.haversine_distance_km(lat, lon, center_lat, center_lon)
        return (dist <= radius_km, dist)

    @classmethod
    def is_within_bounding_box(
        cls,
        lat: float,
        lon: float,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
    ) -> bool:
        """
        Checks if (lat, lon) falls within an Axis-Aligned Bounding Box [min_lat, max_lat] x [min_lon, max_lon].
        Supports boundary boxes crossing the 180th meridian (Antimeridian).
        """
        if not (min_lat <= lat <= max_lat):
            return False

        if min_lon <= max_lon:
            return min_lon <= lon <= max_lon
        else:
            # Crosses 180th meridian (e.g. min_lon = 175, max_lon = -175)
            return lon >= min_lon or lon <= max_lon

    @classmethod
    def is_point_in_polygon(
        cls,
        lat: float,
        lon: float,
        polygon: List[Tuple[float, float]],
    ) -> bool:
        """
        Ray-Casting algorithm (Jordan Curve Theorem) to determine if a GPS coordinate (lat, lon)
        lies within an arbitrary (convex or concave) polygon geofence.
        polygon is a list of (lat, lon) vertex tuples.
        """
        num_vertices = len(polygon)
        if num_vertices < 3:
            return False

        inside = False
        j = num_vertices - 1

        for i in range(num_vertices):
            v_i_lat, v_i_lon = polygon[i]
            v_j_lat, v_j_lon = polygon[j]

            # Ray cast horizontally across longitude
            if (v_i_lat > lat) != (v_j_lat > lat):
                # Calculate the longitude intersection point of the edge with the horizontal ray at latitude `lat`
                slope = (v_j_lon - v_i_lon) / (v_j_lat - v_i_lat)
                intersect_lon = slope * (lat - v_i_lat) + v_i_lon
                if lon < intersect_lon:
                    inside = not inside

            j = i

        return inside

    @classmethod
    def extract_node_coordinates(cls, node: EntityNode) -> Optional[Tuple[float, float]]:
        """
        Extracts decimal latitude and longitude from an EntityNode, whether from attributes
        (e.g., EXIF metadata, IP geolocations, mobile tracker) or node value / node id.
        """
        attrs = node.attributes or {}

        # 1. Direct attribute keys
        for lat_key in ("latitude", "lat", "gps_latitude"):
            for lon_key in ("longitude", "lon", "lng", "gps_longitude"):
                if lat_key in attrs and lon_key in attrs:
                    try:
                        lat_val = float(attrs[lat_key])
                        lon_val = float(attrs[lon_key])
                        if -90.0 <= lat_val <= 90.0 and -180.0 <= lon_val <= 180.0:
                            return (lat_val, lon_val)
                    except (ValueError, TypeError):
                        pass

        # 2. Check if node.value is formatted as "lat,lon" or "lat, lon"
        val = str(node.value).strip()
        if "," in val:
            parts = val.split(",", 1)
            try:
                lat_val = float(parts[0].strip())
                lon_val = float(parts[1].strip())
                if -90.0 <= lat_val <= 90.0 and -180.0 <= lon_val <= 180.0:
                    return (lat_val, lon_val)
            except (ValueError, TypeError):
                pass

        # 3. Check if node.id is "location:lat_lon"
        if node.id.startswith("location:"):
            id_val = node.id[len("location:"):]
            if "_" in id_val:
                parts = id_val.split("_", 1)
                try:
                    lat_val = float(parts[0])
                    lon_val = float(parts[1])
                    if -90.0 <= lat_val <= 90.0 and -180.0 <= lon_val <= 180.0:
                        return (lat_val, lon_val)
                except (ValueError, TypeError):
                    pass

        return None

    @classmethod
    def filter_graph_locations(
        cls,
        graph: KnowledgeGraph,
        filter_type: str,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None,
        polygon: Optional[List[Tuple[float, float]]] = None,
    ) -> Dict[str, Any]:
        """
        Filters all location-bearing nodes in the knowledge graph against spatial parameters.
        Filter types: 'radius', 'bbox', 'polygon'.
        """
        total_nodes = len(graph.nodes)
        evaluated_nodes = 0
        matches: List[Dict[str, Any]] = []

        norm_type = filter_type.lower().strip()

        for node_id, node in graph.nodes.items():
            coords = cls.extract_node_coordinates(node)
            if coords is None:
                continue

            evaluated_nodes += 1
            lat, lon = coords
            is_match = False
            dist_km: Optional[float] = None

            if norm_type == "radius":
                if center_lat is None or center_lon is None or radius_km is None:
                    raise ValueError("Missing 'center_lat', 'center_lon', or 'radius_km' for radius filter.")
                is_match, dist_km = cls.is_within_radius(lat, lon, center_lat, center_lon, radius_km)

            elif norm_type in ("bbox", "bounding_box"):
                if None in (min_lat, max_lat, min_lon, max_lon):
                    raise ValueError("Missing bounding box bounds ('min_lat', 'max_lat', 'min_lon', 'max_lon').")
                is_match = cls.is_within_bounding_box(lat, lon, min_lat, max_lat, min_lon, max_lon)
                if center_lat is not None and center_lon is not None:
                    dist_km = cls.haversine_distance_km(lat, lon, center_lat, center_lon)

            elif norm_type == "polygon":
                if not polygon or len(polygon) < 3:
                    raise ValueError("Polygon filter requires at least 3 coordinate vertex pairs.")
                poly_tuples = [(float(p[0]), float(p[1])) for p in polygon]
                is_match = cls.is_point_in_polygon(lat, lon, poly_tuples)
                if center_lat is not None and center_lon is not None:
                    dist_km = cls.haversine_distance_km(lat, lon, center_lat, center_lon)

            else:
                raise ValueError(f"Unknown filter_type '{filter_type}'. Supported: 'radius', 'bbox', 'polygon'.")

            if is_match:
                matches.append({
                    "node_id": node.id,
                    "label": node.label or node.value,
                    "type": node.type.value if hasattr(node.type, "value") else str(node.type),
                    "latitude": lat,
                    "longitude": lon,
                    "distance_km": dist_km,
                    "node": node.to_dict(),
                })

        # Sort matches by distance if radius filter was used
        if norm_type == "radius":
            matches.sort(key=lambda m: m["distance_km"] if m["distance_km"] is not None else float("inf"))

        return {
            "filter_type": norm_type,
            "total_nodes_scanned": total_nodes,
            "location_nodes_evaluated": evaluated_nodes,
            "matched_count": len(matches),
            "matches": matches,
        }

    @classmethod
    def trilaterate_coordinates(
        cls,
        p1: Tuple[float, float],
        r1_km: float,
        p2: Tuple[float, float],
        r2_km: float,
        p3: Tuple[float, float],
        r3_km: float,
    ) -> Tuple[float, float]:
        """
        Solves 2D trilateration on local tangent plane from 3 reference points and circle radii
        (inspired by CCTV people-nearby triangulation).
        Returns estimated (latitude, longitude).
        """
        lat1, lon1 = p1
        lat2, lon2 = p2
        lat3, lon3 = p3

        # Project to local Cartesian plane with origin at p1
        r_earth = cls.EARTH_RADIUS_KM
        cos_lat1 = math.cos(math.radians(lat1))

        x2 = r_earth * math.radians(lon2 - lon1) * cos_lat1
        y2 = r_earth * math.radians(lat2 - lat1)

        x3 = r_earth * math.radians(lon3 - lon1) * cos_lat1
        y3 = r_earth * math.radians(lat3 - lat1)

        # Circle intersection linear equations:
        # 2*x*x2 + 2*y*y2 = x2^2 + y2^2 + r1^2 - r2^2
        # 2*x*x3 + 2*y*y3 = x3^2 + y3^2 + r1^2 - r3^2
        A = 2.0 * x2
        B = 2.0 * y2
        C = x2**2 + y2**2 + r1_km**2 - r2_km**2

        D = 2.0 * x3
        E = 2.0 * y3
        F = x3**2 + y3**2 + r1_km**2 - r3_km**2

        det = A * E - B * D
        if abs(det) < 1e-9:
            # Collinear points fallback: midpoint of p1 and p2
            return round((lat1 + lat2) / 2.0, 6), round((lon1 + lon2) / 2.0, 6)

        x = (C * E - B * F) / det
        y = (A * F - C * D) / det

        # Convert local coordinates back to (lat, lon)
        est_lat = lat1 + math.degrees(y / r_earth)
        est_lon = lon1 + math.degrees(x / (r_earth * max(cos_lat1, 1e-6)))

        return round(est_lat, 6), round(est_lon, 6)


class PersonaResolutionEngine:
    """
    Union-Find Disjoint-Set Persona Resolution Engine (inspired by nox-framework).
    Merges fragmented identity nodes (usernames, emails, phone numbers, social accounts)
    into unified real-world Persona Clusters based on shared pivot identifiers.
    """

    @classmethod
    def resolve_personas(cls, graph: KnowledgeGraph) -> List[Dict[str, Any]]:
        parent: Dict[str, str] = {nid: nid for nid in graph.nodes}

        def find(i: str) -> str:
            path = []
            while parent[i] != i:
                path.append(i)
                i = parent[i]
            for node in path:
                parent[node] = i
            return i

        def union(i: str, j: str) -> None:
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        # 1. Pivot key index: pivot_key -> list of node_ids
        pivot_map: Dict[str, List[str]] = {}

        for nid, node in graph.nodes.items():
            # Index by primary value for emails, phones
            if node.type in (TargetType.EMAIL, TargetType.PHONE):
                clean_val = node.value.strip().lower()
                pivot_map.setdefault(f"{node.type.value}:{clean_val}", []).append(nid)

            attrs = node.attributes or {}
            for email_key in ("public_email", "email", "recovery_email"):
                if attrs.get(email_key):
                    clean_e = str(attrs[email_key]).strip().lower()
                    pivot_map.setdefault(f"email:{clean_e}", []).append(nid)

            for phone_key in ("public_phone", "phone", "recovery_phone", "raw_phone"):
                if attrs.get(phone_key):
                    clean_p = str(attrs[phone_key]).strip()
                    pivot_map.setdefault(f"phone:{clean_p}", []).append(nid)

        # Union nodes sharing identical verified pivot keys
        for pivot, node_ids in pivot_map.items():
            if len(node_ids) > 1:
                first = node_ids[0]
                for other in node_ids[1:]:
                    union(first, other)

        # Union nodes connected via direct associative edges
        for edge in graph.edges:
            rel = edge.relation_type.value if hasattr(edge.relation_type, "value") else str(edge.relation_type)
            if rel in ("ASSOCIATED_WITH", "DERIVED_FROM", "REGISTERED_ON"):
                if edge.source_id in parent and edge.target_id in parent:
                    union(edge.source_id, edge.target_id)

        # Group into clusters
        clusters: Dict[str, List[str]] = {}
        for nid in graph.nodes:
            root = find(nid)
            clusters.setdefault(root, []).append(nid)

        results = []
        cluster_idx = 1
        for root, member_ids in sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True):
            member_nodes = [graph.nodes[nid].to_dict() for nid in member_ids if nid in graph.nodes]
            types = list({n["type"] for n in member_nodes})
            emails = list({n["value"] for n in member_nodes if n["type"] == TargetType.EMAIL.value})
            phones = list({n["value"] for n in member_nodes if n["type"] == TargetType.PHONE.value})
            usernames = list({n["value"] for n in member_nodes if n["type"] == TargetType.USERNAME.value})

            lead_label = graph.nodes[root].label if root in graph.nodes else member_ids[0]

            results.append({
                "persona_id": f"persona_{cluster_idx}",
                "lead_label": lead_label,
                "size": len(member_ids),
                "node_ids": member_ids,
                "entity_types": types,
                "correlated_emails": emails,
                "correlated_phones": phones,
                "correlated_usernames": usernames,
                "nodes": member_nodes,
            })
            cluster_idx += 1

        return results


class RiskScoringEngine:
    """
    Forensic Threat & Risk Scoring Engine (inspired by nox-framework).
    Evaluates compromise severity and generates FAIR-aligned 0-100 risk assessments.
    """

    @classmethod
    def evaluate_graph_risk(cls, graph: KnowledgeGraph) -> Dict[str, Any]:
        score = 0.0
        factors = []

        total_nodes = len(graph.nodes)
        if total_nodes == 0:
            return {"score": 0.0, "severity": "LOW", "factors": ["No target assets in graph."]}

        # 1. Infostealer exposure
        infostealers = [n for n in graph.nodes.values() if "infostealer" in n.id.lower() or "malware" in n.id.lower()]
        if infostealers:
            score += 35.0
            factors.append(f"CRITICAL: {len(infostealers)} infostealer malware infection record(s) detected.")

        # 2. Breach records
        breaches = [n for n in graph.nodes.values() if n.type == TargetType.BREACH or "breach" in n.id.lower()]
        if breaches:
            added = min(25.0, len(breaches) * 8.0)
            score += added
            factors.append(f"HIGH: {len(breaches)} public corporate/service breach record(s) identified.")

        # 3. Telecommunication & Physical Location Exposure
        locations = [n for n in graph.nodes.values() if n.type == TargetType.LOCATION]
        phones = [n for n in graph.nodes.values() if n.type == TargetType.PHONE]
        if locations:
            score += 15.0
            factors.append(f"MEDIUM: Physical GPS coordinates ({len(locations)} location node(s)) discovered.")
        if phones:
            score += 10.0
            factors.append(f"MEDIUM: Direct telephone line ({len(phones)} phone node(s)) exposed.")

        # 4. Digital Footprint Breadth
        usernames = [n for n in graph.nodes.values() if n.type == TargetType.USERNAME or n.id.startswith("account:")]
        if len(usernames) >= 5:
            score += 15.0
            factors.append(f"LOW: Broad online attack surface ({len(usernames)} registered public account(s)).")
        elif len(usernames) >= 2:
            score += 5.0
            factors.append(f"LOW: Multiple registered social accounts ({len(usernames)} account(s)).")

        final_score = min(100.0, round(score, 1))

        if final_score >= 75.0:
            severity = "CRITICAL"
        elif final_score >= 50.0:
            severity = "HIGH"
        elif final_score >= 25.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        return {
            "score": final_score,
            "severity": severity,
            "total_entities_evaluated": total_nodes,
            "risk_factors": factors,
        }


class ThematicClusteringEngine:
    """
    Lightweight N-gram Semantic Clustering Engine (inspired by carrot2).
    Groups investigation text snippets, account categories, and topics into natural thematic clusters.
    """

    STOPWORDS = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of", "from",
        "dan", "di", "ke", "dari", "yang", "ini", "itu", "untuk", "pada", "dengan", "adalah"
    }

    @classmethod
    def cluster_entities(cls, graph: KnowledgeGraph) -> List[Dict[str, Any]]:
        categories: Dict[str, List[str]] = {}

        for nid, node in graph.nodes.items():
            attrs = node.attributes or {}
            cat = attrs.get("category") or attrs.get("platform") or node.type.value
            cat_name = str(cat).capitalize()
            categories.setdefault(cat_name, []).append(nid)

        clusters = []
        for cat_name, nids in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            clusters.append({
                "theme": cat_name,
                "entity_count": len(nids),
                "node_ids": nids,
                "sample_labels": [graph.nodes[nid].label or nid for nid in nids[:5]],
            })

        return clusters


