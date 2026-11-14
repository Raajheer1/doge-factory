# Research and source plan

Last reviewed: 2026-11-13. These are starting points for data acquisition and system controls, not legal advice or an endorsement of a provider.

## Authoritative or primary-source inputs

| Need | Source | How DOGE Factory should use it |
| --- | --- | --- |
| Federal statutes | [U.S. Code downloads](https://uscode.house.gov/download.html) | Prefer the published machine-readable release and retain release-point metadata. |
| Federal legislative activity | [Congress.gov API](https://api.congress.gov/) | Retrieve bill, member, and legislative-action data; an API key is required. |
| Federal regulations | [eCFR API](https://www.ecfr.gov/developers/documentation/api/v1) | Retrieve current regulatory content and metadata; distinguish regulations from statutes. |
| Government publications and bulk data | [GovInfo Developer Hub](https://www.govinfo.gov/developers) | Use official API/bulk sources where available; API access uses an API.data.gov key. |
| State legislative activity | [OpenStates API](https://docs.openstates.org/api-v3/) | Use for discovery and standardized legislative metadata; verify legal text against the jurisdiction’s official publisher. |
| Legislative markup | [USLM schema](https://github.com/usgpo/uslm) | Preserve structural markup and citation hierarchy instead of flattening legal documents into plain text. |

## Data-source policy

1. Prefer the issuing government body or its designated publisher.
2. Treat aggregators as a discovery or convenience layer, never the sole authority for a proposed change.
3. Capture source URL, publisher, retrieval timestamp, document version/effective date, checksum, and applicable access terms.
4. Keep source snapshots immutable so a reviewer can reproduce an analysis.
5. Do not bypass rate limits, authentication, robots controls, or terms of use.

## AI risk controls

The [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) organizes AI risk work around **Govern, Map, Measure, and Manage**. For this product:

| NIST function | Product control |
| --- | --- |
| Govern | Named owners, approval roles, an audit log, and documented use limits. |
| Map | Define jurisdiction, users, affected populations, policy domain, and harms before analysis. |
| Measure | Test citation accuracy, unsupported-claim rate, retrieval coverage, and reviewer disagreement. |
| Manage | Block publication for missing evidence; track incidents and improve rules/prompts from review outcomes. |

## Evaluation set to build before expansion

Create a hand-labeled dataset from the first jurisdiction:

- provisions that truly require a manual, paper, or physical process;
- provisions that appear to do so but contain an exception or referenced definition;
- provisions where manual review is an essential safeguard;
- known false positives and citations that changed over time.

Measure precision of the initial review queue before reporting “automation-barrier” counts or fiscal estimates.
