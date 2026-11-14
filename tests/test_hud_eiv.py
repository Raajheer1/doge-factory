import unittest
import os
from pathlib import Path

from housing_graph.hud_eiv import (
    NOTICE_ID, SOURCES, _section_xml, build_hud_pilot,
)
from housing_graph.graph import HousingGraph, NODE_FIELDS, RELATIONSHIPS, validate_fixture


class HudEivSourceTests(unittest.TestCase):
    def test_section_xml_preserves_paragraphs_and_citation(self):
        xml = b"""<CFRGRANULE><SECTION><SECTNO>5.233</SECTNO>
        <SUBJECT>Verified rule</SUBJECT><P>(a) First <E>requirement</E>.</P>
        <P>(b) Exception.</P></SECTION></CFRGRANULE>"""
        title, passages = _section_xml(xml, "5.233")
        self.assertEqual(title, "Verified rule")
        self.assertEqual(passages, ["(a) First requirement.", "(b) Exception."])
        with self.assertRaises(ValueError):
            _section_xml(xml, "5.659")

    def test_invalid_download_stops_before_import(self):
        with self.assertRaises(ValueError):
            build_hud_pilot(download=lambda url: b"not an official section")

    def test_source_manifest_is_small_and_program_specific(self):
        self.assertEqual({c for c, *_ in SOURCES},
                         {"5.233", "5.236", "5.659", "982.516", "960.259"})
        self.assertIn("notice", NOTICE_ID)

    def test_rejects_unsupported_cross_reference(self):
        fixture = {
            "nodes": [
                {"label": "PolicyDocument", "id": "doc:a", "title": "A",
                 "text": "A policy", "source_url": "https://example.org/a"},
                {"label": "PolicyDocument", "id": "doc:b", "title": "B",
                 "text": "B policy", "source_url": "https://example.org/b"},
            ],
            "relationships": [
                {"type": "CITES", "src": "doc:a", "dst": "doc:b", "source_url": ""},
            ],
        }
        with self.assertRaises(ValueError):
            validate_fixture(fixture)


@unittest.skipUnless(os.getenv("HYDRADB_HUD_EIV_INTEGRATION") == "1"
                     and os.getenv("HYDRADB_API_KEY") and os.getenv("HYDRADB_DATABASE_ID")
                     and os.getenv("HYDRADB_HUD_EIV_ROSTER"),
                     "opt in with HYDRADB_HUD_EIV_INTEGRATION=1 and database/key/roster variables")
class HudEivHydraIntegrationTests(unittest.TestCase):
    def test_real_graph_traversal_and_repeat_import(self):
        graph = HousingGraph(
            os.environ["HYDRADB_DATABASE_ID"],
            os.getenv("HYDRADB_HUD_EIV_COLLECTION", "hud_eiv_pilot"),
            os.environ["HYDRADB_API_KEY"],
        )
        fixture, _ = build_hud_pilot(Path(os.environ["HYDRADB_HUD_EIV_ROSTER"]))
        expected_nodes = {}
        for node in fixture["nodes"]:
            expected_nodes[node["label"]] = expected_nodes.get(node["label"], 0) + 1
        expected_edges = {}
        for edge in fixture["relationships"]:
            expected_edges[edge["type"]] = expected_edges.get(edge["type"], 0) + 1

        def counts():
            nodes = {label: graph.query(f"MATCH (n:{label}) RETURN count(n) AS total")[0]["total"]
                     for label in NODE_FIELDS}
            edges = {kind: graph.query(
                f"MATCH (a:{src})-[:{kind}]->(b:{dst}) RETURN count(*) AS total"
            )[0]["total"] for kind, (src, dst) in RELATIONSHIPS.items()}
            return nodes, edges

        before = counts()
        graph.import_fixture(fixture)
        after = counts()
        self.assertEqual(before, after)
        for label, n in expected_nodes.items():
            self.assertEqual(after[0][label], n)
        for kind, n in expected_edges.items():
            self.assertEqual(after[1][kind], n)
        self.assertEqual(graph.document_context(NOTICE_ID)["findings"][0]["proposal_id"],
                         "hud-eiv:proposal:auditable-electronic-evidence")
        passage = graph.section_context("hud-eiv:cfr-2025:24:5.233:passage:001")
        self.assertEqual(passage["section"]["document_type"], "regulation")
        self.assertEqual(len(passage["next"]), 1)
        self.assertTrue(graph.policy_contacts(NOTICE_ID))
        self.assertEqual(after[1]["LOBBIED_ON"], 0)
        self.assertEqual(after[1]["HAS_AUTHORITY_OVER"], 0)


if __name__ == "__main__":
    unittest.main()
