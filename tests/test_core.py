"""
Comprehensive unit tests for Hamsa core models, graph engine, and plugins.
"""

import asyncio
import os
import tempfile
import unittest

from hamsa.core.graph import KnowledgeGraph
from hamsa.core.models import (
    EntityNode,
    PluginResult,
    RelationEdge,
    RelationType,
    TargetType,
)
from hamsa.core.orchestrator import Orchestrator
from hamsa.plugins.phone.phone_parser import PhoneParserPlugin


class TestHamsaCore(unittest.TestCase):
    def test_entity_and_relation_models(self):
        node = EntityNode(
            id="email:alice@example.com",
            type=TargetType.EMAIL,
            value="alice@example.com",
            label="alice@example.com",
            attributes={"domain": "example.com"},
        )
        self.assertEqual(node.type, TargetType.EMAIL)
        d = node.to_dict()
        self.assertEqual(d["id"], "email:alice@example.com")
        self.assertEqual(d["attributes"]["domain"], "example.com")

        edge = RelationEdge(
            source_id="email:alice@example.com",
            target_id="breach:canva",
            relation_type=RelationType.EXPOSED_IN,
        )
        self.assertEqual(edge.relation_type, RelationType.EXPOSED_IN)
        ed = edge.to_dict()
        self.assertEqual(ed["source"], "email:alice@example.com")

    def test_knowledge_graph_merging_and_export(self):
        graph = KnowledgeGraph()
        node1 = EntityNode(
            id="username:john",
            type=TargetType.USERNAME,
            value="john",
            label="@john",
            attributes={"found_on": ["github"]},
        )
        graph.add_node(node1)

        # Merge with updated attributes
        node2 = EntityNode(
            id="username:john",
            type=TargetType.USERNAME,
            value="john",
            label="@john",
            attributes={"found_on": ["github", "reddit"], "country": "ID"},
        )
        graph.add_node(node2)

        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(len(graph.nodes["username:john"].attributes["found_on"]), 2)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            html_path = f.name

        try:
            graph.export_json(json_path)
            self.assertTrue(os.path.exists(json_path))
            self.assertGreater(os.path.getsize(json_path), 20)

            graph.export_html(html_path, title="Test Graph")
            self.assertTrue(os.path.exists(html_path))
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("Test Graph", content)
                self.assertIn("vis-network", content)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)
            if os.path.exists(html_path):
                os.remove(html_path)

    def test_phone_parser_indonesia(self):
        plugin = PhoneParserPlugin()
        self.assertTrue(plugin.can_handle("081234567890", TargetType.PHONE))
        self.assertFalse(plugin.can_handle("alice@test.com", TargetType.EMAIL))

        result = asyncio.run(plugin.run("081234567890", TargetType.PHONE))
        self.assertTrue(result.success)

        # Check root node
        root = next((n for n in result.nodes if n.type == TargetType.PHONE), None)
        self.assertIsNotNone(root)
        self.assertEqual(root.attributes["carrier"], "Telkomsel")
        self.assertEqual(root.attributes["country"], "Indonesia")
        self.assertEqual(root.value, "+6281234567890")

    def test_orchestrator_multi_target_correlation(self):
        orch = Orchestrator()
        self.assertGreaterEqual(len(orch.plugins), 5)

        # Scan phone and verify in graph
        targets = [("0818123456", TargetType.PHONE)]
        graph = asyncio.run(orch.scan(targets, max_depth=1))
        summary = graph.to_dict()["summary"]
        self.assertGreaterEqual(summary["total_entities"], 3)  # Phone + Country + Carrier
        self.assertGreaterEqual(summary["total_relations"], 2)

    def test_name_resolver_dork_generation(self):
        from hamsa.plugins.username.name_resolver import NameResolverPlugin

        plugin = NameResolverPlugin()
        self.assertTrue(plugin.can_handle("Linus Torvalds", TargetType.GENERIC))

        result = asyncio.run(plugin.run("Linus Torvalds", TargetType.GENERIC))
        self.assertTrue(result.success)
        self.assertGreaterEqual(len(result.nodes), 1)
        root = result.nodes[0]
        self.assertIn("google_dork", root.attributes)
        self.assertIn("bing_dork", root.attributes)
        self.assertIn("duckduckgo_dork", root.attributes)


    def test_source_manager_caching(self):
        from hamsa.core.sources import SourceManager

        sm = SourceManager()
        sites = sm.load_sites()
        self.assertIsInstance(sites, list)
        if sites:
            self.assertIn("name", sites[0])
            self.assertIn("url", sites[0])

    def test_phone_presence_plugin(self):
        from hamsa.plugins.phone.phone_presence import PhonePresencePlugin

        plugin = PhonePresencePlugin()
        self.assertTrue(plugin.can_handle("08123456789", TargetType.PHONE))
        res = asyncio.run(plugin.run("08123456789", TargetType.PHONE))
        self.assertTrue(res.success)
        types = [n.attributes.get("line_type") for n in res.nodes if "line_type" in n.attributes]
        self.assertIn("Mobile Cellular", types)

    def test_csv_export(self):
        graph = KnowledgeGraph()
        node = EntityNode(
            id="email:test@example.com",
            type=TargetType.EMAIL,
            value="test@example.com",
            label="test@example.com",
        )
        graph.add_node(node)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            csv_path = f.name
        try:
            graph.export_csv(csv_path)
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("SECTION: ENTITIES", content)
                self.assertIn("email:test@example.com", content)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)


    def test_contact_tags_resolver_plugin(self):
        from hamsa.plugins.phone.contact_tags import ContactTagResolverPlugin

        plugin = ContactTagResolverPlugin()
        self.assertTrue(plugin.can_handle("+628123456789", TargetType.PHONE))
        res = asyncio.run(plugin.run("+628123456789", TargetType.PHONE))
        self.assertTrue(res.success)
        self.assertTrue(any("contact" in msg.lower() or "getcontact" in msg.lower() for msg in res.logs))

    def test_agent_brain_planning(self):
        from hamsa.core.agent_brain import AgentBrain

        brain = AgentBrain(max_depth=2)
        graph = KnowledgeGraph()
        node = EntityNode(
            id="email:victim@target.com",
            type=TargetType.BREACH,
            value="victim@target.com",
            label="victim@target.com",
            attributes={"real_name": "John Doe"},
        )
        graph.add_node(node)

        raw_candidates = [
            ("John Doe", TargetType.GENERIC, "email:victim@target.com"),
            ("unknown", TargetType.USERNAME, "email:victim@target.com"),  # Garbage token
            ("admin", TargetType.USERNAME, "email:victim@target.com"),    # Garbage token
            ("johndoe99", TargetType.USERNAME, "email:victim@target.com"),
        ]

        plan = brain.evaluate_and_plan(
            graph=graph,
            current_depth=1,
            raw_candidates=raw_candidates,
            visited_keys=set(),
        )

        self.assertTrue(plan["continue_investigation"])
        self.assertGreater(len(plan["prioritized_targets"]), 0)
        # Verify garbage tokens were pruned
        target_vals = [t[0].lower() for t in plan["prioritized_targets"]]
        self.assertNotIn("unknown", target_vals)
        self.assertNotIn("admin", target_vals)
        self.assertIn("John Doe", [t[0] for t in plan["prioritized_targets"]])

    def test_knowledge_graph_clear(self):
        graph = KnowledgeGraph()
        graph.add_node(EntityNode(id="test:1", type=TargetType.GENERIC, value="val", label="lbl"))
        self.assertEqual(len(graph.nodes), 1)
        graph.clear()
        self.assertEqual(len(graph.nodes), 0)
        self.assertEqual(len(graph.edges), 0)

    def test_two_tier_ttl_cache(self):
        from hamsa.core.cache import TTLCache, cached

        cache = TTLCache(maxsize=3, ttl_seconds=1.0, enable_redis=False)
        cache.set("key1", "val1")
        cache.set("key2", "val2")
        self.assertEqual(cache.get("key1"), "val1")
        self.assertEqual(cache.get("key2"), "val2")
        self.assertIsNone(cache.get("key_missing"))

        # Test LRU eviction when maxsize is exceeded
        cache.set("key3", "val3")
        cache.set("key4", "val4")  # Should evict key1 (or oldest)
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key4"), "val4")

        # Test stats
        st = cache.stats()
        self.assertEqual(st["l1_memory_size"], 3)
        self.assertEqual(st["l1_maxsize"], 3)

        # Test delete & clear
        cache.delete("key4")
        self.assertIsNone(cache.get("key4"))
        cache.clear()
        self.assertEqual(cache.stats()["l1_memory_size"], 0)


if __name__ == "__main__":
    unittest.main()
