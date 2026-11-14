"""Sourced HUD EIV pilot in a dedicated HydraDB BYOG collection.

Input is a reviewed manifest of official source URLs, not the research notes or
actor CSV themselves. PDF extraction requires pypdf; CFR sections use govinfo XML.
"""

import csv
import hashlib
import io
import json
import os
import re
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib import request
from xml.etree import ElementTree

from .graph import HousingGraph, validate_fixture


SOURCES = (
    ("5.233", "1", "income verification,public housing,HCV,project-based Section 8"),
    ("5.236", "1", "income verification,tenant protections"),
    ("5.659", "1", "project-based Section 8,owner verification"),
    ("982.516", "4", "HCV,annual reexamination"),
    ("960.259", "4", "public housing,reexamination"),
)
NOTICE_URL = "https://www.hud.gov/sites/dfiles/OCHCO/documents/18-18pihn.pdf"
DIRECTORY_URL = "https://www.hud.gov/contactus/principal-directory"
TEAM_URL = "https://www.hud.gov/sites/dfiles/PIH/documents/EIV%20TEAM%20CONTACTS.pdf"
NOTICE_ID = "hud-eiv:notice:pih-2018-18"
JURISDICTION_ID = "hud-eiv:jurisdiction:us"
HUD_ID = "hud-eiv:actor:hud"


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, text):
        self.parts.append(text)


def _download(url):
    req = request.Request(url, headers={"User-Agent": "DOGE-Factory-policy-research/1.0"})
    with request.urlopen(req, timeout=45) as response:
        return response.read()


def _clean(text):
    return re.sub(r"\s+", " ", text).strip()


def _directory_names(data):
    parser = TextOnly()
    parser.feed(data.decode("utf-8", errors="replace"))
    return _clean(" ".join(parser.parts))


def _section_xml(data, citation, expected_date=None):
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError(f"invalid official section XML for {citation}") from exc
    if expected_date and root.findtext("./FDSYS/DATE") != expected_date:
        raise ValueError(f"unexpected CFR edition date for {citation}")
    section = root.find(".//SECTION")
    if section is None or not re.search(
        rf"(?<![\d.]){re.escape(citation)}(?![\d.])", _clean(section.findtext("SECTNO") or "")
    ):
        raise ValueError(f"official source did not contain section {citation}")
    paragraphs = [_clean("".join(child.itertext())) for child in section if child.tag == "P"]
    paragraphs = [text for text in paragraphs if text]
    if not paragraphs:
        raise ValueError(f"empty section {citation}")
    return section.findtext("SUBJECT"), paragraphs


def _notice_pages(data):
    if not data.startswith(b"%PDF"):
        raise ValueError("HUD notice was not a PDF")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install PDF extraction support: uv run --with pypdf --with fonttools ...") from exc
    return [(page.extract_text() or "").strip() for page in PdfReader(io.BytesIO(data)).pages]


def _node(label, node_id, **properties):
    return {"label": label, "id": node_id, **properties}


def _edge(kind, src, dst, **properties):
    return {"type": kind, "src": src, "dst": dst, **properties}


def build_hud_pilot(roster_path=None, download=None):
    """Return a validated, deterministic import from official sources and a reviewed roster."""
    if download is None:
        download = _download
    nodes = [_node("Jurisdiction", JURISDICTION_ID, name="United States", level="federal")]
    edges = []
    sources = {}
    for citation, volume, topics in SOURCES:
        url = (f"https://www.govinfo.gov/content/pkg/CFR-2025-title24-vol{volume}/xml/"
               f"CFR-2025-title24-vol{volume}-sec{citation.replace('.', '-')}.xml")
        raw = download(url)
        title, paragraphs = _section_xml(raw, citation, expected_date="2025-04-01")
        doc_id = f"hud-eiv:cfr-2025:24:{citation}"
        full_text = f"24 CFR § {citation} — {title}\n\n" + "\n".join(paragraphs)
        nodes.append(_node("PolicyDocument", doc_id, title=f"24 CFR § {citation} — {title}",
                           text=full_text, source_url=url, citation=f"24 CFR § {citation}",
                           document_type="regulation", issuing_agency="HUD",
                           publication_date="2025-04-01", status="historical_snapshot",
                           topics=topics))
        sources[doc_id] = hashlib.sha256(raw).hexdigest()
        edges.append(_edge("ISSUED", JURISDICTION_ID, doc_id))
        # Full text stays on the document; ordered passages provide local context.
        for i, paragraph in enumerate(paragraphs, 1):
            passage_id = f"{doc_id}:passage:{i:03d}"
            nodes.append(_node("PolicySection", passage_id, title=f"§ {citation}, passage {i}",
                               text=paragraph, citation=f"24 CFR § {citation} / passage {i}",
                               order=i, source_url=url))
            edges.append(_edge("HAS_SECTION", doc_id, passage_id))
            if i > 1:
                edges.append(_edge("NEXT_SECTION", f"{doc_id}:passage:{i - 1:03d}", passage_id))

    notice_bytes = download(NOTICE_URL)
    pages = _notice_pages(notice_bytes)
    notice = "\n\n".join(pages).strip()
    if (len(notice) < 10000 or "Notice PIH 2018-18" not in notice
            or "Issued: October 26, 2018" not in notice):
        raise ValueError("unexpected HUD notice text")
    sources[NOTICE_ID] = hashlib.sha256(notice_bytes).hexdigest()
    nodes.append(_node("PolicyDocument", NOTICE_ID,
                       title="HUD Notice PIH 2018-18 — Administrative Guidance for Effective and Mandated Use of EIV",
                       text=notice, source_url=NOTICE_URL, citation="Notice PIH 2018-18",
                       document_type="notice", issuing_agency="HUD/PIH",
                       publication_date="2018-10-26", status="verify_current_status",
                       topics="public housing,HCV,PBV,EIV,income verification"))
    edges.append(_edge("ISSUED", JURISDICTION_ID, NOTICE_ID))
    # Notice page chunks are navigable; the document retains the exact extracted text.
    for i, page in enumerate(pages, 1):
        sid = f"{NOTICE_ID}:passage:{i:03d}"
        nodes.append(_node("PolicySection", sid, title=f"PIH 2018-18, page {i}",
                           text=page, citation=f"PIH 2018-18 / passage {i}",
                           order=i, source_url=NOTICE_URL))
        edges.append(_edge("HAS_SECTION", NOTICE_ID, sid))
        if i > 1:
            edges.append(_edge("NEXT_SECTION", f"{NOTICE_ID}:passage:{i - 1:03d}", sid))

    cfr_id = "hud-eiv:cfr-2025:24:5.233"
    protection_id = "hud-eiv:cfr-2025:24:5.236"
    cfr_source = next(node["source_url"] for node in nodes if node["id"] == cfr_id)
    edges.extend([
        _edge("CITES", NOTICE_ID, cfr_id, source_url=NOTICE_URL),
        _edge("CITES", cfr_id, protection_id, source_url=cfr_source),
    ])
    quote = ("The PHA is required to obtain at a minimum, two current and consecutive pay stubs "
             "for determining annual income from wages.")
    if quote not in _clean(notice):
        raise ValueError("finding quote not found in source notice")
    finding_id = "hud-eiv:finding:pih-wage-docs"
    proposal_id = "hud-eiv:proposal:auditable-electronic-evidence"
    nodes.extend([
        _node("PolicyFinding", finding_id,
              description="Assess whether approved electronic wage evidence could satisfy routine PHA verification while preserving EIV, documentation and exceptions.",
              evidence_quote=quote),
        _node("RedlineProposal", proposal_id,
              proposed_text="Draft a narrowly scoped allowance for approved, auditable electronic evidence in routine wage recertification; preserve EIV use, consent, exception handling, tenant correction rights, and existing data-sharing limits.",
              estimated_annual_savings=None),
    ])
    edges.extend([
        _edge("HAS_FINDING", NOTICE_ID, finding_id),
        _edge("ADDRESSED_BY", finding_id, proposal_id),
        _edge("PROPOSES_CHANGE_TO", proposal_id, NOTICE_ID),
    ])
    nodes.append(_node("Actor", HUD_ID, name="U.S. Department of Housing and Urban Development",
                       type="organization", role="Federal housing agency", organization="HUD",
                       source_url=DIRECTORY_URL, verified_at="2026-11-14", public_contact=""))
    edges.append(_edge("ADMINISTERS", HUD_ID, NOTICE_ID, source_url=NOTICE_URL))

    if roster_path:
        directory_bytes = download(DIRECTORY_URL)
        directory = _directory_names(directory_bytes)
        if len(directory) < 1000 or "Principal Directory" not in directory:
            raise ValueError("HUD principal directory could not be verified")
        team_pdf = download(TEAM_URL)
        if not team_pdf.startswith(b"%PDF"):
            raise ValueError("HUD EIV team contact source is not a PDF")
        team_text = _clean("\n".join(_notice_pages(team_pdf))).casefold()
        sources[DIRECTORY_URL] = hashlib.sha256(directory_bytes).hexdigest()
        sources[TEAM_URL] = hashlib.sha256(team_pdf).hexdigest()
        with Path(roster_path).open(newline="", encoding="utf-8-sig") as file:
            roster = list(csv.DictReader(file))
        for row in roster:
            # Only official HUD records independently checked against an agency source.
            if row["organization"] not in {"HUD", "HUD REAC EIV"}:
                continue
            if row["organization"] == "HUD":
                position = directory.find(row["name"])
                if position < 0 or row["role"].casefold().split(",")[0] not in (
                    directory[position:position + 190].casefold()
                ):
                    continue
            elif row["name"].casefold() not in team_text:
                continue
            source_url = DIRECTORY_URL if row["organization"] == "HUD" else TEAM_URL
            actor_id = "hud-eiv:actor:" + re.sub(r"[^a-z0-9]+", "-", row["name"].lower()).strip("-")
            nodes.append(_node("Actor", actor_id, name=row["name"], type=row["actor_type"],
                               role=row["role"], organization=row["organization"],
                               source_url=source_url, verified_at=row["source_date_or_status"],
                               public_contact=row["public_email"] or row["public_phone"]))
            # The directory supports HUD employment context, not individual authority to
            # amend the 2018 notice. Congressional roles are not HUD authority.
            if row["actor_type"] == "official" and row["organization"] == "HUD":
                edges.append(_edge("HOLDS_OFFICE_IN", actor_id, JURISDICTION_ID))
                edges.append(_edge("WORKS_FOR", actor_id, HUD_ID, source_url=DIRECTORY_URL))
    fixture = validate_fixture({"nodes": nodes, "relationships": edges})
    return fixture, sources


def import_hud_pilot(graph, roster_path):
    fixture, hashes = build_hud_pilot(roster_path)
    graph.import_fixture(fixture)
    return fixture, hashes


def main():
    parser = argparse.ArgumentParser(description="Import the verified HUD EIV pilot to HydraDB")
    parser.add_argument("--roster", type=Path, required=True,
                        help="Path to HUD-EIV-Actor-Roster.csv; only independently verified HUD rows are loaded")
    parser.add_argument("--collection", default="hud_eiv_pilot")
    args = parser.parse_args()
    graph = HousingGraph(
        os.environ["HYDRADB_DATABASE_ID"], args.collection, os.environ["HYDRADB_API_KEY"],
        os.getenv("HYDRADB_BASE_URL", "https://api.hydradb.com"),
    )
    fixture, hashes = import_hud_pilot(graph, args.roster)
    print(json.dumps({
        "database": graph.database, "collection": graph.collection,
        "nodes": len(fixture["nodes"]), "relationships": len(fixture["relationships"]),
        "source_sha256": hashes,
    }, indent=2))


if __name__ == "__main__":
    main()
