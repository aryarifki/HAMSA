"""
Autonomous Agent Decision & Heuristic Planning Brain for Hamsa OSINT Framework.
Analyzes the evolving intelligence graph between rounds to prioritize high-value targets,
prune low-confidence leads, and optimize recursive exploration.
"""

from typing import Any, Dict, List, Set, Tuple
from hamsa.core.graph import KnowledgeGraph
from hamsa.core.models import EntityNode, RelationEdge, TargetType


class AgentBrain:
    """
    Cognitive evaluation engine that guides the autonomous investigation flow.
    Applies graph heuristics and correlation rules to plan subsequent scanning rounds.
    """

    def __init__(self, max_depth: int = 2) -> None:
        self.max_depth = max_depth

    def evaluate_and_plan(
        self,
        graph: KnowledgeGraph,
        current_depth: int,
        raw_candidates: List[Tuple[str, TargetType, str]],
        visited_keys: Set[Tuple[str, TargetType]],
    ) -> Dict[str, Any]:
        """
        Evaluates current graph state and selects prioritized candidates for the next round.
        """
        plan = {
            "continue_investigation": True,
            "reason": "",
            "prioritized_targets": [],
            "graph_insights": [],
        }

        # Check depth boundary
        if current_depth >= self.max_depth:
            plan["continue_investigation"] = False
            plan["reason"] = f"Target depth boundary ({self.max_depth}) reached. Consolidating knowledge graph."
            return plan

        summary = graph.to_dict()
        nodes = summary["nodes"]
        total_nodes = len(nodes)

        # Graph Insight: Correlated Identity Check
        has_real_name = any(n.get("attributes", {}).get("real_name") for n in nodes)
        has_breach = any(n["type"] == TargetType.BREACH.value for n in nodes)
        has_phone = any(n["type"] == TargetType.PHONE.value for n in nodes)

        if has_real_name and has_breach:
            plan["graph_insights"].append("High-Value Pivot: Target has correlated real name and recorded breach exposures.")

        if has_phone:
            plan["graph_insights"].append("Telecommunication Pivot: Target has verified phone network footprint.")

        # Candidate Evaluation & Deduplication
        valid_candidates = []
        seen = set()

        # Blacklisted generic tokens to prune false leads
        garbage_tokens = {
            "unknown", "null", "none", "admin", "contact", "support", "sales",
            "info", "help", "user", "profile", "test", "demo", "mail"
        }

        for val, t_type, parent_id in raw_candidates:
            clean_val = val.strip().lower()
            key = (clean_val, t_type)

            if key in visited_keys or clean_val in seen:
                continue

            if clean_val in garbage_tokens or len(clean_val) < 3:
                continue

            # Prioritize candidates based on entity type and context
            priority_score = 1.0
            if t_type == TargetType.GENERIC:  # Real Name
                priority_score += 1.5
            elif t_type == TargetType.EMAIL:
                priority_score += 2.0
            elif t_type == TargetType.USERNAME:
                priority_score += 1.2

            seen.add(clean_val)
            valid_candidates.append({
                "value": val.strip(),
                "type": t_type,
                "parent_id": parent_id,
                "priority": priority_score,
            })

        # Sort candidates descending by priority score
        valid_candidates.sort(key=lambda x: x["priority"], reverse=True)

        # Select top candidates (cap at 5 per round to prevent explosion)
        selected = valid_candidates[:5]

        if not selected:
            plan["continue_investigation"] = False
            plan["reason"] = "No new high-value candidates discovered. Finalizing graph."
            return plan

        plan["prioritized_targets"] = [
            (c["value"], c["type"], c["parent_id"]) for c in selected
        ]
        plan["reason"] = f"Autonomous Brain selected {len(selected)} prioritized target(s) for Round {current_depth + 1}."
        return plan
