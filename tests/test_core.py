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


    def test_phone_infoga_plugin(self):
        from hamsa.plugins.phone.phone_infoga import PhoneInfogaDorksPlugin

        plugin = PhoneInfogaDorksPlugin()
        self.assertTrue(plugin.can_handle("08123456789", TargetType.PHONE))
        res = asyncio.run(plugin.run("08123456789", TargetType.PHONE))
        self.assertTrue(res.success)
        dork_nodes = [n for n in res.nodes if "google_search_url" in n.attributes]
        self.assertGreaterEqual(len(dork_nodes), 3)


if __name__ == "__main__":
    unittest.main()
