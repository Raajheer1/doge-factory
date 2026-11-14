import copy
import json
import os
import unittest
import uuid
from pathlib import Path
from urllib import request

from housing_graph import HousingGraph, validate_fixture
from housing_graph.graph import NODE_FIELDS, RELATIONSHIPS


FIXTURE = json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "fictional_housing.json").read_text())


class ValidationTests(unittest.TestCase):
    def test_fixture_is_valid(self):
        self.assertIs(validate_fixture(FIXTURE), FIXTURE)

    def test_rejects_bad_levels_and_actor_types(self):
        for node_id, field, value in [
            ("fictional:local:bayhaven", "level", "county"),
            ("fictional:actor:lobbyist", "type", "developer"),
        ]:
            with self.subTest(field=field):
                data = copy.deepcopy(FIXTURE)
                next(n for n in data["nodes"] if n["id"] == node_id)[field] = value
                with self.assertRaises(ValueError):
                    validate_fixture(data)

    def test_rejects_mismatched_edges_and_missing_sources(self):
        for update in [
            {"type": "ISSUED", "src": "fictional:actor:official"},
            {"type": "REPRESENTS", "dst": "fictional:actor:official"},
            {"type": "HOLDS_OFFICE_IN", "src": "fictional:actor:lobbyist"},
            {"type": "HAS_AUTHORITY_OVER", "src": "fictional:actor:lobbyist"},
            {"type": "LOBBIED_ON", "src": "fictional:actor:official"},
            {"type": "LOBBIED_ON", "source_url": ""},
            {"type": "HAS_AUTHORITY_OVER", "source_url": ""},
            {"type": "HAS_FINDING", "dst": "fictional:doc:aster"},
        ]:
            with self.subTest(update=update):
                data = copy.deepcopy(FIXTURE)
                edge = next(e for e in data["relationships"] if e["type"] == update["type"])
                edge.update(update)
                with self.assertRaises(ValueError):
                    validate_fixture(data)

    def test_rejects_duplicate_ids_and_edges(self):
        for key in ("nodes", "relationships"):
            data = copy.deepcopy(FIXTURE)
            data[key].append(copy.deepcopy(data[key][0]))
            with self.assertRaises(ValueError):
                validate_fixture(data)

    def test_unknown_savings_may_be_null_but_not_speculative(self):
        data = copy.deepcopy(FIXTURE)
        proposal = next(n for n in data["nodes"] if n["label"] == "RedlineProposal")
        proposal["estimated_annual_savings"] = None
        validate_fixture(data)
        for invalid in (-1, True, float("nan")):
            with self.subTest(invalid=invalid):
                proposal["estimated_annual_savings"] = invalid
                with self.assertRaises(ValueError):
                    validate_fixture(data)


@unittest.skipUnless(
    os.getenv("HYDRADB_TEST_DATABASE") and os.getenv("HYDRADB_API_KEY"),
    "set HYDRADB_TEST_DATABASE and HYDRADB_API_KEY to run against real hosted HydraDB",
)
class HydraDBIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Unique collection isolates tests from application data and other test runs.
        cls.collection = "housing_test_" + uuid.uuid4().hex
        cls.graph = HousingGraph(
            os.environ["HYDRADB_TEST_DATABASE"],
            cls.collection,
            os.environ["HYDRADB_API_KEY"],
            os.getenv("HYDRADB_BASE_URL", "https://api.hydradb.com"),
        )
        cls.graph.import_fixture(FIXTURE)

    @classmethod
    def tearDownClass(cls):
        # The collection is created exclusively for this test suite.
        payload = json.dumps({"database": cls.graph.database, "collection": cls.collection}).encode()
        req = request.Request(
            cls.graph.base_url + "/byog/collections", data=payload, method="DELETE",
            headers={"Authorization": "Bearer " + cls.graph.api_key,
                     "Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=30) as response:
            if not json.load(response).get("success"):
                raise RuntimeError("could not remove test collection")

    def test_jurisdiction_issuance_and_actor_roles(self):
        rows = self.graph.query(
            "MATCH (j:Jurisdiction)-[:ISSUED]->(d:PolicyDocument) "
            "RETURN j.level AS level, d.id AS document_id"
        )
        self.assertEqual({r["level"] for r in rows}, {"local", "state", "federal"})
        self.assertEqual(len(rows), 3)
        actors = self.graph.query("MATCH (a:Actor) RETURN a.id AS id, a.type AS type")
        self.assertEqual({a["type"] for a in actors}, {"official", "lobbyist", "organization"})
        self.assertEqual(len(actors), 3)
        office = self.graph.query(
            "MATCH (a:Actor)-[:HOLDS_OFFICE_IN]->(j:Jurisdiction) "
            "RETURN a.type AS type, j.level AS level"
        )
        self.assertEqual(office, [{"type": "official", "level": "local"}])
        clients = self.graph.query(
            "MATCH (a:Actor)-[:REPRESENTS]->(c:Actor) "
            "RETURN a.type AS lobbyist_type, c.type AS client_type"
        )
        self.assertEqual(clients, [{"lobbyist_type": "lobbyist", "client_type": "organization"}])

    def test_document_context_and_filing_url(self):
        context = self.graph.document_context("fictional:doc:bayhaven")
        self.assertEqual(context["jurisdictions"][0]["level"], "local")
        self.assertIn("Applications must be submitted", context["document"]["text"])
        self.assertEqual(context["findings"][0]["proposal_id"], "fictional:proposal:online")
        self.assertEqual(context["findings"][0]["estimated_annual_savings"], 12000)
        self.assertEqual(context["officials"][0]["id"], "fictional:actor:official")
        self.assertEqual(context["lobbying"][0]["client_id"], "fictional:actor:client")
        self.assertEqual(context["lobbying"][0]["filing_url"],
                         "https://example.org/fictional/public-lobbying-filing")

    def test_repeat_import_is_idempotent(self):
        def counts():
            nodes = {
                label: self.graph.query(f"MATCH (n:{label}) RETURN count(n) AS total")[0]["total"]
                for label in NODE_FIELDS
            }
            edges = {
                kind: self.graph.query(
                    f"MATCH (a:{src})-[:{kind}]->(b:{dst}) RETURN count(*) AS total"
                )[0]["total"]
                for kind, (src, dst) in RELATIONSHIPS.items()
            }
            return nodes, edges

        before = counts()
        self.graph.import_fixture(FIXTURE)
        after = counts()
        self.assertEqual(before, after)
        self.assertEqual(sum(before[0].values()), len(FIXTURE["nodes"]))
        self.assertEqual(sum(before[1].values()), len(FIXTURE["relationships"]))


if __name__ == "__main__":
    unittest.main()
