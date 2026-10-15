"""
HAMSA Global Interoperability & Forensic Graph Exporter
Generates standard data interchange formats:
- GraphML (Gephi, Cytoscape, yEd, Maltego)
- STIX 2.1 Cyber Threat Intelligence Bundle
- Forensic CSV (Nodes & Edges)
Pure Python Standard Library implementation.
"""

import csv
import io
import json
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
import xml.sax.saxutils as saxutils

from hamsa.core.graph import KnowledgeGraph
from hamsa.core.models import TargetType


class GraphMLExporter:
    """Exports KnowledgeGraph to standard XML GraphML specification."""

    @classmethod
    def export(cls, graph: KnowledgeGraph) -> str:
        out = io.StringIO()
        out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        out.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns"\n')
        out.write('         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n')
        out.write('         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns\n')
        out.write('         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">\n')

        # Keys
        out.write('  <key id="type" for="node" attr.name="type" attr.type="string"/>\n')
        out.write('  <key id="label" for="node" attr.name="label" attr.type="string"/>\n')
        out.write('  <key id="value" for="node" attr.name="value" attr.type="string"/>\n')
        out.write('  <key id="confidence" for="node" attr.name="confidence" attr.type="double"/>\n')
        out.write('  <key id="attributes" for="node" attr.name="attributes" attr.type="string"/>\n')
        out.write('  <key id="relation" for="edge" attr.name="relation" attr.type="string"/>\n')
        out.write('  <key id="weight" for="edge" attr.name="weight" attr.type="double"/>\n')

        out.write('  <graph id="HAMSA_KnowledgeGraph" edgedefault="undirected">\n')

        # Nodes
        for node in graph.nodes.values():
            n_id = saxutils.escape(node.id)
            n_type = saxutils.escape(node.type.value)
            n_label = saxutils.escape(node.label or node.value)
            n_val = saxutils.escape(node.value)
            n_conf = str(node.confidence)
            n_attrs = saxutils.escape(json.dumps(node.attributes, ensure_ascii=False))

            out.write(f'    <node id="{n_id}">\n')
            out.write(f'      <data key="type">{n_type}</data>\n')
            out.write(f'      <data key="label">{n_label}</data>\n')
            out.write(f'      <data key="value">{n_val}</data>\n')
            out.write(f'      <data key="confidence">{n_conf}</data>\n')
            out.write(f'      <data key="attributes">{n_attrs}</data>\n')
            out.write('    </node>\n')

        # Edges
        for i, edge in enumerate(graph.edges):
            e_id = f"e{i}"
            s_id = saxutils.escape(edge.source_id)
            t_id = saxutils.escape(edge.target_id)
            rel = saxutils.escape(edge.relation_type.value)
            weight = str(edge.weight)

            out.write(f'    <edge id="{e_id}" source="{s_id}" target="{t_id}">\n')
            out.write(f'      <data key="relation">{rel}</data>\n')
            out.write(f'      <data key="weight">{weight}</data>\n')
            out.write('    </edge>\n')

        out.write('  </graph>\n')
        out.write('</graphml>\n')
        return out.getvalue()


class STIX2Exporter:
    """Exports KnowledgeGraph to OASIS STIX 2.1 Cyber Threat Intelligence Bundle."""

    @classmethod
    def export(cls, graph: KnowledgeGraph) -> Dict[str, Any]:
        bundle_id = f"bundle--{uuid.uuid4()}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        objects = []
        node_stix_map = {}

        # 1. Identity representing HAMSA investigator
        author_id = f"identity--{uuid.uuid4()}"
        objects.append({
            "type": "identity",
            "spec_version": "2.1",
            "id": author_id,
            "created": now_iso,
            "modified": now_iso,
            "name": "HAMSA OSINT Intelligence Suite",
            "identity_class": "system"
        })

        # 2. Map nodes to STIX Indicators / Observed Data
        for node in graph.nodes.values():
            stix_id = f"indicator--{uuid.uuid4()}"
            node_stix_map[node.id] = stix_id

            pattern = f"[{node.type.value}:value = '{node.value}']"
            if node.type == TargetType.EMAIL:
                pattern = f"[email-addr:value = '{node.value}']"
            elif node.type == TargetType.USERNAME:
                pattern = f"[user-account:account_login = '{node.value}']"
            elif node.type == TargetType.PHONE:
                pattern = f"[phone-number:value = '{node.value}']"

            objects.append({
                "type": "indicator",
                "spec_version": "2.1",
                "id": stix_id,
                "created": now_iso,
                "modified": now_iso,
                "created_by_ref": author_id,
                "name": node.label or node.value,
                "description": f"OSINT Entity ({node.type.value}) collected via HAMSA",
                "indicator_types": ["malicious-activity" if node.type == TargetType.BREACH else "unknown"],
                "pattern": pattern,
                "pattern_type": "stix",
                "valid_from": now_iso,
                "confidence": int(node.confidence * 100),
                "custom_properties": node.attributes
            })

        # 3. Map edges to STIX Relationships
        for edge in graph.edges:
            s_stix = node_stix_map.get(edge.source_id)
            t_stix = node_stix_map.get(edge.target_id)
            if s_stix and t_stix:
                rel_id = f"relationship--{uuid.uuid4()}"
                objects.append({
                    "type": "relationship",
                    "spec_version": "2.1",
                    "id": rel_id,
                    "created": now_iso,
                    "modified": now_iso,
                    "created_by_ref": author_id,
                    "relationship_type": "related-to",
                    "source_ref": s_stix,
                    "target_ref": t_stix,
                    "description": edge.label or edge.relation_type.value
                })

        return {
            "type": "bundle",
            "id": bundle_id,
            "objects": objects
        }


class CSVExporter:
    """Exports nodes and edges to CSV tables for tabular investigation reporting."""

    @classmethod
    def export_nodes_csv(cls, graph: KnowledgeGraph) -> str:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["id", "type", "value", "label", "confidence", "source_plugin", "attributes_json"])
        for node in graph.nodes.values():
            writer.writerow([
                node.id,
                node.type.value,
                node.value,
                node.label or "",
                node.confidence,
                node.source_plugin or "",
                json.dumps(node.attributes, ensure_ascii=False)
            ])
        return out.getvalue()

    @classmethod
    def export_edges_csv(cls, graph: KnowledgeGraph) -> str:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["source_id", "target_id", "relation_type", "label", "weight", "metadata_json"])
        for edge in graph.edges:
            writer.writerow([
                edge.source_id,
                edge.target_id,
                edge.relation_type.value,
                edge.label or "",
                edge.weight,
                json.dumps(edge.metadata, ensure_ascii=False)
            ])
        return out.getvalue()
