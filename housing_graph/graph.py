"""Validated housing-policy imports and reads using HydraDB's hosted BYOG API."""

import json
import math
import os
from urllib import error, request


NODE_FIELDS = {
    "Jurisdiction": ("id", "name", "level"),
    "PolicyDocument": ("id", "title", "text", "source_url"),
    "Actor": ("id", "name", "type"),
    "PolicyFinding": ("id", "description", "evidence_quote"),
    "RedlineProposal": ("id", "proposed_text", "estimated_annual_savings"),
}

RELATIONSHIPS = {
    "ISSUED": ("Jurisdiction", "PolicyDocument"),
    "HOLDS_OFFICE_IN": ("Actor", "Jurisdiction"),
    "REPRESENTS": ("Actor", "Actor"),
    "LOBBIED_ON": ("Actor", "PolicyDocument"),
    "HAS_AUTHORITY_OVER": ("Actor", "PolicyDocument"),
    "HAS_FINDING": ("PolicyDocument", "PolicyFinding"),
    "ADDRESSED_BY": ("PolicyFinding", "RedlineProposal"),
    "PROPOSES_CHANGE_TO": ("RedlineProposal", "PolicyDocument"),
}


def _url(value):
    return isinstance(value, str) and value.startswith(("https://", "http://")) and len(value.split("://", 1)[1]) > 0


def validate_fixture(fixture):
    """Reject malformed nodes, invalid edge roles, and unsupported disclosures before writing."""
    if not isinstance(fixture, dict) or set(fixture) != {"nodes", "relationships"}:
        raise ValueError("fixture must contain nodes and relationships")
    nodes = fixture["nodes"]
    edges = fixture["relationships"]
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("nodes and relationships must be lists")
    by_id = {}
    for node in nodes:
        if not isinstance(node, dict) or node.get("label") not in NODE_FIELDS:
            raise ValueError("unknown node label")
        label = node["label"]
        if set(node) != {"label", *NODE_FIELDS[label]}:
            raise ValueError(f"invalid {label} properties")
        node_id = node["id"]
        if not isinstance(node_id, str) or not node_id.strip() or node_id in by_id:
            raise ValueError("node IDs must be unique nonempty strings")
        if any(not isinstance(node[field], str) or not node[field].strip()
               for field in NODE_FIELDS[label] if field != "estimated_annual_savings"):
            raise ValueError(f"invalid {label} property")
        if label == "Jurisdiction" and node["level"] not in {"federal", "state", "local"}:
            raise ValueError("invalid jurisdiction level")
        if label == "Actor" and node["type"] not in {"official", "lobbyist", "organization"}:
            raise ValueError("invalid actor type")
        if label == "RedlineProposal" and (
            isinstance(node["estimated_annual_savings"], bool)
            or not isinstance(node["estimated_annual_savings"], (int, float))
            or not math.isfinite(node["estimated_annual_savings"])
            or node["estimated_annual_savings"] < 0
        ):
            raise ValueError("savings must be a nonnegative number")
        if label == "PolicyDocument" and not _url(node["source_url"]):
            raise ValueError("document requires a source URL")
        by_id[node_id] = node

    seen = set()
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("type") not in RELATIONSHIPS:
            raise ValueError("unknown relationship type")
        kind, src, dst = edge["type"], edge.get("src"), edge.get("dst")
        expected = {"type", "src", "dst"}
        if kind in {"LOBBIED_ON", "HAS_AUTHORITY_OVER"}:
            expected.add("source_url")
        if (set(edge) != expected or not isinstance(src, str) or not isinstance(dst, str)
                or src not in by_id or dst not in by_id):
            raise ValueError("relationship endpoints or properties invalid")
        if (by_id[src]["label"], by_id[dst]["label"]) != RELATIONSHIPS[kind]:
            raise ValueError("mismatched relationship endpoints")
        actor_type = by_id[src].get("type")
        if kind in {"HOLDS_OFFICE_IN", "HAS_AUTHORITY_OVER"} and actor_type != "official":
            raise ValueError("only officials hold office or authority")
        if kind in {"REPRESENTS", "LOBBIED_ON"} and actor_type != "lobbyist":
            raise ValueError("only lobbyists represent clients or lobby")
        if kind == "REPRESENTS" and by_id[dst]["type"] != "organization":
            raise ValueError("lobbyists must represent organizations")
        if kind in {"LOBBIED_ON", "HAS_AUTHORITY_OVER"} and not _url(edge["source_url"]):
            raise ValueError("lobbying and authority require a supporting source URL")
        key = (kind, src, dst)
        if key in seen:
            raise ValueError("duplicate relationship")
        seen.add(key)
    return fixture


class HousingGraph:
    def __init__(self, database, collection, api_key, base_url="https://api.hydradb.com"):
        if not all((database, collection, api_key)):
            raise ValueError("database, collection and api_key are required")
        self.database = database
        self.collection = collection
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_env(cls):
        return cls(
            os.environ["HYDRADB_DATABASE_ID"],
            os.environ.get("HYDRADB_COLLECTION", "doge_housing"),
            os.environ["HYDRADB_API_KEY"],
            os.environ.get("HYDRADB_BASE_URL", "https://api.hydradb.com"),
        )

    def query(self, cypher, params=None):
        payload = json.dumps({
            "database": self.database, "collection": self.collection,
            "query": cypher, "params": params or {},
        }).encode()
        req = request.Request(
            self.base_url + "/byog/query", data=payload,
            headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                body = json.load(response)
        except error.HTTPError as exc:
            raise RuntimeError(f"HydraDB HTTP {exc.code}: {exc.read().decode()}") from exc
        if not body.get("success") or not isinstance(body.get("data"), list):
            raise RuntimeError(f"HydraDB query failed: {body.get('error') or body}")
        return body["data"]

    def import_fixture(self, fixture):
        validate_fixture(fixture)
        # Hosted BYOG uses user-owned string property IDs (internal numeric IDs are not stable).
        # MERGE followed by SET refreshes properties on every rerun.
        for label, fields in NODE_FIELDS.items():
            rows = [{field: node[field] for field in fields}
                    for node in fixture["nodes"] if node["label"] == label]
            if rows:
                assignments = ", ".join(f"n.{field} = row.{field}" for field in fields if field != "id")
                self.query(
                    f"UNWIND $rows AS row MERGE (n:{label} {{id: row.id}}) SET {assignments}",
                    {"rows": rows},
                )
        for kind, (source_label, target_label) in RELATIONSHIPS.items():
            rows = [edge for edge in fixture["relationships"] if edge["type"] == kind]
            if not rows:
                continue
            cypher = (
                f"UNWIND $rows AS row "
                f"MATCH (a:{source_label} {{id: row.src}}), (b:{target_label} {{id: row.dst}}) "
                f"MERGE (a)-[r:{kind}]->(b)"
            )
            if kind in {"LOBBIED_ON", "HAS_AUTHORITY_OVER"}:
                cypher += " SET r.source_url = row.source_url"
            self.query(cypher, {"rows": rows})

    def document_context(self, document_id):
        """Traverse from a document without requiring unrelated optional connections."""
        doc = self.query(
            "MATCH (d:PolicyDocument {id: $id}) RETURN d.id AS id, d.title AS title, "
            "d.text AS text, d.source_url AS source_url", {"id": document_id},
        )
        if not doc:
            return None
        params = {"id": document_id}
        return {
            "document": doc[0],
            "jurisdictions": self.query(
                "MATCH (j:Jurisdiction)-[:ISSUED]->(d:PolicyDocument {id: $id}) "
                "RETURN j.id AS id, j.name AS name, j.level AS level", params,
            ),
            "findings": self.query(
                "MATCH (d:PolicyDocument {id: $id})-[:HAS_FINDING]->(f:PolicyFinding) "
                "OPTIONAL MATCH (f)-[:ADDRESSED_BY]->(p:RedlineProposal)-[:PROPOSES_CHANGE_TO]->(d) "
                "RETURN f.id AS id, f.description AS description, f.evidence_quote AS evidence_quote, "
                "p.id AS proposal_id, p.proposed_text AS proposed_text, "
                "p.estimated_annual_savings AS estimated_annual_savings", params,
            ),
            "officials": self.query(
                "MATCH (o:Actor)-[r:HAS_AUTHORITY_OVER]->(d:PolicyDocument {id: $id}) "
                "RETURN o.id AS id, o.name AS name, r.source_url AS source_url", params,
            ),
            "lobbying": self.query(
                "MATCH (l:Actor)-[r:LOBBIED_ON]->(d:PolicyDocument {id: $id}) "
                "OPTIONAL MATCH (l)-[:REPRESENTS]->(c:Actor) "
                "RETURN l.id AS lobbyist_id, l.name AS lobbyist_name, "
                "c.id AS client_id, c.name AS client_name, r.source_url AS filing_url", params,
            ),
        }
