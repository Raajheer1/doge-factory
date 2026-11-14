"""Validated housing-policy imports and reads using HydraDB's hosted BYOG API."""

import json
import math
import os
from datetime import date
from urllib.parse import urlparse
from urllib import error, request


NODE_FIELDS = {
    "Jurisdiction": ("id", "name", "level"),
    "PolicyDocument": ("id", "title", "text", "source_url", "citation", "document_type",
                       "issuing_agency", "publication_date", "status", "topics"),
    "PolicySection": ("id", "title", "text", "citation", "order", "source_url"),
    "Actor": ("id", "name", "type", "role", "organization", "source_url",
              "verified_at", "public_contact"),
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
    "HAS_SECTION": ("PolicyDocument", "PolicySection"),
    "NEXT_SECTION": ("PolicySection", "PolicySection"),
    "CITES": ("PolicyDocument", "PolicyDocument"),
    "ADMINISTERS": ("Actor", "PolicyDocument"),
    "WORKS_FOR": ("Actor", "Actor"),
}

OPTIONAL_NODE_FIELDS = {
    "PolicyDocument": {"citation", "document_type", "issuing_agency", "publication_date",
                       "status", "topics"},
    "Actor": {"role", "organization", "source_url", "verified_at", "public_contact"},
}
SOURCED_RELATIONSHIPS = {
    "LOBBIED_ON", "HAS_AUTHORITY_OVER", "CITES", "ADMINISTERS", "WORKS_FOR",
}


def _url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"https", "http"} and bool(parsed.netloc)


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
        required = set(NODE_FIELDS[label]) - OPTIONAL_NODE_FIELDS.get(label, set())
        if not required <= set(node) or not set(node) <= {"label", *NODE_FIELDS[label]}:
            raise ValueError(f"invalid {label} properties")
        node_id = node["id"]
        if not isinstance(node_id, str) or not node_id.strip() or node_id in by_id:
            raise ValueError("node IDs must be unique nonempty strings")
        required_strings = required - {"order", "estimated_annual_savings"}
        if any(not isinstance(node[field], str) or not node[field].strip()
               for field in required_strings):
            raise ValueError(f"invalid {label} property")
        if any(not isinstance(value, str) for field, value in node.items()
               if field in OPTIONAL_NODE_FIELDS.get(label, ())):
            raise ValueError(f"invalid {label} metadata")
        if label == "PolicySection" and (
            isinstance(node["order"], bool) or not isinstance(node["order"], int)
            or node["order"] < 1
        ):
            raise ValueError("section order must be positive")
        if label == "PolicyDocument" and "document_type" in node and node["document_type"] not in {
            "statute", "regulation", "notice", "guidance", "form", "evidence",
        }:
            raise ValueError("invalid document type")
        if label == "PolicyDocument" and "status" in node and node["status"] not in {
            "current", "historical_snapshot", "superseded", "verify_current_status",
        }:
            raise ValueError("invalid document status")
        if label == "Actor" and "source_url" in node and not _url(node["source_url"]):
            raise ValueError("actor source URL required")
        if label == "PolicySection" and not _url(node["source_url"]):
            raise ValueError("section source URL required")
        if label == "Jurisdiction" and node["level"] not in {"federal", "state", "local"}:
            raise ValueError("invalid jurisdiction level")
        if label == "Actor" and node["type"] not in {"official", "lobbyist", "organization"}:
            raise ValueError("invalid actor type")
        if label == "RedlineProposal":
            savings = node["estimated_annual_savings"]
            if savings is not None and (
                isinstance(savings, bool) or not isinstance(savings, (int, float))
                or not math.isfinite(savings) or savings < 0
            ):
                raise ValueError("savings must be a nonnegative number or null")
        if label == "PolicyDocument" and not _url(node["source_url"]):
            raise ValueError("document requires a source URL")
        if label == "PolicyDocument" and "publication_date" in node:
            try:
                date.fromisoformat(node["publication_date"])
            except ValueError as exc:
                raise ValueError("publication date must be ISO YYYY-MM-DD") from exc
        by_id[node_id] = node

    seen = set()
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("type") not in RELATIONSHIPS:
            raise ValueError("unknown relationship type")
        kind, src, dst = edge["type"], edge.get("src"), edge.get("dst")
        expected = {"type", "src", "dst"}
        if kind in SOURCED_RELATIONSHIPS:
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
        if kind == "ADMINISTERS" and actor_type != "organization":
            raise ValueError("only an organization can administer a document")
        if kind == "WORKS_FOR" and (
            actor_type != "official" or by_id[dst]["type"] != "organization"
        ):
            raise ValueError("only officials can work for an organization")
        if kind in SOURCED_RELATIONSHIPS and not _url(edge["source_url"]):
            raise ValueError("sourced relationships require a supporting URL")
        if kind == "CITES" and src == dst:
            raise ValueError("a document cannot cite itself")
        if kind == "NEXT_SECTION" and (
            by_id[dst]["order"] != by_id[src]["order"] + 1
            or by_id[dst]["citation"].split(" / passage ")[0]
            != by_id[src]["citation"].split(" / passage ")[0]
        ):
            raise ValueError("section order or parent does not match")
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
            rows = [{field: node.get(field) for field in fields}
                    for node in fixture["nodes"] if node["label"] == label]
            if rows:
                assignments = ", ".join(
                    f"n.{field} = row.{field}" for field in fields if field != "id"
                )
                chunk_size = 1 if label == "PolicyDocument" else 25
                for start in range(0, len(rows), chunk_size):
                    self.query(
                        f"UNWIND $rows AS row MERGE (n:{label} {{id: row.id}}) SET {assignments}",
                        {"rows": rows[start:start + chunk_size]},
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
            if kind in SOURCED_RELATIONSHIPS:
                cypher += " SET r.source_url = row.source_url"
            for start in range(0, len(rows), 50):
                self.query(cypher, {"rows": rows[start:start + 50]})

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

    def section_context(self, section_id):
        """Read a passage with its parent document and immediate neighbors."""
        rows = self.query(
            "MATCH (d:PolicyDocument)-[:HAS_SECTION]->(s:PolicySection {id: $id}) "
            "RETURN d.id AS document_id, d.title AS document_title, "
            "d.document_type AS document_type, d.status AS document_status, "
            "d.source_url AS document_url, s.id AS id, s.citation AS citation, "
            "s.text AS text, s.order AS section_order",
            {"id": section_id},
        )
        if not rows:
            return None
        previous = self.query(
            "MATCH (p:PolicySection)-[:NEXT_SECTION]->(s:PolicySection {id: $id}) "
            "RETURN p.id AS id, p.text AS text", {"id": section_id},
        )
        following = self.query(
            "MATCH (s:PolicySection {id: $id})-[:NEXT_SECTION]->(n:PolicySection) "
            "RETURN n.id AS id, n.text AS text", {"id": section_id},
        )
        return {"section": rows[0], "previous": previous, "next": following}

    def policy_contacts(self, document_id):
        """Return sourced administering organizations and their relevant officeholders."""
        return self.query(
            "MATCH (agency:Actor)-[r:ADMINISTERS]->(d:PolicyDocument {id: $id}) "
            "OPTIONAL MATCH (official:Actor)-[:WORKS_FOR]->(agency) "
            "RETURN agency.id AS agency_id, agency.name AS agency_name, "
            "r.source_url AS administration_source, official.id AS official_id, "
            "official.name AS official_name, official.role AS role, "
            "official.source_url AS role_source, official.public_contact AS public_contact",
            {"id": document_id},
        )
