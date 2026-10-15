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

