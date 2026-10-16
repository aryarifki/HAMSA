"""
Fast Username Checker Plugin for Hamsa OSINT Framework.
Checks existence across major developer, social, and gaming platforms.
"""

import asyncio
from typing import Any, Dict, List, Optional
from hamsa.core.models import (
    EntityNode,
    PluginMetadata,
    PluginResult,
    RelationEdge,
    RelationType,
    TargetType,
)
from hamsa.plugins.base import BasePlugin
from hamsa.utils.http import HttpClient

# Curated platform probes with URL template and error heuristics
PLATFORMS = [
    {
        "name": "GitHub",
        "url": "https://github.com/{}",
        "category": "developer",
        "check_status": 200,
    },
    {
        "name": "GitLab",
        "url": "https://gitlab.com/{}",
        "category": "developer",
        "check_status": 200,
    },
    {
        "name": "Reddit",
        "url": "https://www.reddit.com/user/{}/about.json",
        "category": "social",
        "check_status": 200,
    },
    {
        "name": "HackerNews",
        "url": "https://hacker-news.firebaseio.com/v0/user/{}.json",
        "category": "developer",
        "check_status": 200,
    },
    {
        "name": "Dev.to",
        "url": "https://dev.to/{}",
        "category": "developer",
        "check_status": 200,
    },
    {
        "name": "Medium",
        "url": "https://medium.com/@{}",
        "category": "blog",
        "check_status": 200,
    },
    {
        "name": "DockerHub",
        "url": "https://hub.docker.com/v2/users/{}/",
        "category": "developer",
        "check_status": 200,
    },
    {
        "name": "Pinterest",
        "url": "https://www.pinterest.com/{}/",
        "category": "social",
        "check_status": 200,
    },
    {
        "name": "Telegram",
        "url": "https://t.me/{}",
        "category": "messenger",
        "check_status": 200,
        "error_marker": "If you have <strong>Telegram</strong>, you can contact",
    },
    {
        "name": "Steam",
        "url": "https://steamcommunity.com/id/{}",
        "category": "gaming",
        "check_status": 200,
        "error_marker": "The specified profile could not be found",
    },
]


class FastUsernameCheckerPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="fast_username_checker",
        version="0.1.0",
        author="Hamsa Team",
        description="Fast concurrent username availability and account discovery checker.",
        target_types=[TargetType.USERNAME],
        rate_limit_delay=0.15,
    )

    def __init__(self) -> None:
        super().__init__()
        self.http_client = HttpClient(timeout=8.0, default_delay=0.1)

    async def _is_soft_404_control(
        self,
        url_template: str,
        username: str,
        target_status: int,
        target_body: str,
    ) -> bool:
        """
        Baseline Control Probe (inspired by tookie-osint).
        Checks if the platform returns a dynamic soft-404 by probing an impossible random username.
        """
        control_user = "hamsa_probe_nonexist_99x"
        if "{account}" in url_template:
            control_url = url_template.replace("{account}", control_user)
        elif "{}" in url_template:
            control_url = url_template.replace("{}", control_user)
        else:
            control_url = f"{url_template.rstrip('/')}/{control_user}"

        try:
            c_status, c_body, _ = await self.http_client.request(control_url, method="GET", jitter=False)
            if c_status != target_status:
                return False
            c_text = c_body.decode("utf-8", errors="ignore")
            clean_target = len(target_body.replace(username, ""))
            clean_control = len(c_text.replace(control_user, ""))
            if not clean_target or not clean_control:
                return clean_target == clean_control
            return abs(clean_target - clean_control) / max(clean_target, clean_control) < 0.025
        except Exception:
            return False

    async def _check_platform(
        self,
        platform: Dict[str, Any],
        username: str,
        root_node_id: str,
    ) -> Optional[tuple[EntityNode, RelationEdge, List[tuple[str, TargetType, str]]]]:
        url_template = platform.get("url") or platform.get("uri_check", "")
        if "{account}" in url_template:
            url = url_template.replace("{account}", username)
        elif "{}" in url_template:
            url = url_template.replace("{}", username)
        else:
            url = f"{url_template.rstrip('/')}/{username}"

        candidates: List[tuple[str, TargetType, str]] = []
        try:
            status, body, _ = await self.http_client.request(url, method="GET", jitter=False)
            if status == platform.get("check_status", 200):
                body_text = body.decode("utf-8", errors="ignore")

                # Verify error marker if specified
                error_marker = platform.get("error_marker")
                if error_marker and error_marker in body_text:
                    return None

                # Verify valid marker if specified (WhatsMyName m_string)
                valid_marker = platform.get("valid_marker")
                if valid_marker and valid_marker not in body_text:
                    return None

                # Baseline Control False-Positive Eliminator (inspired by tookie-osint)
                if not error_marker and not valid_marker and platform.get("check_baseline", False):
                    if await self._is_soft_404_control(url_template, username, status, body_text):
                        return None

                node_id = f"account:{platform['name'].lower().replace(' ', '_')}:{username}"
                attributes = {
                    "platform": platform["name"],
                    "category": platform.get("category", "general"),
                    "profile_url": url,
                    "status_code": status,
                }

                # Deep profile extraction for GitHub
                if platform["name"] == "GitHub":
                    try:
                        api_status, api_data = await self.http_client.get_json(
                            f"https://api.github.com/users/{username}",
                            headers={"User-Agent": "HamsaOSINT/0.1.0"},
                        )
                        if api_status == 200 and isinstance(api_data, dict):
                            real_name = api_data.get("name")
                            if real_name:
                                attributes["real_name"] = real_name
                                candidates.append((real_name, TargetType.GENERIC, node_id))
                            if api_data.get("location"):
                                attributes["location"] = api_data["location"]
                            if api_data.get("company"):
                                attributes["company"] = api_data["company"]
                            if api_data.get("email"):
                                attributes["public_email"] = api_data["email"]
                                candidates.append((api_data["email"], TargetType.EMAIL, node_id))
                            if api_data.get("twitter_username"):
                                twitter_handle = api_data["twitter_username"]
                                attributes["twitter_username"] = twitter_handle
                                if twitter_handle.lower() != username.lower():
                                    candidates.append((twitter_handle, TargetType.USERNAME, node_id))
                    except Exception:
                        pass

                node = self.create_node(
                    node_id=node_id,
                    node_type=TargetType.GENERIC,
                    value=url,
                    label=f"{platform['name']}: @{username}",
                    attributes=attributes,
                    confidence=0.9,
                )
                edge = self.create_edge(
                    source_id=root_node_id,
                    target_id=node_id,
                    relation_type=RelationType.REGISTERED_ON,
                    label=f"Registered on {platform['name']}",
                )
                return node, edge, candidates
        except Exception:
            return None
        return None

    async def run(
        self,
        target: str,
        target_type: TargetType,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginResult:
        start_time = asyncio.get_event_loop().time()
        context = context or {}
        root_node_id = f"username:{target}"
        root_node = self.create_node(
            node_id=root_node_id,
            node_type=TargetType.USERNAME,
            value=target,
            label=f"@{target}",
            attributes={"initial_target": True},
        )

        nodes: List[EntityNode] = [root_node]
        edges: List[RelationEdge] = []
        all_candidates: List[tuple[str, TargetType, str]] = []

        # Dynamically load from SourceManager if available
        from hamsa.core.sources import SourceManager
        sm = SourceManager()
        all_sites_flag = context.get("all_sites", False)
        limit = None if all_sites_flag else 50
        cached_platforms = sm.load_sites(limit=limit)

        platforms_to_scan = cached_platforms if cached_platforms else list(PLATFORMS)
        logs: List[str] = [f"Checking username '{target}' across {len(platforms_to_scan)} community platforms..."]

        tasks = [
            self._check_platform(platform, target, root_node_id)
            for platform in platforms_to_scan
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, tuple) and res is not None:
                node, edge, candidates = res
                nodes.append(node)
                edges.append(edge)
                log_text = f"Found active account on {node.attributes.get('platform')}: {node.value}"
                if node.attributes.get("real_name"):
                    log_text += f" (Discovered Name: '{node.attributes['real_name']}')"
                logs.append(log_text)
                all_candidates.extend(candidates)

        duration = asyncio.get_event_loop().time() - start_time
        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=nodes,
            edges=edges,
            logs=logs,
            candidate_targets=all_candidates,
            execution_time_seconds=round(duration, 2),
        )
