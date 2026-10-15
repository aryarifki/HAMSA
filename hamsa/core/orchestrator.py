"""
Core Orchestrator for Hamsa OSINT Framework.
Manages plugin registration, task dispatching, concurrency, and recursive cross-entity correlation.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from hamsa.core.graph import KnowledgeGraph
from hamsa.core.models import (
    PluginResult,
    RelationEdge,
    RelationType,
    TargetType,
)
from hamsa.core.agent_brain import AgentBrain
from hamsa.plugins.base import BasePlugin
from hamsa.plugins.email.hudsonrock_infostealer import HudsonRockInfostealerPlugin
from hamsa.plugins.email.xposedornot_breach import XposedOrNotBreachPlugin
from hamsa.plugins.exif.photo_metadata import ExifMetadataPlugin
from hamsa.plugins.phone.contact_tags import ContactTagResolverPlugin
from hamsa.plugins.phone.phone_infoga import PhoneInfogaDorksPlugin
from hamsa.plugins.phone.phone_parser import PhoneParserPlugin
from hamsa.plugins.phone.phone_presence import PhonePresencePlugin
from hamsa.plugins.username.fast_checker import FastUsernameCheckerPlugin
from hamsa.plugins.username.name_resolver import NameResolverPlugin
from hamsa.utils.formatters import log_debug, log_error, log_info, log_success


class Orchestrator:
    """Orchestrates multi-target OSINT investigations with multi-round recursive profiling."""

    def __init__(self) -> None:
        self.plugins: List[BasePlugin] = []
        self.graph = KnowledgeGraph()
        self._register_default_plugins()

    def _register_default_plugins(self) -> None:
        """Loads default built-in core plugins."""
        self.register_plugin(FastUsernameCheckerPlugin())
        self.register_plugin(XposedOrNotBreachPlugin())
        self.register_plugin(HudsonRockInfostealerPlugin())
        self.register_plugin(PhoneParserPlugin())
        self.register_plugin(PhonePresencePlugin())
        self.register_plugin(ContactTagResolverPlugin())
        self.register_plugin(PhoneInfogaDorksPlugin())
        self.register_plugin(ExifMetadataPlugin())
        self.register_plugin(NameResolverPlugin())

    def register_plugin(self, plugin: BasePlugin) -> None:
        """Register a new plugin instance into the pool."""
        self.plugins.append(plugin)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p.metadata.name,
                "version": p.metadata.version,
                "author": p.metadata.author,
                "description": p.metadata.description,
                "target_types": [t.value for t in p.metadata.target_types],
            }
            for p in self.plugins
        ]

    async def _execute_plugin_safe(
        self,
        plugin: BasePlugin,
        target: str,
        target_type: TargetType,
        context: Dict[str, Any],
    ) -> PluginResult:
        try:
            log_debug(f"[{plugin.metadata.name}] Executing on target '{target}' ({target_type.value})...")
            result = await plugin.run(target, target_type, context)
            for log_msg in result.logs:
                log_info(f"[{plugin.metadata.name}] {log_msg}")
            return result
        except Exception as e:
            log_error(f"[{plugin.metadata.name}] Plugin error: {e}")
            return PluginResult(
                plugin_name=plugin.metadata.name,
                success=False,
                error=str(e),
            )

    async def scan(
        self,
        initial_targets: List[Tuple[str, TargetType]],
        context: Optional[Dict[str, Any]] = None,
        max_depth: int = 2,
        recursive: bool = True,
        on_event: Optional[Callable[[str, Any], None]] = None,
    ) -> KnowledgeGraph:
        """
        Executes concurrent intelligence gathering across targets.
        If recursive=True and max_depth > 1, automatically launches round 2 scans
        on newly discovered identities, real names, and handles.
        Streams real-time events via on_event callback if provided.
        """
        context = context or {}
        visited_targets: Set[Tuple[str, TargetType]] = set()
        current_targets: List[Tuple[str, TargetType, Optional[str]]] = [
            (t, typ, None) for t, typ in initial_targets
        ]

        current_depth = 1
        while current_targets and current_depth <= max_depth:
            round_label = f"Round {current_depth}" if current_depth > 1 else "Initial Round"
            log_info(f"--- Starting {round_label} ({len(current_targets)} targets in queue) ---")
            if on_event:
                on_event("round_started", {"depth": current_depth, "queue_size": len(current_targets), "label": round_label})

            tasks = []
            target_parent_map: Dict[Tuple[str, TargetType], Optional[str]] = {}

            for target, target_type, parent_id in current_targets:
                key = (target.strip().lower(), target_type)
                if key in visited_targets:
                    continue
                visited_targets.add(key)
                target_parent_map[(target, target_type)] = parent_id

                matching_plugins = [
                    p for p in self.plugins if p.can_handle(target, target_type)
                ]
                for plugin in matching_plugins:
                    tasks.append(
                        (self._execute_plugin_safe(plugin, target, target_type, context), (target, target_type))
                    )

            if not tasks:
                break

            # Execute tasks for this round
            task_futures = [t[0] for t in tasks]
            results: List[PluginResult] = await asyncio.gather(*task_futures)

            next_candidates: List[Tuple[str, TargetType, str]] = []

            for (res, (tgt, t_type)) in zip(results, [t[1] for t in tasks]):
                if res.success:
                    for node in res.nodes:
                        self.graph.add_node(node)
                        if on_event:
                            on_event("node_added", node.to_dict())
                    for edge in res.edges:
                        self.graph.add_edge(edge)
                        if on_event:
                            on_event("edge_added", edge.to_dict())

                    # Link newly spawned target to its discoverer/parent entity
                    parent_id = target_parent_map.get((tgt, t_type))
                    if parent_id:
                        derived_edge = RelationEdge(
                            source_id=parent_id,
                            target_id=f"{t_type.value}:{tgt.strip().lower()}",
                            relation_type=RelationType.DERIVED_FROM,
                            label="Discovered From Profile",
                        )
                        self.graph.add_edge(derived_edge)
                        if on_event:
                            on_event("edge_added", derived_edge.to_dict())

                    # Gather candidates for next round
                    if recursive and res.candidate_targets:
                        for cand_val, cand_type, p_id in res.candidate_targets:
                            cand_key = (cand_val.strip().lower(), cand_type)
                            if cand_key not in visited_targets:
                                next_candidates.append((cand_val, cand_type, p_id))

            # Cross-correlate root targets if initial round
            if current_depth == 1 and len(initial_targets) > 1:
                for i in range(len(initial_targets)):
                    for j in range(i + 1, len(initial_targets)):
                        t1, typ1 = initial_targets[i]
                        t2, typ2 = initial_targets[j]
                        id1 = f"{typ1.value}:{t1.strip().lower()}"
                        id2 = f"{typ2.value}:{t2.strip().lower()}"
                        co_edge = RelationEdge(
                            source_id=id1,
                            target_id=id2,
                            relation_type=RelationType.ASSOCIATED_WITH,
                            label="Co-investigated Target",
                        )
                        self.graph.add_edge(co_edge)
                        if on_event:
                            on_event("edge_added", co_edge.to_dict())

            # Cognitive evaluation & autonomous recursive planning via AgentBrain
            if recursive and current_depth < max_depth and next_candidates:
                brain = AgentBrain(max_depth=max_depth)
                plan = brain.evaluate_and_plan(
                    graph=self.graph,
                    current_depth=current_depth,
                    raw_candidates=next_candidates,
                    visited_keys=visited_targets,
                )
                for insight in plan.get("graph_insights", []):
                    log_info(f"[AgentBrain] {insight}")
                    if on_event:
                        on_event("agent_insight", {"insight": insight})

                if plan["continue_investigation"] and plan["prioritized_targets"]:
                    current_targets = plan["prioritized_targets"]
                    current_depth += 1
                    log_info(
                        f"[AgentBrain] {plan['reason']} "
                        f"Targets: {', '.join([f'{c[0]} ({c[1].value})' for c in current_targets])}"
                    )
                else:
                    if plan.get("reason"):
                        log_info(f"[AgentBrain] Investigation completed: {plan['reason']}")
                    break
            else:
                break

        if on_event:
            on_event("complete", self.graph.to_dict()["summary"])

        return self.graph
