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

    def test_reporting_engine(self):
        from hamsa.core.reporting import ReportGenerator

        graph = KnowledgeGraph()
        email_node = EntityNode(
            id="email:victim@target.com",
            type=TargetType.EMAIL,
            value="victim@target.com",
            label="victim@target.com",
            confidence=1.0,
            attributes={"domain": "target.com"},
        )
        breach_node = EntityNode(
            id="breach:linkedin",
            type=TargetType.BREACH,
            value="LinkedIn",
            label="LinkedIn 2012 Leak",
            confidence=0.9,
            attributes={"breached_date": "2012-05-05", "compromised_accounts": 164000000},
        )
        graph.add_node(email_node)
        graph.add_node(breach_node)
        graph.add_edge(RelationEdge(source_id=email_node.id, target_id=breach_node.id, relation_type=RelationType.EXPOSED_IN))

        reporter = ReportGenerator(graph)
        summary = reporter.generate_executive_summary([("victim@target.com", TargetType.EMAIL)])
        self.assertIn("victim@target.com", summary)
        self.assertIn("High Risk Exposure", summary)

        timeline = reporter.generate_timeline()
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["event"], "Data Breach: LinkedIn 2012 Leak")

        md = reporter.generate_markdown([("victim@target.com", TargetType.EMAIL)], title="Dossier Test")
        self.assertIn("Dossier Test", md)
        self.assertIn("LinkedIn 2012 Leak", md)

        html = reporter.generate_html([("victim@target.com", TargetType.EMAIL)], title="HTML Dossier")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("HTML Dossier", html)

    def test_graph_backend_abstraction(self):
        from hamsa.core.graph_backend import MemoryGraphBackend, Neo4jGraphBackend, create_graph_backend

        mem = create_graph_backend("memory")
        self.assertIsInstance(mem, MemoryGraphBackend)

        n1 = EntityNode(id="n1", type=TargetType.USERNAME, value="user1", label="User 1", attributes={"ip": "1.2.3.4"})
        n2 = EntityNode(id="n2", type=TargetType.USERNAME, value="user2", label="User 2", attributes={"ip": "1.2.3.4"})
        mem.add_node(n1)
        mem.add_node(n2)
        mem.add_edge(RelationEdge(source_id="n1", target_id="n2", relation_type=RelationType.ASSOCIATED_WITH))

        self.assertEqual(len(mem.get_nodes()), 2)
        self.assertEqual(len(mem.get_edges()), 1)

        # Test shared attributes detection (shared IP)
        shared = mem.find_shared_attributes("ip")
        self.assertIn("1.2.3.4", shared)
        self.assertEqual(len(shared["1.2.3.4"]), 2)

        mem.clear()
        self.assertEqual(len(mem.get_nodes()), 0)

        # Test Neo4j graceful degradation when offline
        neo = Neo4jGraphBackend(uri="bolt://127.0.0.1:19999")
        self.assertFalse(neo.is_connected())
        neo.add_node(n1)
        self.assertEqual(len(neo.get_nodes()), 1)

    def test_continuous_monitoring_and_diff(self):
        from hamsa.core.monitor import ScanDiffEngine, WatchlistManager

        old_snap = {
            "nodes": [
                {"id": "user:bob", "type": "username", "label": "bob", "attributes": {"platform": "github"}}
            ],
            "edges": []
        }
        new_snap = {
            "nodes": [
                {"id": "user:bob", "type": "username", "label": "bob", "attributes": {"platform": "github", "bio": "developer"}},
                {"id": "breach:adobe", "type": "breach", "label": "Adobe Breach", "attributes": {"date": "2013"}}
            ],
            "edges": [
                {"source": "user:bob", "target": "breach:adobe", "type": "exposed_in"}
            ]
        }

        diff = ScanDiffEngine.compute_diff(old_snap, new_snap)
        self.assertTrue(diff["has_drift"])
        self.assertEqual(diff["total_added_nodes"], 1)
        self.assertEqual(diff["total_modified_nodes"], 1)
        self.assertEqual(diff["total_new_edges"], 1)
        self.assertEqual(len(diff["new_breaches"]), 1)
        self.assertGreaterEqual(diff["drift_score"], 30)

        alert_md = ScanDiffEngine.format_alert_markdown("bob", diff)
        self.assertIn("HAMSA PROACTIVE INTELLIGENCE ALERT", alert_md)
        self.assertIn("Adobe Breach", alert_md)

        # Test WatchlistManager
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            w_file = f.name
        try:
            wm = WatchlistManager(filepath=w_file)
            entry = wm.add("target_alice", target_type="username")
            self.assertEqual(len(wm.list_all()), 1)
            self.assertEqual(entry.value, "target_alice")

            wm.update_scanned("target_alice", "username")
            self.assertIsNotNone(wm.list_all()[0].last_scanned)

            removed = wm.remove("target_alice", "username")
            self.assertTrue(removed)
            self.assertEqual(len(wm.list_all()), 0)
        finally:
            if os.path.exists(w_file):
                os.remove(w_file)

    def test_port_8080_protection(self):
        from hamsa.web.server import find_safe_port, is_port_available

        # Verifies port 8080 is strictly disallowed
        self.assertFalse(is_port_available("127.0.0.1", 8080))
        safe_port = find_safe_port("127.0.0.1", start_port=8080)
        self.assertNotEqual(safe_port, 8080)
        self.assertGreaterEqual(safe_port, 8888)

    def test_case_management_and_annotations(self):
        from hamsa.core.cases import CaseManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            cm = CaseManager(base_dir=tmp_dir)
            cases = cm.list_cases()
            self.assertGreaterEqual(len(cases), 1)  # Default case exists
            self.assertEqual(cases[0]["id"], "case_default")

            # Create new case
            c2 = cm.create_case(title="Project Alpha", description="Alpha description", tags=["Confidential"])
            self.assertIn("case_project_alpha", c2.id)

            # Update notes
            updated = cm.update_case(c2.id, notes="Subject last seen active.")
            self.assertEqual(updated.notes, "Subject last seen active.")

            # Annotate node
            ok = cm.annotate_node(c2.id, "user:admin", tag="Primary Suspect", color="#ef4444", notes="Key operator")
            self.assertTrue(ok)
            fetched = cm.get_case(c2.id)
            self.assertIn("user:admin", fetched.node_annotations)
            self.assertEqual(fetched.node_annotations["user:admin"]["tag"], "Primary Suspect")

            # Add evidence
            ev = cm.add_evidence(c2.id, url="https://target.com/profile", title="Profile Snapshot")
            self.assertIsNotNone(ev)
            self.assertEqual(len(cm.get_case(c2.id).evidence), 1)

            # Delete case
            deleted = cm.delete_case(c2.id)
            self.assertTrue(deleted)
            self.assertIsNone(cm.get_case(c2.id))

    def test_enterprise_database_manager(self):
        import asyncio
        from hamsa.core.database import DatabaseManager
        from hamsa.core.graph import KnowledgeGraph
        from hamsa.core.models import EntityNode, RelationEdge, TargetType, RelationType

        with tempfile.NamedTemporaryFile(suffix=".db") as tmp_db:
            db = DatabaseManager()
            db.engine_type = "sqlite"
            db.sqlite_path = tmp_db.name

            # Test connect and auto-migration
            connected = asyncio.run(db.connect())
            self.assertTrue(connected)

            # Test case creation
            case_data = asyncio.run(db.create_case(title="Operation Trident", case_id="case_trident", description="Test dossier"))
            self.assertEqual(case_data["id"], "case_trident")
            self.assertEqual(case_data["title"], "Operation Trident")

            # Test graph persistence
            kg = KnowledgeGraph()
            n1 = EntityNode(
                id="email:target@corp.com",
                type=TargetType.EMAIL,
                value="target@corp.com",
                label="Target Email",
                attributes={"breach_year": "2023", "breach_title": "MegaCorp Breach"}
            )
            n2 = EntityNode(
                id="phone:+62812345678",
                type=TargetType.PHONE,
                value="+62812345678",
                label="Target Phone",
                attributes={"carrier": "Telkomsel"}
            )
            e1 = RelationEdge(
                source_id="email:target@corp.com",
                target_id="phone:+62812345678",
                relation_type=RelationType.ASSOCIATED_WITH,
                label="Linked in resume"
            )
            kg.add_node(n1)
            kg.add_node(n2)
            kg.add_edge(e1)

            asyncio.run(db.save_graph("case_trident", kg))

            # Test graph loading
            loaded = asyncio.run(db.load_graph("case_trident"))
            self.assertEqual(len(loaded.nodes), 2)
            self.assertEqual(len(loaded.edges), 1)
            self.assertIn("email:target@corp.com", loaded.nodes)

            # Test node annotation
            annotated = asyncio.run(db.annotate_node("case_trident", "email:target@corp.com", tag="Primary Suspect", color="#ef4444", notes="Key vector"))
            self.assertTrue(annotated)

            # Test case listing
            cases = asyncio.run(db.list_cases())
            self.assertGreaterEqual(len(cases), 1)
            c_found = next(c for c in cases if c["id"] == "case_trident")
            self.assertEqual(c_found["entity_count"], 2)

            # Test evidence capture
            ev = asyncio.run(db.add_evidence("case_trident", url="https://pastebin.com/raw/xyz", title="Dump Evidence", notes="Paste leak"))
            self.assertEqual(ev["title"], "Dump Evidence")

            # Test timeline extraction
            events = asyncio.run(db.get_timeline_events("case_trident"))
            self.assertGreaterEqual(len(events), 1)
            self.assertEqual(events[0]["category"], "breach")

            # Test notes update
            notes_saved = asyncio.run(db.update_case_notes("case_trident", "All entities confirmed."))
            self.assertTrue(notes_saved)

            asyncio.run(db.close())

    def test_fastapi_enterprise_app(self):
        try:
            from fastapi.testclient import TestClient
            from hamsa.web.enterprise_app import app
        except ImportError:
            raise unittest.SkipTest("FastAPI or TestClient not installed; skipping ASGI endpoint tests.")

        with TestClient(app) as client:
            # 1. Health check
            resp = client.get("/api/health")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "online")
            self.assertEqual(data["version"], "2.0.0")

            # 2. Create case
            c_resp = client.post("/api/cases", json={"title": "Enterprise Case Test", "description": "Testing FastAPI", "tags": ["Unit-Test"]})
            self.assertEqual(c_resp.status_code, 200)
            c_data = c_resp.json()
            self.assertTrue(c_data["success"])
            case_id = c_data["case"]["id"]

            # 3. List cases
            l_resp = client.get("/api/cases")
            self.assertEqual(l_resp.status_code, 200)
            self.assertTrue(any(c["id"] == case_id for c in l_resp.json()["cases"]))

            # 4. Get case detail
            d_resp = client.get(f"/api/cases/{case_id}")
            self.assertEqual(d_resp.status_code, 200)
            self.assertEqual(d_resp.json()["title"], "Enterprise Case Test")

            # 5. Timeline endpoint
            t_resp = client.get(f"/api/timeline?case_id={case_id}")
            self.assertEqual(t_resp.status_code, 200)
            self.assertIn("events", t_resp.json())

            # 6. Cache stats
            cs_resp = client.get("/api/cache/stats")
            self.assertEqual(cs_resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
