"""
HAMSA Graph Intelligence Analytics Engine
Algorithms for Shortest Path Correlation (Dijkstra/BFS), Entity Centrality Scoring,
Bridge/Brokerage Detection, and Cluster Decomposition.
Pure Python Standard Library implementation.
"""

from collections import deque
from typing import Dict, List, Any, Optional, Set, Tuple

from hamsa.core.graph import KnowledgeGraph
from hamsa.core.models import EntityNode, RelationEdge


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
