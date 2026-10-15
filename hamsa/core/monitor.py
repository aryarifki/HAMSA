"""
Continuous Exposure Monitoring, Attack Surface Drift & Webhook Alerting for Hamsa.
Tracks targets on a continuous watchlist, calculates cross-scan graph diffs, and dispatches
threat intelligence alerts to Slack, Discord, and Telegram.
"""

from __future__ import annotations

import datetime
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from hamsa.core.graph import KnowledgeGraph
from hamsa.core.models import TargetType
from hamsa.utils.formatters import log_error, log_info, log_success, log_warn


@dataclass
class WatchlistTarget:
    """Represents an investigative target subject under continuous surveillance."""
    value: str
    target_type: str
    added_at: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    last_scanned: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WatchlistTarget:
        return cls(
            value=data["value"],
            target_type=data.get("target_type", "username"),
            added_at=data.get("added_at", ""),
            last_scanned=data.get("last_scanned"),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
        )


class WatchlistManager:
    """Manages persistent surveillance watchlists stored on disk."""

    def __init__(self, filepath: Optional[str] = None) -> None:
        if filepath:
            self.filepath = filepath
        else:
            base_dir = os.path.expanduser("~/.hamsa")
            os.makedirs(base_dir, exist_ok=True)
            self.filepath = os.path.join(base_dir, "watchlist.json")

        self.targets: Dict[str, WatchlistTarget] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.filepath) or os.path.getsize(self.filepath) == 0:
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("targets", []):
                    target = WatchlistTarget.from_dict(item)
                    self.targets[f"{target.target_type}:{target.value}"] = target
        except Exception as e:
            log_warn(f"Failed to read watchlist file: {e}")

    def save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        try:
            payload = {
                "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "total_targets": len(self.targets),
                "targets": [t.to_dict() for t in self.targets.values()],
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to write watchlist file: {e}")

    def add(self, value: str, target_type: str = "username", tags: Optional[List[str]] = None, notes: str = "") -> WatchlistTarget:
        key = f"{target_type.lower()}:{value.strip()}"
        target = WatchlistTarget(
            value=value.strip(),
            target_type=target_type.lower(),
            tags=tags or [],
            notes=notes,
        )
        self.targets[key] = target
        self.save()
        return target

    def remove(self, value: str, target_type: str = "username") -> bool:
        key = f"{target_type.lower()}:{value.strip()}"
        if key in self.targets:
            del self.targets[key]
            self.save()
            return True
        return False

    def list_all(self) -> List[WatchlistTarget]:
        return list(self.targets.values())

    def update_scanned(self, value: str, target_type: str) -> None:
        key = f"{target_type.lower()}:{value.strip()}"
        if key in self.targets:
            self.targets[key].last_scanned = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            self.save()


class ScanDiffEngine:
    """
    Computes cross-scan perimeter drift and security exposure changes between intelligence graph snapshots.
    Identifies new entities, resolved/removed entities, attribute changes, and critical new breach incidents.
    """

    @staticmethod
    def compute_diff(old_graph_dict: Dict[str, Any], new_graph_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates changes between two knowledge graph snapshots."""
        old_nodes = {n["id"]: n for n in old_graph_dict.get("nodes", [])}
        new_nodes = {n["id"]: n for n in new_graph_dict.get("nodes", [])}

        old_edges = {(e["source"], e["target"], e.get("type", "related")) for e in old_graph_dict.get("edges", [])}
        new_edges = {(e["source"], e["target"], e.get("type", "related")) for e in new_graph_dict.get("edges", [])}

        # 1. Added Nodes
        added_node_ids = set(new_nodes.keys()) - set(old_nodes.keys())
        added_nodes = [new_nodes[nid] for nid in added_node_ids]

        # 2. Removed Nodes
        removed_node_ids = set(old_nodes.keys()) - set(new_nodes.keys())
        removed_nodes = [old_nodes[nid] for nid in removed_node_ids]

        # 3. Modified Nodes (Attribute changes)
        modified_nodes = []
        for nid in set(old_nodes.keys()) & set(new_nodes.keys()):
            old_attr = old_nodes[nid].get("attributes", {})
            new_attr = new_nodes[nid].get("attributes", {})
            if old_attr != new_attr:
                modified_nodes.append({
                    "id": nid,
                    "label": new_nodes[nid].get("label"),
                    "type": new_nodes[nid].get("type"),
                    "old_attributes": old_attr,
                    "new_attributes": new_attr,
                })

        # 4. Added Edges
        added_edges = list(new_edges - old_edges)

        # 5. High-Severity Critical Findings (New Breaches or Malware Logs)
        new_breaches = [
            n for n in added_nodes
            if n.get("type") in (TargetType.BREACH.value, "breach") or "infected_path" in n.get("attributes", {})
        ]

        # 6. Drift Score (0 - 100)
        # Breaches contribute 30 pts each, accounts 10 pts, general nodes 2 pts
        raw_score = (len(new_breaches) * 30) + (len(added_nodes) * 4) + (len(modified_nodes) * 2)
        drift_score = min(100, raw_score)

        has_drift = bool(added_nodes or removed_nodes or modified_nodes or added_edges)

        return {
            "has_drift": has_drift,
            "drift_score": drift_score,
            "total_added_nodes": len(added_nodes),
            "total_removed_nodes": len(removed_nodes),
            "total_modified_nodes": len(modified_nodes),
            "total_new_edges": len(added_edges),
            "new_breaches": new_breaches,
            "added_nodes": added_nodes,
            "removed_nodes": removed_nodes,
            "modified_nodes": modified_nodes,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    @staticmethod
    def format_alert_markdown(target_name: str, diff: Dict[str, Any]) -> str:
        """Formats the scan drift report into a clean markdown message for notification webhooks."""
        lines = [
            f"🚨 **HAMSA PROACTIVE INTELLIGENCE ALERT** 🚨",
            f"**Subject:** `{target_name}`",
            f"**Timestamp:** {diff['timestamp']}",
            f"**Perimeter Drift Score:** {diff['drift_score']}/100",
            f"",
            f"**Delta Summary:**",
            f"• New Entities Discovered: **+{diff['total_added_nodes']}**",
            f"• Entities Removed/Resolved: **-{diff['total_removed_nodes']}**",
            f"• Attribute Drift Detected: **{diff['total_modified_nodes']}** entities",
            f"• New Relational Links: **+{diff['total_new_edges']}**",
        ]

        if diff["new_breaches"]:
            lines.append("\n⚠️ **CRITICAL NEW SECURITY EXPOSURE(S) DETECTED:**")
            for b in diff["new_breaches"][:5]:
                label = b.get("label", "Unknown Breach")
                attrs = b.get("attributes", {})
                date = attrs.get("breached_date", attrs.get("date", "Unknown Date"))
                lines.append(f"  - **{label}** (Date: {date})")

        return "\n".join(lines)


class WebhookDispatcher:
    """Dispatches threat alerts to external security chat channels (Discord, Slack, Telegram)."""

    @staticmethod
    def send(webhook_url: str, title: str, text: str, diff_score: int = 0) -> bool:
        """Auto-detects webhook endpoint type (Telegram, Discord, Slack) and posts notification."""
        if not webhook_url:
            return False

        try:
            # 1. Telegram Bot API: https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>
            if "api.telegram.org" in webhook_url:
                payload = json.dumps({
                    "text": f"*{title}*\n\n{text}",
                    "parse_mode": "Markdown",
                }).encode("utf-8")
                req = urllib.request.Request(
                    webhook_url,
                    data=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "Hamsa-OSINT-Alert/1.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.status in (200, 201)

            # 2. Discord Webhook: https://discord.com/api/webhooks/...
            if "discord.com" in webhook_url or "discordapp.com" in webhook_url:
                embed_color = 0xEF4444 if diff_score >= 30 else 0x38BDF8
                payload = json.dumps({
                    "username": "Hamsa OSINT Sentinel",
                    "embeds": [{
                        "title": title,
                        "description": text,
                        "color": embed_color,
                        "footer": {"text": "Autonomous Threat Reconnaissance"},
                    }],
                }).encode("utf-8")
                req = urllib.request.Request(
                    webhook_url,
                    data=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "Hamsa-OSINT-Alert/1.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.status in (200, 204)

            # 3. Slack Webhook: https://hooks.slack.com/services/...
            slack_color = "#ef4444" if diff_score >= 30 else "#38bdf8"
            payload = json.dumps({
                "attachments": [{
                    "fallback": title,
                    "color": slack_color,
                    "title": title,
                    "text": text,
                    "footer": "HAMSA OSINT Intelligence Framework",
                    "ts": int(datetime.datetime.now().timestamp()),
                }],
            }).encode("utf-8")

            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "Hamsa-OSINT-Alert/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204)

        except Exception as e:
            log_error(f"Webhook dispatch failed to {webhook_url}: {e}")
            return False
