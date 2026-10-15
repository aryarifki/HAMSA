"""
Base plugin interface and abstract class for Hamsa OSINT plugins.
"""

from abc import ABC, abstractmethod
import time
from typing import Any, Dict, List, Optional
from hamsa.core.models import (
    EntityNode,
    PluginMetadata,
    PluginResult,
    RelationEdge,
    RelationType,
    TargetType,
)


class BasePlugin(ABC):
    """Abstract base class that all Hamsa plugins must inherit from."""

    metadata: PluginMetadata

    def __init__(self) -> None:
        if not hasattr(self, "metadata") or not isinstance(self.metadata, PluginMetadata):
            raise NotImplementedError("Plugins must declare a valid 'metadata' attribute of type PluginMetadata.")

    def can_handle(self, target: str, target_type: TargetType) -> bool:
        """Determines if the plugin can handle the given target and target type."""
        return target_type in self.metadata.target_types

    @abstractmethod
    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        """
        Executes the plugin analysis asynchronously.
        Must return a PluginResult containing discovered nodes, edges, and logs.
        """
        pass

    def create_node(
        self,
        node_id: str,
        node_type: TargetType,
        value: str,
        label: str,
        attributes: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
    ) -> EntityNode:
        """Helper to create an EntityNode with this plugin's name as source."""
        return EntityNode(
            id=node_id,
            type=node_type,
            value=value,
            label=label,
            attributes=attributes or {},
            source_plugin=self.metadata.name,
            confidence=confidence,
        )

    def create_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        label: str = "",
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RelationEdge:
        """Helper to create a RelationEdge between two nodes."""
        return RelationEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            label=label or relation_type.value,
            weight=weight,
            metadata=metadata or {},
        )
