# HydraDB housing and healthcare corpus

## Architecture

The hosted HydraDB BYOG API stores explicit nodes and relationships and executes Cypher. It is not the self-hosted graph-node HTTP API: BYOG uses `/byog/query`, the database name, a collection name, and a bearer API key. The Rust [HydraDB repository](https://github.com/hydra-db/hydradb) describes the underlying engine; the [hosted BYOG guide](https://docs.hydradb.com/essentials/v2/bring-your-own-graph) documents this API. HydraDB also describes a separate [knowledge and retrieval layer](https://docs.hydradb.com/index). A node written to BYOG should not be assumed to have been indexed into that layer: its ingestion, retrieval, availability, pricing, and cross-collection behavior require separate verification.

Use the existing `doge-factory` database with independent `housing` and `healthcare` graph collections. Collections are isolated; a query spanning both domains must query both and merge results in the application. The earlier `hud_eiv_pilot` remains untouched. Sources can legitimately apply to both collections; retain provenance and deduplicate results by source ID and edition in the application.

Each collection holds:

- `Jurisdiction`: stable ID, name, federal/state/local level.
- `PolicyDocument`: application-owned ID, title, source text, citation, type, issuing body, source URL, topics, source snapshot, checksum, and status. A source split for API limits has multiple document nodes with ordered part numbers in their IDs/titles; concatenate parts when the entire source is needed. A source snapshot date is not its effective date.
- `PolicySection`: ordered source passage, parent citation, text, URL and stable ID. A passage is a source fragment, not necessarily a legal section. PDF passages are pages; US Code passages are extracted statutory paragraphs; eCFR passages preserve XML child ordering. Verify extraction and context before relying on any quotation.
- `ISSUED`, `HAS_SECTION`, and `NEXT_SECTION` relationships connect jurisdiction, documents and adjacent passages. The jurisdiction is the issuing jurisdiction; it does not by itself determine geographic or program applicability.
- The existing graph model can also represent source-backed agencies, officials, authority and lobbying links. The new importers do not populate those actors or infer authority, comparisons, outcomes, or contacts.

The ingestion workers create dated snapshots. eCFR `verify_current_status` and US Code `historical_snapshot` intentionally require verification before legal use; QAP status also needs verification. A fresh snapshot creates new IDs, so retrieval must select an appropriate edition rather than treating all versions as current. PDF text is machine-extracted and tables and reading order may be imperfect; cite and verify the underlying source. US Code import currently stores statutory body paragraphs, not editorial notes or all ancillary material.

## Sources and coverage

- Housing: selected Title 24 eCFR parts covering HOME, housing assistance and related regulations; selected federal statutes including 26 USC 42 and 42 USC 1437f; reviewed official Iowa, California, Texas, and New York allocation-plan PDFs.
- Healthcare: selected Title 42 and Title 45 eCFR parts covering Medicaid, Medicare, privacy and health IT; selected federal healthcare statutes; selected official Iowa Medicaid state plan documents.
- The eCFR import date comes from the source's `up_to_date_as_of` metadata. Source URLs refer to that point-in-time edition. The U.S. Code importer uses the explicitly identified 119-120 edition, not an assertion that it is the latest edition.
- This is not a nationwide state/local corpus or a complete federal corpus. Expand with official state codes, state LIHTC QAPs, Medicaid plans, local housing programs, official contact information, and applicability and comparison links. Preserve issuing agency and source version; do not treat agency guidance or program summaries as statutes. Track missing and failed sources rather than claiming coverage.

## Operation

Set `HYDRADB_API_KEY` and optionally `HYDRADB_DATABASE_ID` (defaults to `doge-factory`) and `HYDRADB_BASE_URL` in the environment. Do not commit credentials. Commands:

```sh
python3 -m housing_graph.ecfr_import --domain housing
python3 -m housing_graph.ecfr_import --domain healthcare
python3 -m housing_graph.usc_import --domain housing
python3 -m housing_graph.usc_import --domain healthcare
# Install pypdf in your Python environment for PDF extraction first.
python3 -m housing_graph.qap_import
python3 -m housing_graph.qap_import --domain healthcare
```

For a focused rerun, `ecfr_import --domain housing --parts 24:92,24:982` limits the manifest. Each command prints successful sources and errors. A particular dated snapshot has stable IDs and `MERGE`-based upserts; rerunning repairs interrupted writes, but imports are not atomic and stale nodes from changed segmentation need reconciliation. No command drops a collection. Avoid running multiple imports of the same source concurrently. Before reusing imported data, reconcile source and passage counts and inspect representative excerpts against originals.

`usc_import --domain healthcare --sections 42:1396a,42:1396d` limits a statute rerun to entries in the domain manifest.

### Import notes, 2026-11-14

The Ohio 2026–2027 9% QAP technical amendment, New Jersey 2026 QAP, and Pennsylvania 2025–2026 and 2027–2028 QAPs were imported. Massachusetts returned HTTP 403 and the Washington PDF URL returned 404; their manifest entries are retained for investigation, not as claims of coverage.

An additional healthcare eCFR run reported 519 documents and 8,714 passages successfully imported across 42 CFR parts 460, 489, 494 and 498 and 45 CFR parts 156, 160, 164, 170, 171 and 180. A subsequent run reported 2,674 documents and 55,303 passages across 42 CFR parts 405, 410–416, 418–420, 422–425, 488, 493, 495 and 512 and 45 CFR part 155; this recovered the previous timeouts for 488, 493, 495, 512 and 155. Counts are per-run reports, not independently verified live collection totals. Parts 42:490 and 42:518 returned 404; 42:1001 exceeded the current request size limit. The healthcare statute run reported 11 sections successful; focused retries recovered 42 USC 1395, 1396a and 1396d. The earlier housing timeout for 24 CFR part 960 was also recovered (32 documents, 496 passages). Reconcile records before relying on coverage: writes are not atomic, and completion reports have not been checked against source and collection counts.

## Application integration still required

The Go API currently targets a different HydraDB endpoint and `Provision` label, not these BYOG collections. Add a hosted BYOG reader that selects relevant collections, filters and ranks by topic and jurisdiction, follows passage and source links, supplies the text and provenance to the model, and returns explicit coverage and missing-context information. Related federal/state law and cross-state comparisons require explicit data and retrieval; don't infer 50-state coverage from a partial set. Review citations, version and authority before generating outreach. Outbound calls remain the responsibility of the calling integration.
