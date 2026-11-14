# HUD EIV policy graph: pilot specification

**Status:** implemented pilot in PR #4. This describes the code and imported
records, not a claim that the dataset covers all affordable-housing policy.
Operational setup is in [the housing graph guide](housing-policy-graph.md).

## Purpose and boundary

Support source-traceable review of the federal HUD Enterprise Income
Verification (EIV) requirements: retrieve full policy text and nearby passages,
connect a documented potential bottleneck to a reviewable proposal, and identify
the administering organization without inventing lobbying or amendment authority.
The graph lives in hosted HydraDB BYOG, database `doge-factory`, collection
`hud_eiv_pilot`. The fictional housing fixture uses a separate collection.
No tenant-level EIV, tax, paystub, SSN, or other eligibility records belong here.

## Graph contract

Application-owned string `id` is unique across all node labels **within a
collection**; HydraDB's numeric internal ID is not a business key. The importer
validates the whole input before writing. Labels and relationship types are
fixed in code (`housing_graph/graph.py`), not provided as Cypher parameters.

| Node label | Fields | Semantics |
| --- | --- | --- |
| `Jurisdiction` | `id`, `name`, `level` (`federal`, `state`, `local`) | Issuing legal jurisdiction, not an agency or committee. |
| `PolicyDocument` | `id`, `title`, **full** `text`, `source_url`; optional `citation`, `document_type`, `issuing_agency`, `publication_date`, `status`, `topics` | An official source. Types accepted by the application: `statute`, `regulation`, `notice`, `guidance`, `form`, `evidence`. Statuses: `current`, `historical_snapshot`, `superseded`, `verify_current_status`. A date records the source edition/publication, **not necessarily its effective date**. Topics are a comma-separated string, not an enumerated taxonomy. |
| `PolicySection` | `id`, `title`, `text`, `citation`, positive `order`, `source_url` | An ordered retrieval passage within a document; the CFR pilot uses XML paragraphs, the notice uses PDF pages. A passage is **not** asserted to be a distinct legal section. |
| `Actor` | `id`, `name`, `type` (`official`, `lobbyist`, `organization`); optional `role`, `organization`, `source_url`, `verified_at`, `public_contact` | Public role metadata; `verified_at` is a source date/status string, **not** a guarantee of current employment. |
| `PolicyFinding` | `id`, `description`, `evidence_quote` | A reviewable interpretation tied to its source document. |
| `RedlineProposal` | `id`, `proposed_text`, `estimated_annual_savings` | Draft, not adopted text; savings is a nonnegative number or `null` when unmeasured. |

Directed edges (the application checks endpoint labels and role constraints):

| Pattern | Meaning / evidence rule |
| --- | --- |
| `Jurisdiction-[:ISSUED]->PolicyDocument` | Jurisdiction of the source. |
| `Actor(official)-[:HOLDS_OFFICE_IN]->Jurisdiction` | Jurisdiction for a sourced public role; does **not** imply power to amend a policy. |
| `Actor(lobbyist)-[:REPRESENTS]->Actor(organization)` | Lobbyist/client connection. |
| `Actor(lobbyist)-[:LOBBIED_ON {source_url}]->PolicyDocument` | Only with a public filing supporting lobbying on **that document**. |
| `Actor(official)-[:HAS_AUTHORITY_OVER {source_url}]->PolicyDocument` | Only with a source establishing **that official's** authority. |
| `PolicyDocument-[:HAS_FINDING]->PolicyFinding` | Finding tied to source text; evidence quote is on the finding. |
| `PolicyFinding-[:ADDRESSED_BY]->RedlineProposal` | Proposed remedy. |
| `RedlineProposal-[:PROPOSES_CHANGE_TO]->PolicyDocument` | Target of the draft change. |
| `PolicyDocument-[:HAS_SECTION]->PolicySection` | Parent-to-passage retrieval. |
| `PolicySection-[:NEXT_SECTION]->PolicySection` | Consecutive passages in the same cited document. |
| `PolicyDocument-[:CITES {source_url}]->PolicyDocument` | Source-backed cross-reference. |
| `Actor(organization)-[:ADMINISTERS {source_url}]->PolicyDocument` | Agency administers a source; **not** individual amendment authority. |
| `Actor(official)-[:WORKS_FOR {source_url}]->Actor(organization)` | Sourced agency affiliation; **not** authority over a document. |

The last five edges and `PolicySection` extend the earlier minimal housing
fixture for this pilot. No government-body, published-version, or
lobbying-filing node is introduced. A URL's shape is validated; **the
application does not prove the URL's content supports a manually supplied
relationship**. Importers must verify that claim before writing.

## Sources and import rules

`housing_graph/hud_eiv.py` downloads source material before writing:

| Record | Official source | Stored status |
| --- | --- | --- |
| 24 CFR §§ 5.233, 5.236, 5.659 | [2025 govinfo CFR XML, title 24 volume 1](https://www.govinfo.gov/content/pkg/CFR-2025-title24-vol1/) | `historical_snapshot` |
| 24 CFR §§ 960.259, 982.516 | [2025 govinfo CFR XML, title 24 volume 4](https://www.govinfo.gov/content/pkg/CFR-2025-title24-vol4/) | `historical_snapshot` |
| HUD Notice PIH 2018-18 | [HUD PDF](https://www.hud.gov/sites/dfiles/OCHCO/documents/18-18pihn.pdf) | `verify_current_status` |
| Public actor leads | [HUD principal directory](https://www.hud.gov/contactus/principal-directory), [HUD EIV team sheet](https://www.hud.gov/sites/dfiles/PIH/documents/EIV%20TEAM%20CONTACTS.pdf), and the separately provided actor CSV | Only HUD directory/team matches included; older EIV team roles remain unverified as *current*. |

The CSV and Desktop research notes are **leads, not official policy texts**.
The importer checks the CFR edition date/citation, the notice's identifier/date
and a literal finding quote, and cross-checks selected HUD roster names against
the official directory/team sheet. It prints SHA-256 hashes for downloaded
sources. This is a snapshot; re-importing fetches live files again, so hashes
may change. Current-law status must be verified before legal or outreach use.

Stable IDs encode the source and edition (for example,
`hud-eiv:cfr-2025:24:5.233` and
`hud-eiv:cfr-2025:24:5.233:passage:001`). The full extracted text remains
on each `PolicyDocument`; passage IDs and `NEXT_SECTION` support context
retrieval. Import node labels first, then typed relationships, using `MERGE`
and parameterized values. Reruns update properties without adding duplicate
nodes/edges. Hosted BYOG auto-commits each query: an import is **not** one
transaction; rerun after a partial failure. Documents are written individually,
other nodes and edges in bounded batches.

## Read behavior and acceptance checks

* `document_context(document_id)` returns the document, issuing jurisdiction,
  findings with proposals, and **only explicitly evidenced**
  `HAS_AUTHORITY_OVER` / `LOBBIED_ON` connections.
* `section_context(section_id)` returns a passage, its document and immediate
  previous/next passages, or `None` when absent.
* `policy_contacts(document_id)` returns an administering organization and
  sourced `WORKS_FOR` role data. A result is a research contact lead, **not**
  a determination of amendment power or an endorsement.
* The pilot currently has **147 nodes** (1 jurisdiction, 6 documents, 119
  passages, 19 actors, 1 finding, 1 proposal) and **264 edges**. Its
  `LOBBIED_ON` and `HAS_AUTHORITY_OVER` counts are **zero**. Historical
  housing-related filings do not establish lobbying on this notice/redline.
* Validation rejects unknown enum values, mismatched edges, duplicate IDs
  and edge triples, bad source URLs, unsupported section order and invalid
  savings. The opted-in real HydraDB regression test checks traversal,
  counts and idempotent re-import. See the [run instructions](housing-policy-graph.md#hud-eiv-research-pilot).

## Not yet supported

This is **not** an Iowa or 50-state corpus; it cannot support claims such as
"49 states do this differently." It does not yet provide actual form text and
instructions, statute/form change-process mappings, comprehensive definition/
exception links, program-specific local PHA plans, measured outcomes, verified
current notice status, individual legal amendment authority, legislative
committee routes, advocacy contacts, or a defensible fiscal model. Add those
only from reviewed primary sources, with coverage and applicability tracked;
do not infer effectiveness from differing legal wording or treat all HCV
administrative fees as income-verification savings.
