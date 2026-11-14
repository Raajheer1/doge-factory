# DOGE Factory architecture

## Design goal

Produce a **citation-backed policy modernization case**: a reviewer can trace every finding and proposed change to a versioned source provision, a stated detection rule, and documented assumptions. The system must not present a draft as enacted law or execute legislative outreach without approval.

## System context

```mermaid
flowchart LR
  Sources[Authoritative legal sources<br/>USLM • XML • HTML • PDFs] --> Ingest[Ingestion service]
  Ingest --> Store[(Versioned source store)]
  Ingest --> Normalize[Normalizer & citation resolver]
  Normalize --> Index[(Search / vector index)]
  Normalize --> Store

  Analyst[Policy analyst] --> Workspace[Review workspace]
  Workspace --> Engine[Policy engine]
  Engine --> Index
  Engine --> Store
  Engine --> Findings[(Findings & evidence)]

  Findings --> Review[Legal / policy review]
  Review --> Draft[Redline & impact brief]
  Draft --> Export[Approved export]
```

## Policy-engine pipeline

```mermaid
flowchart TD
  A[Select jurisdiction, domain, and source version] --> B[Extract sections and citations]
  B --> C[Run deterministic barrier rules]
  C --> D[Retrieve related definitions, exceptions, and cross-references]
  D --> E[Generate structured candidate finding]
  E --> F{Evidence supports claim?}
  F -- No --> G[Reject or mark needs research]
  F -- Yes --> H[Reviewer validates scope and safeguards]
  H --> I{Approved for drafting?}
  I -- No --> J[Close with rationale]
  I -- Yes --> K[Create redline and impact scenario]
  K --> L[Legal and policy sign-off]
  L --> M[Export a clearly labeled proposal]
```

## Deployment boundaries

| Boundary | Responsibility | Requirement |
| --- | --- | --- |
| Source acquisition | Fetch and retain original legal material | Record URL, publisher, retrieval time, checksum, and license/terms. |
| Source store | Immutable source snapshots | Never overwrite an analyzed version. |
| Analysis service | Rules, retrieval, and structured generation | Every claim links to a source span and confidence is not treated as proof. |
| Review workspace | Triage, annotations, approvals | Role-based access and a complete decision audit trail. |
| Export service | Memo and redline generation | Watermark drafts as proposed and include version/citation data. |

## Human-review states

```mermaid
stateDiagram-v2
  [*] --> Detected
  Detected --> NeedsResearch
  Detected --> UnderReview
  NeedsResearch --> UnderReview
  UnderReview --> Rejected
  UnderReview --> ApprovedForDrafting
  ApprovedForDrafting --> DraftReviewed
  DraftReviewed --> Published
  DraftReviewed --> UnderReview
  Rejected --> [*]
  Published --> [*]
```

Only a reviewer can transition a finding to `ApprovedForDrafting`; only an authorized publisher can transition a draft to `Published`.
