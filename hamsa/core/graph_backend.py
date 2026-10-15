"""
Graph Storage Backend Abstraction & Neo4j Enterprise Adapter for Hamsa OSINT Framework.
Provides pluggable graph persistence: In-Memory (Zero-Dependency Default) and Neo4j (Graph Database with Cypher Support).
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple

from hamsa.core.models import EntityNode, RelationEdge, RelationType, TargetType
from hamsa.utils.formatters import log_info, log_warn


class BaseGraphBackend(ABC):
    """Abstract interface for intelligence graph persistence backends."""

    @abstractmethod
    def add_node(self, node: EntityNode) -> None:
        """Persist or merge an entity node into the graph."""
        pass

    @abstractmethod
    def add_edge(self, edge: RelationEdge) -> None:
        """Persist or merge a relation edge between two entities."""
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[EntityNode]:
        """Fetch an entity node by its unique ID."""
        pass

    @abstractmethod
    def get_nodes(self) -> Dict[str, EntityNode]:
        """Fetch all entity nodes as a dictionary mapping node_id -> EntityNode."""
        pass

    @abstractmethod
    def get_edges(self) -> List[RelationEdge]:
        """Fetch all relationship edges."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Erase all nodes and edges from storage."""
        pass

    @abstractmethod
    def execute_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a Cypher graph query (supported on Neo4j backend)."""
        pass

    @abstractmethod
    def find_shared_attributes(self, attribute_name: str) -> Dict[str, List[str]]:
        """Finds values of an attribute shared by two or more distinct entities."""
        pass


class MemoryGraphBackend(BaseGraphBackend):
    """Fast, lightweight in-memory graph backend requiring zero external dependencies."""

    def __init__(self) -> None:
        self._nodes: Dict[str, EntityNode] = {}
        self._edges: List[RelationEdge] = []
        self._edge_keys: Set[Tuple[str, str, str]] = set()

    def add_node(self, node: EntityNode) -> None:
        if node.id in self._nodes:
            existing = self._nodes[node.id]
            existing.attributes.update(node.attributes)
            existing.confidence = max(existing.confidence, node.confidence)
        else:
            self._nodes[node.id] = node

    def add_edge(self, edge: RelationEdge) -> None:
        r_type = edge.relation_type.value if isinstance(edge.relation_type, RelationType) else str(edge.relation_type)
        key = (edge.source_id, edge.target_id, r_type)
        if key not in self._edge_keys:
            self._edge_keys.add(key)
            self._edges.append(edge)

    def get_node(self, node_id: str) -> Optional[EntityNode]:
        return self._nodes.get(node_id)

    def get_nodes(self) -> Dict[str, EntityNode]:
        return self._nodes

    def get_edges(self) -> List[RelationEdge]:
        return self._edges

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._edge_keys.clear()

    def execute_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """In-memory emulation for basic entity lookups when Cypher is requested."""
        # Simple read emulation for node filtering
        query_lower = query.lower()
        if "match (n)" in query_lower or "match (n:entity)" in query_lower:
            return [{"node": n.to_dict()} for n in self._nodes.values()]
        return []

    def find_shared_attributes(self, attribute_name: str) -> Dict[str, List[str]]:
        """Maps attribute values to entity IDs that share that attribute."""
        value_to_nodes: Dict[str, List[str]] = {}
        for node in self._nodes.values():
            val = node.attributes.get(attribute_name)
            if val is not None:
                val_str = str(val).strip()
                if val_str:
                    value_to_nodes.setdefault(val_str, []).append(node.id)

        # Filter only values shared by 2 or more entities
        return {val: nodes for val, nodes in value_to_nodes.items() if len(nodes) > 1}


class Neo4jGraphBackend(BaseGraphBackend):
    """
    Enterprise-grade Neo4j graph database adapter for large-scale OSINT correlation.
    Supports Cypher graph pattern matching, multi-hop pivots, and persistent cluster storage.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")

        # Local cache for sub-millisecond retrieval and offline fallback
        self._mem = MemoryGraphBackend()
        self._driver: Any = None
        self._connected: bool = False

        self._initialize_driver()

    def _initialize_driver(self) -> None:
        try:
            import neo4j  # type: ignore

            self._driver = neo4j.GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            self._connected = True
            log_info(f"Neo4j Graph Backend connected successfully to {self.uri}")
        except ImportError:
            log_warn("Neo4j driver package is not installed ('pip install neo4j'). Running in local memory cache mode.")
            self._connected = False
        except Exception as e:
            log_warn(f"Unable to connect to Neo4j at {self.uri}: {e}. Falling back to in-memory cache.")
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def add_node(self, node: EntityNode) -> None:
        # Update local memory
        self._mem.add_node(node)

        if not self._connected or not self._driver:
            return

        try:
            n_type = node.type.value if isinstance(node.type, TargetType) else str(node.type)
            safe_attrs = {
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in node.attributes.items()
            }
            cypher = """
            MERGE (n:Entity {id: $id})
            SET n.label = $label,
                n.value = $value,
                n.type = $type,
                n.confidence = $confidence,
                n.source_plugin = $source_plugin,
                n += $attributes
            """
            with self._driver.session() as session:
                session.run(
                    cypher,
                    id=node.id,
                    label=node.label,
                    value=node.value,
                    type=n_type,
                    confidence=node.confidence,
                    source_plugin=node.source_plugin,
                    attributes=safe_attrs,
                )
        except Exception as e:
            log_warn(f"Neo4j add_node error for {node.id}: {e}")

    def add_edge(self, edge: RelationEdge) -> None:
        # Update local memory
        self._mem.add_edge(edge)

        if not self._connected or not self._driver:
            return

        try:
            r_type = edge.relation_type.value if isinstance(edge.relation_type, RelationType) else str(edge.relation_type)
            cypher = """
            MATCH (a:Entity {id: $src}), (b:Entity {id: $dst})
            MERGE (a)-[r:CORRELATED {rel_type: $rel_type, label: $label, weight: $weight}]->(b)
            """
            with self._driver.session() as session:
                session.run(
                    cypher,
                    src=edge.source_id,
                    dst=edge.target_id,
                    rel_type=r_type,
                    label=edge.label,
                    weight=edge.weight,
                )
        except Exception as e:
            log_warn(f"Neo4j add_edge error ({edge.source_id} -> {edge.target_id}): {e}")

    def get_node(self, node_id: str) -> Optional[EntityNode]:
        return self._mem.get_node(node_id)

    def get_nodes(self) -> Dict[str, EntityNode]:
        return self._mem.get_nodes()

    def get_edges(self) -> List[RelationEdge]:
        return self._mem.get_edges()

    def clear(self) -> None:
        self._mem.clear()
        if self._connected and self._driver:
            try:
                with self._driver.session() as session:
                    session.run("MATCH (n:Entity) DETACH DELETE n")
            except Exception as e:
                log_warn(f"Neo4j clear error: {e}")

    def execute_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a custom Cypher query against the connected Neo4j cluster."""
        if not self._connected or not self._driver:
            return self._mem.execute_cypher(query, params)

        try:
            with self._driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            log_warn(f"Cypher execution failed: {e}")
            return []

    def find_shared_attributes(self, attribute_name: str) -> Dict[str, List[str]]:
        if self._connected and self._driver:
            try:
                query = f"""
                MATCH (n:Entity)
                WHERE n.{attribute_name} IS NOT NULL
                WITH n.{attribute_name} AS attr_val, collect(n.id) AS node_ids
                WHERE size(node_ids) > 1
                RETURN attr_val, node_ids
                """
                with self._driver.session() as session:
                    res = session.run(query)
                    return {record["attr_val"]: record["node_ids"] for record in res}
            except Exception:
                pass
        return self._mem.find_shared_attributes(attribute_name)

    def close(self) -> None:
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass


def create_graph_backend(backend_type: Optional[str] = None, **kwargs: Any) -> BaseGraphBackend:
    """Factory creating the appropriate graph storage backend."""
    b_type = (backend_type or os.getenv("HAMSA_GRAPH_BACKEND", "memory")).lower().strip()
    if b_type == "neo4j":
        return Neo4jGraphBackend(**kwargs)
    return MemoryGraphBackend()
