# DOGE Factory housing policy graph

This Python module stores a small, directed housing-policy graph in **HydraDB hosted BYOG**. It models jurisdictions, full-text policy documents, actors, findings and proposed redlines. It does not infer lobbying or legal authority: each such edge requires a supplied public source URL. The included data is entirely fictional; `example.org` URLs illustrate the format and **are not actual public filings or authority citations**. Replace them with verified sources before importing real-world data.

## Setup and database

Requires Python 3.10+ and a HydraDB hosted BYOG database. No Python dependencies are needed.

1. Obtain an API key from HydraDB and create a graph database via `POST https://api.hydradb.com/byog/databases` (see [BYOG instructions](https://docs.hydradb.com/essentials/v2/bring-your-own-graph)). Hosted HydraDB runs the database; no local Docker process is required. You can check availability with `GET /byog/collections?database=YOUR_DATABASE`.
2. Set `HYDRADB_API_KEY` and `HYDRADB_DATABASE_ID` in the shell. Optionally set `HYDRADB_COLLECTION` (defaults to `doge_housing`) and `HYDRADB_BASE_URL` (defaults to `https://api.hydradb.com`). Do not commit credentials.
3. From the repository root, import the fixture:

   ```sh
   python3 -m housing_graph
   ```

   Importing it again updates node properties and disclosure URLs without multiplying nodes or edges. IDs are stable, unique application-owned string properties; do not use HydraDB's internal node IDs as business IDs.

To read the graph from a document in Python:

```python
from housing_graph import HousingGraph

graph = HousingGraph.from_env()
context = graph.document_context("fictional:doc:bayhaven")
print(context)  # document, jurisdictions, findings with proposals, officials, lobbying
```

The importer validates all nodes and directed edges **before** sending any writes. It writes nodes first, then relationships using `MERGE` on the source and destination IDs. Hosted BYOG writes are auto-committed per query, not atomic across an entire fixture; a failed import can be rerun safely. For large imports, split into smaller parameter batches to stay under the hosted 256 KiB request body and 30-second write limits. Use a dedicated collection for each graph.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

This runs local input-validation tests. To run the **real HydraDB integration tests**, provide a valid API key and an existing **dedicated test database**:

```sh
export HYDRADB_TEST_DATABASE=your-test-database
export HYDRADB_API_KEY=your-valid-key
python3 -m unittest discover -s tests -v
```

Integration tests create and delete only a randomly named `housing_test_...` collection in that database; they verify Cypher read/write behavior and reimport counts. They are skipped if either variable is missing, and fail (not pass) when authentication or HydraDB queries fail. Never point the tests at a collection containing other data.

## HydraDB dialect

This integration targets **hosted BYOG** (`POST /byog/query`, `database`, `collection`, `params`, and `data` rows), not the differently shaped self-hosted graph-node API. Hosted BYOG's documented `MERGE (n:Label {id: ...}) SET ...` and `MATCH ... MERGE (a)-[r:TYPE]->(b) SET ...` allow repeatable imports. Relationship types are fixed in code, never interpolated from user input. Its server-managed numeric node ID is not stable across export/import, so the `id` property is a string key. The self-hosted server instead treats numeric `id` as vertex identity and restricts single-statement writes to one-hop edge patterns; those rules **do not apply to this client**. The original fixture has no SQL foreign keys, sections, published versions, government bodies or separate filing nodes; the HUD EIV pilot below adds source-backed passages to meet its retrieval requirements.

## HUD EIV research pilot

See the [pilot specification](hud-eiv-policy-graph-spec.md) for the graph contract, source and evidence rules, read behavior, and known gaps.

The HUD EIV pilot extends the initial small graph with `PolicySection` passages, document provenance (`citation`, `document_type`, `issuing_agency`, `publication_date`, `status`, `topics`), and sourced `HAS_SECTION`, `NEXT_SECTION`, `CITES`, `ADMINISTERS`, and `WORKS_FOR` links. This **does not rewrite** the earlier fictional fixture. These additional records support passage-level retrieval and distinguish an agency's administering role from an individual's authority to change a rule. Passages are source-ordered portions of the original full-text document, and status is metadata.

From the repository root, set a valid `HYDRADB_API_KEY` and `HYDRADB_DATABASE_ID=doge-factory` **in the shell** (the module does not load `.env` automatically). With the provided Desktop actor roster, import the pilot to its **dedicated** graph collection:

```sh
uv run --with pypdf --with fonttools python3 -m housing_graph.hud_eiv \
  --roster "$HOME/Desktop/HUD-EIV-Actor-Roster.csv" \
  --collection hud_eiv_pilot
```

The importer downloads and validates five 2025 CFR sections as official govinfo XML and the complete HUD Notice PIH 2018-18 PDF. It also checks the HUD principal directory and EIV team sheet against the roster. These are fetched anew at import time; hashes of the downloaded sources are printed for an audit trail. It upserts by stable IDs, and is safe to rerun. Do not import the research source pack as though it were regulation text.

The pilot currently includes five **historical 2025 CFR edition** regulations (separate HCV, public-housing, and project-based Section 8 tracks), one HUD notice whose current status still requires confirmation, 119 ordered passages, 19 actors (HUD and HUD personnel cross-checked against official sources), one quoted potential finding and a draft redline with **null** estimated savings. Historical EIV team-sheet roles are marked unverified for current assignment. It intentionally does not link historical lobbyists to the notice, attribute individual amendment authority from a job title, include unverified congressional/PHA records, or imply IRS/EIV tenant data is accessible. Congress, local PHA plans and LIHTC law require separate verified source work; no Iowa or nationwide state-comparison coverage is claimed. Before action, verify current versions and program-specific applicability with counsel.

Query a passage with context, or see the administering agency and sourced contact roles:

```python
graph = HousingGraph.from_env()  # set HYDRADB_COLLECTION=hud_eiv_pilot
graph.section_context("hud-eiv:cfr-2025:24:5.233:passage:001")
graph.policy_contacts("hud-eiv:notice:pih-2018-18")
```

To run the pilot's real-instance regression test on the already populated collection:

```sh
export HYDRADB_HUD_EIV_INTEGRATION=1
export HYDRADB_HUD_EIV_ROSTER="$HOME/Desktop/HUD-EIV-Actor-Roster.csv"
export HYDRADB_HUD_EIV_COLLECTION=hud_eiv_pilot
python3 -m unittest discover -s tests -v
```

The test reimports the reviewed pilot and checks stable counts and navigable results. It does not drop the pilot collection.
