"""
Multi-Case Project Management & Investigation Dossier Engine for Hamsa OSINT Framework.
Provides case workspace isolation, investigator annotations, evidence tracking, and audit history.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CaseEvidence:
    """Represents a captured piece of digital forensic evidence."""
    id: str
    url: str
    title: str
    captured_at: str
    evidence_type: str  # "screenshot", "html_snapshot", "metadata", "note"
    filepath: Optional[str] = None
    sha256: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Case:
    """Represents an isolated investigative case workspace."""
    id: str
    title: str
    description: str = ""
    status: str = "active"  # "active", "archived", "closed"
    created_at: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    targets: List[Dict[str, str]] = field(default_factory=list)
    node_annotations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    graph_data: Dict[str, Any] = field(default_factory=lambda: {"nodes": [], "edges": [], "summary": {"total_entities": 0, "total_relations": 0}})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Case:
        return cls(
            id=data["id"],
            title=data.get("title", "Untitled Case"),
            description=data.get("description", ""),
            status=data.get("status", "active"),
            created_at=data.get("created_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")),
            updated_at=data.get("updated_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
            targets=data.get("targets", []),
            node_annotations=data.get("node_annotations", {}),
            evidence=data.get("evidence", []),
            graph_data=data.get("graph_data", {"nodes": [], "edges": [], "summary": {"total_entities": 0, "total_relations": 0}}),
        )


class CaseManager:
    """Manages creation, switching, persistence, and audit logging of multiple investigation cases."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = os.path.expanduser("~/.hamsa/cases")
        os.makedirs(self.base_dir, exist_ok=True)
        self._ensure_default_case()

    def _ensure_default_case(self) -> None:
        """Ensures at least one default case exists for fresh installations."""
        default_file = os.path.join(self.base_dir, "case_default.json")
        if not os.path.exists(default_file):
            default_case = Case(
                id="case_default",
                title="Primary Investigation Dossier",
                description="Default case workspace for initial reconnaissance and entity correlation.",
                tags=["General", "Active"],
            )
            self.save_case(default_case)

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^\w\s-]", "", text).strip().lower()
        return re.sub(r"[-\s]+", "_", s)

    def create_case(
        self,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        case_id: Optional[str] = None,
    ) -> Case:
        """Creates a new isolated investigation case."""
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = self._slugify(title)[:24] if title else "case"
        cid = case_id or f"case_{slug}_{now_str}"

        case = Case(
            id=cid,
            title=title,
            description=description,
            tags=tags or ["Active"],
        )
        self.save_case(case)
        return case

    def save_case(self, case: Case) -> None:
        """Persists case state to disk."""
        case.updated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        filepath = os.path.join(self.base_dir, f"{case.id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(case.to_dict(), f, indent=2, ensure_ascii=False)

    def get_case(self, case_id: str) -> Optional[Case]:
        """Loads a case by its ID."""
        filepath = os.path.join(self.base_dir, f"{case_id}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Case.from_dict(data)
        except Exception:
            return None

    def list_cases(self) -> List[Dict[str, Any]]:
        """Returns summaries of all available cases."""
        cases = []
        for filename in sorted(os.listdir(self.base_dir)):
            if filename.endswith(".json"):
                filepath = os.path.join(self.base_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        summary = data.get("graph_data", {}).get("summary", {})
                        cases.append({
                            "id": data["id"],
                            "title": data.get("title", "Untitled"),
                            "description": data.get("description", ""),
                            "status": data.get("status", "active"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "tags": data.get("tags", []),
                            "targets_count": len(data.get("targets", [])),
                            "entities_count": summary.get("total_entities", len(data.get("graph_data", {}).get("nodes", []))),
                            "relations_count": summary.get("total_relations", len(data.get("graph_data", {}).get("edges", []))),
                            "evidence_count": len(data.get("evidence", [])),
                        })
                except Exception:
                    continue
        return sorted(cases, key=lambda c: c.get("updated_at", ""), reverse=True)

    def update_case(
        self,
        case_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Case]:
        """Updates metadata and notes of an existing case."""
        case = self.get_case(case_id)
        if not case:
            return None
        if title is not None:
            case.title = title
        if description is not None:
            case.description = description
        if status is not None:
            case.status = status
        if notes is not None:
            case.notes = notes
        if tags is not None:
            case.tags = tags
        self.save_case(case)
        return case

    def annotate_node(
        self,
        case_id: str,
        node_id: str,
        tag: Optional[str] = None,
        color: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Applies manual investigator markings to a node in the case graph."""
        case = self.get_case(case_id)
        if not case:
            return False

        annotation = case.node_annotations.get(node_id, {})
        if tag is not None:
            annotation["tag"] = tag
        if color is not None:
            annotation["color"] = color
        if notes is not None:
            annotation["notes"] = notes
        annotation["annotated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        case.node_annotations[node_id] = annotation

        # Also update node attributes in graph_data if present
        for node in case.graph_data.get("nodes", []):
            if node.get("id") == node_id:
                node.setdefault("attributes", {})
                if tag:
                    node["attributes"]["investigator_tag"] = tag
                if color:
                    node["attributes"]["custom_color"] = color
                if notes:
                    node["attributes"]["investigator_notes"] = notes

        self.save_case(case)
        return True

    def add_evidence(
        self,
        case_id: str,
        url: str,
        title: str,
        evidence_type: str = "web_snapshot",
        filepath: Optional[str] = None,
        notes: str = "",
    ) -> Optional[CaseEvidence]:
        """Attaches captured forensic evidence to a case."""
        case = self.get_case(case_id)
        if not case:
            return None

        eid = f"ev_{int(datetime.datetime.now().timestamp() * 1000)}"
        evidence = CaseEvidence(
            id=eid,
            url=url,
            title=title,
            captured_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            evidence_type=evidence_type,
            filepath=filepath,
            notes=notes,
        )
        case.evidence.append(evidence.to_dict())
        self.save_case(case)
        return evidence

    def delete_case(self, case_id: str) -> bool:
        """Deletes a case workspace from disk (cannot delete default)."""
        if case_id == "case_default":
            return False
        filepath = os.path.join(self.base_dir, f"{case_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
