# DOGE Factory

> **Department of Government Efficiency / Engineering Factory**

DOGE Factory is an autonomous regulatory refactoring platform that helps governments identify policy written for a paper-and-people era, modernize it for responsible automation, and build the case for legislative action.

## The problem

Government policy is often *human-native*, rather than *AI-native*. Federal, state, and local statutes can explicitly require manual review, paper records, wet signatures, or other human-in-the-loop processes—even when technology can perform the same work more quickly, consistently, and affordably.

These requirements can:

- Preserve expensive administrative bottlenecks.
- Block adoption of safe, compliant automation.
- Protect entrenched manual intermediaries.
- Shift avoidable costs onto taxpayers.

The bottleneck to government efficiency is not always the technology. Often, it is the law.

## What we’re building

DOGE Factory ingests municipal, state, and federal codes to identify provisions that unnecessarily mandate manual work. It produces proposed, reviewable legislative redlines and a localized fiscal-impact brief to help policymakers modernize policy while preserving oversight, due process, privacy, and compliance.

**We turn legacy, human-only laws into AI-native policy—clearing the path for accountable public-sector modernization.**

## How it works

### 1. Audit

Scans statutes and regulations to isolate mandatory human bottlenecks, paper-era requirements, and automation barriers—then estimates their potential fiscal impact.

### 2. Redline

Translates legacy, paper-bound provisions into reviewable, AI-native legislative amendments designed to preserve the policy’s original safeguards without requiring unnecessary manual labor.

### 3. Mobilize

Packages the legislative redline, fiscal ROI memo, and stakeholder context for the lawmakers and committees positioned to act.

## Example outcome

For a given code section, DOGE Factory can help a policy team answer:

1. **What does this law require people to do manually?**
2. **Is that requirement necessary for the policy objective or legal safeguard?**
3. **What is a legally actionable amendment?**
4. **What could modernization save taxpayers and constituents?**
5. **Who has the authority to move the change forward?**

## Principles

- **Human accountability:** Automation should strengthen—not remove—appropriate oversight and appeal processes.
- **Legislative precision:** Recommendations are specific, traceable, and suitable for expert legal review.
- **Measurable impact:** Fiscal claims should be transparent, localized, and evidence-backed.
- **Public interest first:** Modernization must protect privacy, equity, due process, and public trust.

## Status

Early-stage concept and product development. The [housing policy graph guide](docs/housing-policy-graph.md) covers the HydraDB-backed fixture, setup, and tests.

## Disclaimer

DOGE Factory is a policy-analysis and drafting-support tool. Its output is not legal advice and should be reviewed by qualified legal, policy, security, and subject-matter experts before use.

## Voice agents

The Mobilize step's calling agents live in `voice_agents/`. See [docs/voice-agents.md](docs/voice-agents.md).
