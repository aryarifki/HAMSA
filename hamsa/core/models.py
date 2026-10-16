"""
Core data models for Hamsa OSINT Framework.
Defines entity nodes, relations, scan context, and plugin outputs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class TargetType(str, Enum):
    USERNAME = "username"
    EMAIL = "email"
    PHONE = "phone"
    IMAGE = "image"
    DOMAIN = "domain"
    IP = "ip"
    ORGANIZATION = "organization"
    BREACH = "breach"
    LOCATION = "location"
    DEVICE = "device"
    VULNERABILITY = "vulnerability"
    GENERIC = "generic"


class RelationType(str, Enum):
    REGISTERED_ON = "REGISTERED_ON"
    EXPOSED_IN = "EXPOSED_IN"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    LOCATED_AT = "LOCATED_AT"
    CAPTURED_BY = "CAPTURED_BY"
    OPERATED_BY = "OPERATED_BY"
    MENTIONED_IN = "MENTIONED_IN"
    DERIVED_FROM = "DERIVED_FROM"
    FOLLOWS = "FOLLOWS"
    COLLEAGUE_OF = "COLLEAGUE_OF"
    ENDORSES = "ENDORSES"
    INTERACTED_WITH = "INTERACTED_WITH"
    RESOLVES_TO = "RESOLVES_TO"
    AFFECTED_BY = "AFFECTED_BY"


@dataclass
class EntityNode:
    """Represents an entity node in the intelligence knowledge graph."""
    id: str  # Unique identifier, e.g. "email:target@example.com" or "platform:github:johndoe"
    type: TargetType
    value: str
    label: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    source_plugin: str = "core"
    confidence: float = 1.0  # 0.0 to 1.0
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, TargetType) else self.type,
            "value": self.value,
            "label": self.label,
            "attributes": self.attributes,
            "source_plugin": self.source_plugin,
            "confidence": self.confidence,
            "discovered_at": self.discovered_at,
        }


@dataclass
class RelationEdge:
    """Represents a relationship edge between two entities in the knowledge graph."""
    source_id: str
    target_id: str
    relation_type: RelationType
    label: str = ""
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relation_type.value if isinstance(self.relation_type, RelationType) else self.relation_type,
            "label": self.label or (self.relation_type.value if isinstance(self.relation_type, RelationType) else self.relation_type),
            "weight": self.weight,
            "metadata": self.metadata,
        }


@dataclass
class PluginMetadata:
    """Metadata describing a plugin's identity, author, and capabilities."""
    name: str
    version: str
    author: str
    description: str
    target_types: List[TargetType]
    requires_network: bool = True
    requires_api_key: bool = False
    rate_limit_delay: float = 0.3


@dataclass
class PluginResult:
    """Aggregated output returned by a plugin during execution."""
    plugin_name: str
    success: bool
    nodes: List[EntityNode] = field(default_factory=list)
    edges: List[RelationEdge] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    candidate_targets: List[tuple[str, TargetType, str]] = field(default_factory=list)  # (target_value, target_type, parent_node_id)
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
