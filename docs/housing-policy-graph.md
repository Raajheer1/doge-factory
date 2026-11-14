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

This integration targets **hosted BYOG** (`POST /byog/query`, `database`, `collection`, `params`, and `data` rows), not the differently shaped self-hosted graph-node API. Hosted BYOG's documented `MERGE (n:Label {id: ...}) SET ...` and `MATCH ... MERGE (a)-[r:TYPE]->(b) SET ...` allow repeatable imports. Relationship types are fixed in code, never interpolated from user input. Its server-managed numeric node ID is not stable across export/import, so the `id` property is a string key. The self-hosted server instead treats numeric `id` as vertex identity and restricts single-statement writes to one-hop edge patterns; those rules **do not apply to this client**. No SQL foreign keys, sections, published versions, government bodies or separate filing nodes are created.
