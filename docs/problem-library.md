# Policy problem library

Real products that governments would buy but can't, or can only buy in a crippled form, because of a specific line of policy. Each entry gives the SaaS, the government buyer, the **exact blocking text with an official link**, and the **government-side cost of the status quo**.

Research date: 2026-11-14. Every quote and number was fetched from the cited source during research.
- **R** = reported by the source.
- **C** = computed by us from sourced inputs (the arithmetic is shown).
- Status changes fast. **Re-check anything marked ⏱ the day before a pitch.**

**How to use in a pitch:** open with the scale numbers, then go deep on one flagship (Kentucky car titles or HUD pay stubs). Then flash the index to show it's a pattern, not a one-off.

---

## 1. The scale

| Metric | Value | Source |
|---|---|---|
| Federal paperwork burden (live inventory) | **11.39 billion hours/yr** across **10,709** active information collections (R). ≈ **5.5M people** doing paperwork full time, at 2,080 hrs/yr (C) | [reginfo.gov PRA inventory](https://www.reginfo.gov/public/do/PRAReport?operation=11) |
| Share of burden from taxes (Treasury/IRS) | 6,657M of 10,503M hrs = **63%** (FY2023) | [OMB ICB FY2023, App. C](https://bidenwhitehouse.archives.gov/wp-content/uploads/2024/10/FINAL_REV_2023-ICB-Appendix-C-FY-2023-Paperwork-Burden-Accounting.pdf) |
| Improper payments, government-wide | **~$186B** in FY2025 (R) | [GAO-26-108694](https://www.gao.gov/products/gao-26-108694) |
| …caused by failing to use data that exists or could be accessed | 66% + 15% + 8% = **~89%, ≈ $165B** (C). "Insufficient applicant documentation" = **0%** | [CRS R48296, Table 2](https://www.everycrsreport.com/files/2026-06-02_R48296_8eaf327d0204b3aeb33815f045ba5b527e7e332b.html) |
| Federal IT budget spent running existing systems | **~80%** of >$100B/yr (R) | [GAO-25-107795](https://www.gao.gov/products/gao-25-107795) |
| Paper check vs. ACH | **$3.07** per check, "20 times more expensive than ACH"; **40.9M** checks in FY2025 (R) → ≈ **$126M/yr** (C) | [Treasury NPRM, 2026-08278](https://www.govinfo.gov/content/pkg/FR-2026-04-29/html/2026-08278.htm) |
| Paper vs. e-filed tax return | Paper costs **43×** more to process; paper is **6%** of returns but **72%** of processing cost (R, FS2025) | [TIGTA 2026-408-003](https://www.oversight.gov/sites/default/files/documents/reports/2026-02/2026408003fr.pdf) |
| Veterans' time on PDF and paper forms | **64M hrs/yr**; **263** VA forms are PDF- or paper-only (R, 2023) | [OIRA Burden Reduction Report 2023](https://bidenwhitehouse.archives.gov/wp-content/uploads/2023/07/OIRA-2023-Burden-Reduction-Report.pdf) |

**Don't say:**
- "11.4B hours cost $203B." The $203B on reginfo is respondents' out-of-pocket cost, not the hours priced in dollars.
- "Applicants' missing paperwork causes improper payments." FY2025 attributes 0% to that. The real story is that *government fails to check data it already has*.

---

## 2. Index

| # | Product a government would buy | Blocking line item | Cost of the status quo |
|---|---|---|---|
| 1 | E-title with identity proofing (KY) | KRS 186.190(3)(b): affidavit signatures "individually notarized" | Every private car sale = 2 notary visits; re-enacted in 2026 |
| 2 | Remote parental-consent ID check (State Dept.) | 22 CFR 51.28: consent "signed before a notary public" | **362,900 forms, 120,967 hrs, $2.79M** notary fees/yr |
| 3 | E-wills custody and e-filing (TX) | Tex. Estates Code §251.051: witnesses sign "in their own handwriting" | **63,952** new estate cases/yr filed as paper originals |
| 4 | Remote I-9 for public employers | 8 CFR 274a.2 plus DHS notice: remote exam "available only to qualified employers" (E-Verify) | **35.7M hrs/yr**, 62M responses |
| 5 | TreasuryDirect identity-proofing fallback | FS 5444: "Sign in ink… Original signature is required" | 33,534 forms, **$778K/yr** in time |
| 6 | Payroll-data income verification (HUD) | PIH 2023-27 §7.2: "minimum of two current and consecutive pay stubs" | **2.34M** recerts/yr; **1.59M hrs**; $5,101 per agency/yr |
| 7 | Digital SNAP interview | 7 CFR 273.2(e): "face-to-face interview… at least once every 12 months" | States' admin share rises from 50% to **75%**: ≈ **+$2.8B/yr** to states |
| 8 | Electronic-data-first SNAP verification | 7 CFR 273.2(f)(4)(i): "documentary evidence as the primary source" | **10.62%** error rate, **$10.1B** improper |
| 9 | Medicaid work-requirement auto-verification | 42 CFR 435.557: "must require documentation" | **42.7M hrs, ~$552M/yr** in beneficiary time (CMS's own estimate) |
| 10 | Ex parte Medicaid renewal engine | 42 CFR 435.952(c)(2)(ii): paper allowed if a data match "would not be effective" | **~17M** procedural disenrollments during unwinding |
| 11 | Remote WIC certification | 7 CFR 246.7(o)(1): "physically present at each WIC certification" | $2.33B admin cost; waivers expire ⏱ |
| 12 | UI identity proofing with an assisted channel | UIPL 10-26: states must fund a separate "non-digital option" | $191B improper pandemic UI; **13.15%** improper in 2025 |
| 13 | Tele-MOUD for jails (DEA) | 21 U.S.C. 829(e): "at least 1 in-person medical evaluation" | Flexibility expires **12/31/2026** ⏱; 7M+ prescriptions/yr issued without a prior visit |
| 14 | ePA for state Medicaid | CMS-0057-F: API not required until 2027; drugs excluded; fax still allowed | **$15B** in savings over 10 yrs |
| 15 | Multistate telehealth panels | Tex. Occ. Code 155.001 (patient-state license) | **246,359** extra compact licenses issued |
| 16 | Any SaaS sold to federal agencies | M-24-15: "must obtain and maintain a FedRAMP authorization" | **2–3 yrs**; ~27 authorizations/yr; agency $69K–$400K and vendor $0.3M–$3.7M each |
| 17 | SaaS sold to Texas agencies | Tex. Gov't Code 2054.0593(e) plus the end of FedRAMP reciprocity | A second review for already-authorized products |
| 18 | Small SaaS sold to Kentucky | KY affidavit FAQ: purchases "over $1000… must be… notarized" | "If the vendor refuses… We cannot contract with them." |
| 19 | Annual SaaS subscriptions (federal) | 31 U.S.C. 3324(a): no payment beyond value "already provided" | No prepaid annual subscriptions |
| 20 | AI tools for agencies | M-25-22: ATO "prior to deployment" for every AI system | VA leaders: contracts "can take 2 years to award" |
| 21 | Fully digital plan review (NJ) | N.J.A.C. 5:23-2.15B(d): jobsite plans "sealed and wet signed" | SF: **280-day** median permit; 1,389 stalled for a median **4.1 yrs** |
| 22 | AI NEPA drafting | 42 U.S.C. 4336a: 150-page cap and 2-yr deadline, ignored in practice | Average EIS **661 pages** (4.4× cap), **4.5 yrs** |
| 23 | Automated grid interconnection studies | FERC LGIP §7.4: 150-day study run by the transmission provider | **2,061 GW** queued; median >3 yrs |
| 24 | E-transcript nurse licensing (WI) | Wis. Admin. Code N 2.12(2): school "shall forward directly" | $11.2M/yr credentialing; slowest cases **190 days** |
| 25 | Online public-notice portal (IA) | Iowa Code 349.16: publish in newspapers "at the expense of the county" | **$50–$250** per notice |
| 26 | Digital disbursements (Treasury) | 31 CFR 208.4(a)(7): EFT not required for one-time payments | **40.9M** checks; ≈ **$119M/yr** avoidable |
| 27 | Paper-return capture and e-file (IRS) | 26 U.S.C. 6011(e)(1): may not require "other than on paper forms" | ~11M paper 1040s; **5%** scanned on time |
| 28 | Electronic death registration (AK) | AS 18.50.230: no electronic mandate | **24%** of deaths reported within 2 wks (US: 54%) |
| 29 | Pro se court e-filing (federal) | FRCP 5(d)(3)(B): pro se may e-file "only if allowed" | **90K** pro se cases; e-filing banned in **29** districts |
| 30 | FOIA portal and AI redaction | OK Open Records Act (Wagner): no duty to produce electronically | Federal FOIA **$661M/yr**, backlog **+27%** |
| 31 | AI call-center agent (CA EDD) | Cal. Penal Code 632: "consent of all parties", government included | EDD answered **<1%** of calls; staff grew to 5,600 |
| 32 | AI voice benefit reminders | 47 CFR 64.1200 plus FCC 20-182: counties and contractors need prior consent | **14.9M** procedural Medicaid disenrollments |
| 33 | Court-date text reminders | FCC 20-182: counties are TCPA "persons" | Texts cut failures to appear by **21%**, **20,800** warrants avoided |
| 34 | Federal jury e-summons | 28 U.S.C. 1864(a): clerk "shall mail" forms | **40%** of mailings wasted in one district |
| 35 | NG911 for county call centers (NJ) | N.J.S.A. 52:17C-19: 911 fees can fund "State's… operating expenses" | **~75%** of ~$122M diverted (2017) |
| 36 | AI court self-help (CA) | Bus. & Prof. Code 6125: no one may "practice law" unlicensed | 4.3M self-represented litigants |
| 37 | BVLOS drone inspection and delivery | 14 CFR 107.31: must "see the unmanned aircraft throughout" | Part 108 is **286 days** past its EO deadline ⏱ |

---

## 3. Cases

### Identity, signatures and notarization

**1. Online car sales stall on a twice-notarized affidavit (Kentucky). FLAGSHIP**
- **SaaS:** an electronic title and transfer system with built-in identity proofing (Persona/Proof-style) for private-party sales. Real companies: [PrivateAuto](https://privateauto.com/), [Proof](https://www.proof.com/).
- **Buyers:** the KY Transportation Cabinet and 120 county clerks.
- **Line item:** "the signatures on the affidavit shall be individually notarized before the county clerk shall issue … a transfer of registration." KRS 186.190(3)(b) ([statute](https://apps.legislature.ky.gov/law/statutes/statute.aspx?id=58262)).
  - [KRS 138.450(22)](https://apps.legislature.ky.gov/law/statutes/statute.aspx?id=53526) defines it: buyer and seller signatures "individually notarized".
  - Form [TC 96-182](https://transportation.ky.gov/Organizational-Resources/Forms/TC%2096-182.pdf) (Rev. 06/2026).
- **Status:** SB 110 (2026, Acts ch. 135) makes titles **electronic by default from 7/1/2027** but **kept the notarized affidavit** ([bill](https://apps.legislature.ky.gov/record/26RS/sb110.html)). KRS 186A.017 already allows e-signatures by approved entities.
- **Cost:**
  - Anderson County alone processed **4,340 titles** in 2024 (R, [SB 110 local mandate statement](https://apps.legislature.ky.gov/recorddocuments/note/26RS/sb110/LM.pdf)).
  - Ceiling: 4,340 × 2 signatures × $2 = **$17,360/yr in notarial acts** in one small county (C).
  - No statewide count found.
- **Redline:** accept an affidavit e-signed through the KRS 186A.017 system with NIST IAL2 identity proofing in place of individual notarization. Keep the perjury penalty and the usage-tax floor.
- **Companion cases:**
  - **Ohio** built an online title portal but still requires the application "sworn to before a notary public" ([ORC 4505.06](https://codes.ohio.gov/ohio-revised-code/section-4505.06); 5.63M titles/yr).
  - **Maryland** repealed its notarized bill-of-sale requirement in 2026 ([HB 251](https://mgaleg.maryland.gov/mgawebsite/Legislation/Details/hb0251?ys=2026RS)). Proof the change can happen.
- **Caveat:** whether KY clerks accept remote online notarization is unverified.

**2. A child's passport needs a notary for the absent parent (federal)**
- **SaaS:** a remote identity-proofed consent module (Proof, Socure, DocuSign).
- **Buyer:** the Bureau of Consular Affairs.
- **Line item:** consent must be "signed before a notary public or… a passport specialist" ([22 CFR 51.28](https://www.ecfr.gov/current/title-22/section-51.28)). Form DS-3053 is "printed for manual signature, notarization, and submission."
- **Cost (R, [OMB 1405-0129](https://www.reginfo.gov/public/do/PRAViewICR?ref_nbr=202412-1405-001)):**
  - **362,900 forms/yr**, **120,967 burden hours**, **$2,794,330/yr** in notary fees.
  - $311,330/yr in federal processing cost.
- **Confidence:** high.

**3. Online wills die at "in their own handwriting" (Texas)**
- **SaaS:** e-will execution plus electronic-original custody and e-filing for county clerks. Real company: [Trust & Will](https://trustandwill.com/).
- **Line items:**
  - Witnesses must "subscribe their names to the will in their own handwriting in the testator's presence" ([Estates Code §251.051](https://tcss.legis.texas.gov/resources/ES/htm/ES.251.htm)).
  - The UETA carve-out excludes "a law governing the creation and execution of wills" ([Bus. & Com. Code §322.003](https://tcss.legis.texas.gov/resources/BC/htm/BC.322.htm)).
- **Cost:** **63,952 new decedents'-estate cases/yr**, each with a paper original deposited with the clerk (C, from [OCA FY2024 data](https://www.txcourts.gov/media/1460326/1-county-level-probate-and-mh-activity-detail-print-fy-2024.xlsx)).
- **Status:** e-will bills failed in 2019 and 2023. Kentucky adopted e-wills in 2026 (secondary source).

**4. Remote hiring breaks on physical ID inspection (Form I-9)**
- **SaaS:** remote I-9 with live video document exam plus IAL2 identity proofing, for state and local HR and school districts ([Mitratech](https://mitratech.com/products/i-9-compliance/i-9-pro/), [WorkBright](https://workbright.com/products/smart-i9-p1)).
- **Line items:**
  - "Physically examine… the documentation presented" ([8 CFR 274a.2](https://www.law.cornell.edu/cfr/text/8/274a.2)).
  - The remote alternative "is available only to qualified employers", meaning E-Verify participants ([DHS notice](https://www.govinfo.gov/content/pkg/FR-2023-07-25/html/2023-15533.htm)).
- **Cost (R, [2026 ICR notice](https://public-inspection.federalregister.gov/2026-09846.pdf)):**
  - **35,655,796 hours/yr**.
  - **62,063,950 employer responses/yr**.
- **Why it's a great redline:** DHS can already authorize alternatives for "some or all employers". The block is one eligibility sentence in a notice, not a statute.

**5. TreasuryDirect locks out holders who fail online identity checks**
- **SaaS:** an IAL2 identity-proofing fallback (Login.gov, Socure, ID.me) for the Bureau of the Fiscal Service.
- **Line items:**
  - "Offline transactions will require a certified or guaranteed signature" ([31 CFR 363](https://www.ecfr.gov/current/title-31/subtitle-B/chapter-II/subchapter-A/part-363)).
  - Form FS 5444: "Sign in ink in the presence of a certifying officer or notary… Original signature is required… Mail the completed authorization form" ([form](https://www.treasurydirect.gov/forms/acctauth.pdf)).
- **Cost:**
  - **33,534 forms/yr** and 16,767 hours (R, [OMB](https://www.reginfo.gov/public/do/DownloadDocument?objectID=173241300)).
  - × $46.38/hr ≈ **$778K/yr** (C).

### Public benefits

**6. Two pay stubs or no voucher (HUD). FLAGSHIP**
- **SaaS:** consumer-permissioned payroll income verification ([Truv](https://truv.com/), [Argyle](https://argyle.com/), Plaid, Steady) built into recertification at public housing agencies.
- **Line item:** "PHAs/MFH Owners are required to obtain a minimum of two current and consecutive pay stubs for determining projected annual income from wages when they are relying on pay stubs for Level 4 documentation" ([Notice PIH 2023-27, Rev. 3, Apr 2026, §7.2](https://hud.gov/sites/dfiles/OCHCO/documents/2023-27pihn.pdf)).
  - This notice replaced PIH 2018-18, which said the same thing.
- **Nuance (use it, it's honest):**
  - The same notice already ranks "UIV using non-EIV system (e.g., The Work Number…)" as the **highest** level of verification.
  - The gap is that consumer-permissioned payroll data isn't named, so agencies default to paper.
- **Cost (R, [HUD-50058 ICR](https://www.govinfo.gov/content/pkg/FR-2023-06-07/pdf/2023-12162.pdf)):**
  - **2,340,162 recertifications/yr**.
  - **1,593,040 burden hours/yr**.
  - **$5,101 per agency/yr** in data entry across ~4,153 agencies.
  - Up to ~4.7M pay stubs/yr (C, upper bound).
- **Status:** HOTMA enforcement starts **1/1/2027** ([PIH 2026-15](https://www.hud.gov/sites/default/files/hudclips/documents/PIH-2026-15.pdf)). Timely.
- **Redline:** name consumer-permissioned, direct-from-payroll data as Level 5 upfront income verification, with data-currency and audit-trail requirements. Keep EIV reconciliation.

**7. The 1970s phone call: SNAP's mandatory interview**
- **SaaS:** an asynchronous, AI-assisted interview that flags only discrepancies for a caseworker ([Code for America](https://www.codeforamerica.org/programs/social-safety-net/), [Nava](https://www.navapbc.com/)).
- **Line item:** "households must have a face-to-face interview with an eligibility worker at initial certification and at least once every 12 months thereafter". The only alternative is "a telephone interview" ([7 CFR 273.2(e)](https://www.ecfr.gov/current/title-7/section-273.2)).
- **Cost:**
  - State SNAP admin costs were **$11.1B** in FY2023 (R, [FNS](https://fns-prod.azureedge.us/sites/default/files/resource-files/snap-sar-fy23.pdf)).
  - The state share rises from 50% to **75% on Oct 1, 2026** (R, [NCSL](https://www.ncsl.org/state-legislatures-news/details/5-changes-the-beautiful-bill-is-bringing-to-snap)), ≈ **+$2.8B/yr** to states (C).
  - SNAP forms carry **82.6M burden hours/yr** (R, [OMB 0584-0064](https://www.reginfo.gov/public/do/PRAViewICR?ref_nbr=202506-0584-001)).
- **Status:** pandemic waivers are ending. Oregon ended its waiver 5/31/2026: "Federal SNAP rules require an interview".

**8. Paper first by law: SNAP's documentary-evidence rule**
- **SaaS:** electronic income verification as the primary source ([Equifax TotalVerify](https://totalverify.equifax.com/hr1), [SteadyIQ](https://www.steadyiq.com/)).
- **Line item:** "State agencies shall use documentary evidence as the primary source of verification… Examples… include wage stubs, rent receipts, and utility bills" ([7 CFR 273.2(f)(4)(i)](https://www.ecfr.gov/current/title-7/section-273.2)).
- **Cost:**
  - FY2025 payment error rate was **10.62%**, about **$10.1B** improper (R, [FNS](https://fns-prod.azureedge.us/sites/default/files/resource-files/snap-qcfy25-per.pdf)).
  - **21 of 53** state agencies are at or above 10% (C).
  - From FY2028, rates at or above 6% trigger a 5–15% state share of benefits.
- **Caveat:** FNS doesn't attribute errors to paper verification. Present it as a cost the product targets.

**9. "Hand in your timesheets": Medicaid work-requirement documentation**
- **SaaS:** automated compliance verification from payroll, claims and SNAP data (Nava, Equifax TotalVerify, SteadyIQ, [Fortuna Health](https://www.fortunahealth.com/)).
- **Line item:** "Beginning on January 1, 2028, when there is no reliable information available to the State… the agency must require documentation whenever documentation is reasonably available". States may also skip a data match on cost grounds ([42 CFR 435.557, IFR 91 FR 33348](https://www.federalregister.gov/documents/2026/06/03/2026-11094)).
- **Cost (R, CMS's own regulatory impact analysis):**
  - 44% of ~20M people (**8.8M**) must document compliance, twice a year: **35.2M hrs, $454.8M/yr**.
  - Total with applicants is **42.7M hrs, ~$552M/yr** (C).
  - CMS expects **7%** of compliant or exempt people to lose coverage for administrative reasons.
  - Each 10-point gain in the ex parte (automatic data-match) rate ≈ **8M hrs and $103M/yr** saved (C).
- **Status:** effective 7/31/2026; states must implement by 1/1/2027. Litigation pending ⏱.

**10. The ex parte gap: Medicaid renewals that fall back to forms**
- **SaaS:** an ex parte renewal engine. Code for America's Minnesota work cut caseworker time per case from 70 to 11 minutes (R, CfA).
- **Line item:** documentation is allowed where "establishing a data match would not be effective, considering… the administrative costs… compared with… relying on paper documentation" ([42 CFR 435.952](https://www.ecfr.gov/current/title-42/section-435.952)).
- **Cost:**
  - FY2025 Medicaid improper payments were **$37.39B**, **77%** "insufficient documentation" (R, [CMS](https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet)). This includes provider-side documentation.
  - Unwinding: **>25M** disenrolled, **69%** for procedural reasons ≈ **17.3M** (R/C, [KFF](https://www.kff.org/medicaid/issue-brief/an-examination-of-medicaid-renewal-outcomes-and-enrollment-changes-at-the-end-of-the-unwinding)).
  - Ex parte rates ranged from **90%+** (AZ, NC, RI) to **≤11%** (PA, TX).

**11. Bring the baby to the clinic: WIC physical presence**
- **SaaS:** remote WIC certification ([CMA WIC+](https://cma.com/services/case-management-platforms/wic-plus-participant-portal), Code for America).
- **Line item:** "The State or local agency must require all applicants to be physically present at each WIC certification" ([7 CFR 246.7(o)(1)](https://www.ecfr.gov/current/title-7/section-246.7)).
- **Cost:** FY2025 WIC admin costs were **$2.33B** for 6.87M participants, ≈ **$28/participant/month** (R/C, [FNS](https://fns-prod.azureedge.us/sites/default/files/resource-files/wisummary-10.pdf)).
- **Pandemic precedent:** **99%** of local agencies certified remotely during the pandemic, versus 12% before (R).
- **Status:** ⏱ waivers run to 9/30/2026, reportedly extended to 9/30/2027. The MODERN WIC and 21st Century WIC Acts are pending.

**12. Pay twice for identity: unemployment insurance's separate non-digital option**
- **SaaS:** identity proofing plus an assisted channel ([Socure](https://www.socure.com/industries/public-sector), Nava, Login.gov).
- **Line item:** states "are required to provide a non-digital option separate from the Department's ID verification services offering" ([UIPL 10-26](https://www.dol.gov/sites/dolgov/files/ETA/advisories/UIPL/2026/UIPL%2010-26/UIPL%2010-26.pdf)).
- **Cost:**
  - Pandemic UI: "at least $191 billion may have been improperly paid", "$76 billion stolen by fraudsters" (R, [DOL-OIG](https://oig.dol.gov/public/Press%20Releases/OIG-Press-Release-030526.htm)).
  - 2025 improper payment rate: **13.15%, $4.73B** (R/C, [DOL](https://oui.doleta.gov/unemploy/improp_payrate.asp)).
- **Framing:** an unfunded mandate to build a second channel. It is also an equity safeguard, so don't call it a "ban on digital ID".

### Health

**13. The Ryan Haight cliff: in-person exam before tele-prescribing**
- **SaaS:** tele-MOUD (addiction treatment by video) for jails and prisons, with a remote prescriber pool ([Bicycle Health](https://www.bicyclehealth.com/)).
- **Line item:** a prescription requires "a practitioner who has conducted at least 1 in-person medical evaluation of the patient" ([21 U.S.C. 829(e)](https://www.law.cornell.edu/uscode/text/21/829)).
- **Status:** ⏱ telehealth flexibilities **end 12/31/2026** ([90 FR 61301](https://www.govinfo.gov/content/pkg/FR-2025-12-31/html/2025-24123.htm)). The special-registration final rule has been under White House review since 8/25/2026 ([RIN 1117-AB40](https://www.reginfo.gov/public/do/eo/neweomeeting?rin=1117-AB40)).
- **Cost:** **7M+** controlled-substance prescriptions in 2024 (~16%) were issued without a prior in-person visit (R, stakeholder data cited by DEA).

**14. Prior auth by fax**
- **SaaS:** an electronic prior-authorization (FHIR) API plus AI agents for payer calls, for state Medicaid fee-for-service ([Cohere Health](https://www.coherehealth.com/), [Infinitus](https://www.infinitus.ai/)).
- **Line item:** denials "may be communicated via portal, fax, email, mail, or phone". The API is required only "beginning January 1, 2027", and "this provision does not apply to prior authorization decisions for drugs" ([CMS-0057-F](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f)).
- **Cost:** **~$15B** in savings over 10 years, ≈ $1.5B/yr (R/C, [CMS](https://www.cms.gov/newsroom/press-releases/cms-finalizes-rule-expand-access-health-information-improve-prior-authorization-process)). The drug rule CMS-0062-P is still only proposed.

**15. 50 licenses for one doctor**
- **SaaS:** a multistate telehealth panel for Medicaid and state-employee plans ([Teladoc](https://www.teladochealth.com/)).
- **Line item:** "A person may not practice medicine in this state unless the person holds a license issued under this subtitle" (Tex. Occ. Code 155.001, [mirror](https://texas.public.law/statutes/tex._occ._code_section_155.001)).
- **Cost:** the Interstate Medical Licensure Compact has issued **246,359 licenses** (R, [IMLCC](https://www.imlcc.com/)). Each is an extra state license, even under the compact.

### Selling to government (procurement)

**16. Two to three years to sell to the federal government (FedRAMP)**
- **Line item:** "Agencies must obtain and maintain a FedRAMP authorization when the cloud product or service falls within the scope of this section" ([OMB M-24-15](https://fedramp.gov/2026/authority/m-24-15/scope/)).
- **FedRAMP's own words:** "an anticipated timeline of 2-3 years… if they somehow managed to find a sponsor"; requirements "forced cloud services to create government-specific versions… less effective, lower quality, and more expensive" ([FedRAMP FY25](https://www.fedramp.gov/2025-09-30-fedramp-built-a-modern-foundation-in-fy25-to-deliver-massive-improvements-in-fy26/)).
- **Cost (R, [GAO-24-106591](https://www.gao.gov/assets/d24106591.pdf)):**
  - Agency sponsorship costs **$69K–$400K** per authorization.
  - VA: ≈ **$10.3M** across 27 services (C).
  - Vendors: **$300K–$3.7M** each.
- **Volume:** "a little more than **350** cloud services… in 13 years" ≈ **27/yr** (C).
- **Status:** the 20x reform and Consolidated Rules become mandatory **1/1/2027** ([timeline](https://www.fedramp.gov/2026/timeline/)). This is a live opening.

**17. Already federally authorized? Texas wants its own review (TX-RAMP)**
- **Line item:** an agency "may not enter or renew a contract… unless the vendor demonstrates compliance with program requirements" ([Tex. Gov't Code 2054.0593(e)](https://texas.public.law/statutes/tex._gov't_code_section_2054.0593)).
- **Reciprocity removed:** "As of October 30, 2024, FedRAMP and StateRAMP certified products will no longer be automatically added" ([DIR FAQ](https://dir.texas.gov/information-security/tx-ramp-frequently-asked-questions-faqs)).
- **Comparable cost:** GovRAMP charges **$13,556/yr** for a $1–5M-revenue vendor, excluding the third-party assessor ([pricing](https://govramp.org/pricing-overview)).

**18. Notarize to sell a $1,001 subscription (Kentucky)**
- **Line item:** "Small purchase awards… (over $1000)… must be signed by awarded contractor only, and notarized… All Affidavits must be notarized in all circumstances."
  - Out-of-state vendors: "requires an actual notary seal. Have the vendor mail in the original."
  - If a vendor refuses: "We cannot contract with them."
  - Source: [KY Finance Cabinet FAQ](https://finance.ky.gov/eProcurement/ResourcesSupport/FrequentlyAskedQuestionsabouttheRequiredAffidavitforBiddersRevisedAugust2020.pdf).
- **Caveat:** the FAQ dates from 2020 and exempts "dues, subscriptions". Verify before using.

**19. A 1982 law against paying for SaaS upfront**
- **Line item:** a payment "may not be more than the value of the service already provided" ([31 U.S.C. 3324(a)](https://www.law.cornell.edu/uscode/text/31/3324)).
- **Precedent:** GAO B-256692 (1995) let the CDC prepay for Microsoft TechNet as a "publication", but not the bundled support.
- **Confidence:** medium. How this applies to SaaS is inferred.

**20. AI moves weekly; procurement takes two years**
- **Line item:** AI systems "must receive an authorization to operate… prior to deployment" ([OMB M-25-22](https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-22-Driving-Efficient-Acquisition-of-Artificial-Intelligence-in-Government.pdf)).
- **Evidence:** VA leaders told GAO: "FAR-based contracts can take 2 years to award… at this pace, agencies are no longer purchasing innovation" ([GAO-26-107859](https://files.gao.gov/reports/GAO-26-107859/index.html)).
- **Who gets through anyway:** only big vendors got the $1-per-agency OneGov deals ([OpenAI](https://www.gsa.gov/about-gsa/newsroom/news-releases/gsa-announces-new-partnership-with-openai-delivering-deep-discount-to-chatgpt-08062025), [Anthropic](https://www.gsa.gov/about-gsa/newsroom/news-releases/gsa-strikes-onegov-deal-with-anthropic-08122025)).
- **Also:** M-25-21 requires per-deployment minimum practices for ~430 high-impact federal AI use cases. That is a safeguard, and the fix is reusable ("FedRAMP for AI") assessments.

### Permitting, energy and licensing

**21. Paperless permit, paper plans (New Jersey)**
- **SaaS:** end-to-end digital plan review with verified e-seals plus AI pre-check ([CivCheck](https://www.civcheck.ai), [Archistar](https://www.archistar.ai/echeck/government), [Symbium](https://www.symbium.com), [Govstream.ai](https://www.govstream.ai)).
- **Line item:** "Where permits are issued electronically, the applicant shall provide a physical copy of the released plans at the worksite that are sealed and wet signed by the design professional" ([N.J.A.C. 5:23-2.15B(d)](https://www.law.cornell.edu/regulations/new-jersey/N-J-A-C-5-23-2-15B), effective 11/18/2024).
- **Cost:**
  - San Francisco: **280-day** median to issue a housing permit, **3** review rounds, **1,389** stalled applications with a median age of **4.1 years** (R/C, [SF Budget & Legislative Analyst, 2026](https://sfbos.archive.sf.gov/sites/default/files/BLA_Post_Entitlement_Permitting_030526.pdf)).
  - The wet-signature rule is New Jersey's. The cost data is San Francisco's.
- **Proof AI works:** Honolulu with CivCheck went from **3.4 to 1.4** review cycles and from **73 to 32.5** days ([Route Fifty](https://www.route-fifty.com/artificial-intelligence/2026/08/cities-turn-ai-speed-housing-permitting/415564/)).
- **Local variant:** Nevada County, CA requires "stamp and wet signature… on all pages" even though state rule 16 CCR §411 allows e-signatures ([handbook](https://nevadacountyca.gov/DocumentCenter/View/15484/Building-Permit-Application-Handbook-PDF)).

**22. The 661-page environmental review**
- **Line item:** an EIS "shall not exceed 150 pages", with a 2-year deadline ([42 U.S.C. 4336a](https://www.law.cornell.edu/uscode/text/42/4336a)).
- **Cost (R, CEQ):**
  - The average final EIS is **661 pages** ([length report](https://nepa.gov/sites/default/files/documents/CEQ_EIS_Length_Report_2020-6-12.pdf)), **4.4×** the cap (C).
  - Average **4.5 years** from start to decision ([timeline report](https://nepa.gov/sites/default/files/documents/CEQ_EIS_Timeline_Report_2020-6-12.pdf)).
- **SaaS:** AI drafting and comment analysis. PNNL's [PermitAI](https://www.pnnl.gov/projects/permitai/ai-applications) is "only available for beta testing by federal government users". There is no purchasing path for commercial tools.
- **Note:** this is a procurement and practice problem more than a prohibition.

**23. A 150-day grid study that takes years**
- **Line item:** "Transmission Provider shall complete the Cluster Study within one hundred fifty (150) Calendar Days". The penalty is $1,000 per business day ([FERC LGIP](https://www.ferc.gov/sites/default/files/2024-08/LGIP.pdf)).
- **Cost (R, [LBNL via APPA](https://www.publicpower.org/periodical/article/backlog-power-plants-seeking-transmission-grid-connection-eased-somewhat-2025-lbnl)):**
  - **2,061 GW** in the queue.
  - Only **13%** of 2000–2020 requests were online by 2025.
  - The median wait is **over 3 years**.
- **Proof automation works:** an automated tool "reproduced a two-year manual interconnection study in 10 days" (FERC Commissioner Rosner, [T&D World](https://www.tdworld.com/overhead-transmission/news/55275793/ferc-commissioner-rosner-urges-isos-and-rtos-to-advance-interconnection-automation)).
- **SaaS:** Pearl Street (SUGAR), GridUnity, Google X Tapestry.

**24. Transcripts by courier (Wisconsin nursing)**
- **Line item:** "The school… shall forward directly to the department, official transcripts" ([Wis. Admin. Code N 2.12(2)](https://docs.legis.wisconsin.gov/code/admin_code/n/2/ii/12)).
- **Cost (R, [Legislative Audit Bureau 23-24](https://legis.wisconsin.gov/lab/media/ky3mcygr/23-24summary_694532.pdf)):**
  - **$11.2M/yr** spent on credentialing.
  - The slowest cases took **189.6 days**, and **75%** of that was spent waiting on documents.
  - An online system cut the average to 59 days.

**25. Paying newspapers to publish government records (Iowa)**
- **Line item:** "There shall be published in each of the official newspapers at the expense of the county…" the board proceedings, bills and treasurer reports ([Iowa Code 349.16](https://www.legis.iowa.gov/docs/code/349.16.pdf)).
- **Cost:** **$50–$250 per notice**. A state portal would cost $150K–$500K plus ~$500K/yr (R, [LSA fiscal note](https://www.legis.iowa.gov/docs/publications/FN/1371101.pdf)).
- **Companion case:** New York LLCs must publish for 6 weeks in 2 newspapers or "shall be suspended" ([NY LLC Law §206](https://www.nysenate.gov/legislation/laws/LLC/206)). A repeal bill is in committee.

### Records, payments and tax

**26. 40.9 million checks: the one-time-payment EFT waiver**
- **Line item:** "Payment by electronic funds transfer is not required… (7) Where the agency does not expect to make multiple payments to the same recipient within a one-year period" ([31 CFR 208.4](https://www.ecfr.gov/current/title-31/subtitle-B/chapter-II/part-208/section-208.4)).
- **Status:** EO 14247 ordered an end to paper checks by 9/30/2025. Treasury's tightening rule is **proposed, not final** ⏱.
- **Cost:** **$3.07/check** vs ≈$0.15 for ACH → ≈ **$119M/yr** avoidable (C).
  - Checks are **16×** more likely to be lost or stolen (R).
  - Paper infrastructure cost **$657M** in FY2024 (R).
- **SaaS:** [Paymentus](https://www.paymentus.com/government/), [Checkbook](https://checkbook.io/), [Usio](https://www.usio.com/).

**27. The law guarantees the IRS a paper problem**
- **Line item:** "the Secretary may not require returns… to be other than on paper forms supplied by the Secretary" ([26 U.S.C. 6011(e)(1)](https://www.law.cornell.edu/uscode/text/26/6011)).
- **Cost (R, [TIGTA 2026](https://www.oversight.gov/sites/default/files/documents/reports/2026-02/2026408003fr.pdf)):**
  - Paper costs **43×** more to process.
  - Contractors scanned only **5%** of 9.8M paper forms.
  - Paper refunds take **14 weeks** vs 7 for e-file ([NTA](https://www.taxpayeradvocate.irs.gov/wp-content/uploads/2026/01/IR-2026-15.pdf)).
- **Redline:** keep the right to file on paper but require a machine-readable 2D barcode.

**28. Slowest death data in the nation (Alaska)**
- **Line item:** death certificates "shall be filed with the local registrar… within three days" with no electronic mandate ([AS 18.50.230](https://www.akleg.gov/basis/statutes.asp?media=print&secStart=18.50.230&secEnd=18.50.230)). CAP lists AK and ID as "Paper only".
- **Cost (R, [NCHS VSRR 40](https://www.cdc.gov/nchs/data/vsrr/vsrr040.pdf)):**
  - **24.1%** of Alaska deaths are available within 2 weeks, vs **53.6%** nationally.
  - Only **3%** of overdose deaths nationally are available within 4 weeks.

**29. Federal courts force paper on 30% of civil filers**
- **Line item:** a person without a lawyer "may file electronically only if allowed by court order or by local rule" ([FRCP 5(d)(3)(B)](https://www.law.cornell.edu/rules/frcp/rule_5)).
- **Status:** **29 of 94** district courts prohibit it and 54 require permission ([FJC 2025](https://www.fjc.gov/content/391989/united-states-district-courts-local-rules-and-procedures-electronic-filing-self)).
- **Volume:** **89,971** of 303,563 civil cases (29.6%) were pro se in FY2025 ([US Courts C-13](https://www.uscourts.gov/sites/default/files/document/jb_c13_0930.2025.pdf)).

**30. FOIA: $661M a year and a growing backlog**
- **Cost (R, [DOJ OIP FY2025](https://www.justice.gov/oip/media/1450791/dl)):**
  - Federal FOIA cost **$661.4M**, ≈ **$405 per request** (C).
  - **1.71M** requests, a record.
  - Backlog of **339,671**, up **27%** ([summary](https://www.justice.gov/oip/blog/summary-fiscal-year-2025-annual-foia-reports-published)).
- **Blocker (Oklahoma):** "Oklahoma does not require public bodies to produce records via email or another specific method" (*Wagner*, via [RCFP](https://www.rcfp.org/open-government-guide/oklahoma/)).
- **SaaS:** GovQA, FOIAXpress, JustFOIA.

### Justice, public safety and AI calling

**31. AI call-center agents vs. California's all-party consent law**
- **Line item:** recording "without the consent of all parties to a confidential communication" is punishable by "a fine not exceeding two thousand five hundred dollars ($2,500) per violation". "Person" includes anyone "acting… on behalf of any government" ([Cal. Penal Code 632](https://california.public.law/codes/penal_code_section_632)).
- **Cost:** at the 2020 surge, EDD's "call center answered less than 1 percent of the calls it received" and staff quadrupled to **5,600+** (R, [CA State Auditor](https://information.auditor.ca.gov/reports/2020-128and628.1/summary.html)).
- **Status:** *In re Otter.AI* survived a motion to dismiss on 8/13/2026 ([order](https://storage.courtlistener.com/recap/gov.uscourts.cand.454675/gov.uscourts.cand.454675.68.0.pdf)).
- **Also:** public meetings are exempt under §632(c).

**32. AI voice reminders need prior consent, even from government**
- **Line items:**
  - The ban covers calls "using… an artificial or prerecorded voice… To any telephone number assigned to a… cellular telephone service" without "prior express consent" ([47 CFR 64.1200](https://www.ecfr.gov/current/title-47/section-64.1200)).
  - AI voices are "artificial" ([FCC 24-17](https://docs.fcc.gov/public/attachments/DOC-400393A1.txt)).
  - Counties and government contractors are "persons" ([FCC 20-182](https://docs.fcc.gov/public/attachments/FCC-20-182A1.txt)).
- **Cost:** **14.9M** people were disenrolled from Medicaid for procedural reasons in 2023–24 (R, [CMS](https://www.medicaid.gov/resources-for-states/downloads/july-2024-national-summary-renewal-outcomes.pdf)). This is the problem reminders target, not something the TCPA caused.
- **Status:** the FCC opened a consent proceeding on 10/26/2026 ⏱. **This is DOGE Factory's own Mobilize product.**

**33. Text, don't warrant: court reminders**
- **Line item:** FCC 20-182: "local government entities, including counties, cities, and towns, are 'persons'" under the TCPA, as are state contractors ([FR](https://www.govinfo.gov/content/pkg/FR-2021-02-12/html/2020-29016.htm)).
- **Cost (R, [J-PAL NYC](https://www.povertyactionlab.org/node/2395)):**
  - Texts cut failures to appear by **21%** (8 points from a 38% baseline).
  - **~20,800 warrants** avoided in a year.
  - Only **13%** of people give a cell number.
  - An NYC jail day costs ≈ **$1,389** (C, from $507K/yr, [Comptroller](https://comptroller.nyc.gov/newsroom/longer-court-case-processing-times-inflate-nycs-jail-population-cost-taxpayers-nearly-1-billion-annually-comptroller-landers-report-reveals/)).

**34. Summoned by snail mail: federal juries**
- **Line items:**
  - The clerk "shall mail to every person whose name is drawn… a juror qualification form" ([28 U.S.C. 1864](https://www.law.cornell.edu/uscode/text/28/1864)).
  - The summons may be served only "personally, or by registered, certified, or first-class mail" (§1866).
- **Cost:** N.D. Ill. found **6.5%** of forms undeliverable and **33.4%** unanswered, so **~13,500** wasted mailings in one district-year (R/C, [2009 study](https://www.ilnd.uscourts.gov/_assets/_documents/_forms/_press/Study%20of%20the%20Revised%20Jury%20Plan%20(002).pdf)). The data is old, and rates improved by 2015.

**35. The 90-cent diversion: New Jersey 911 fees**
- **Line item:** the 911 trust account sits "within the General Fund" and can fund "the State's capital equipment… facilities and operating expenses" ([P.L.2004 c.48](https://pub.njleg.gov/bills/2004/PL04/48_.HTM)).
- **Cost:** in 2017, "only one-quarter" of ~$122M went to 911 ([WHYY](https://whyy.org/articles/as-it-eyes-fee-hike-n-j-spends-most-of-what-it-collects-for-911-maintenance-on-other-things)), ≈ **$91.5M** diverted (C).
- **SaaS:** NG911 and text-to-911 ([Intrado](https://www.intrado.com/psap-solutions), [Carbyne](https://carbyne.com/partners/att/)). SCR98 (2026) would lock the fund.

**36. Robot lawyer, licensed humans only**
- **Line item:** "No person shall practice law in California unless the person is an active licensee of the State Bar". Violation is a misdemeanor ([Bus. & Prof. Code 6125–6126](https://california.public.law/codes/business_and_professions_code_section_6125)).
- **Cost:**
  - **4.3M** self-represented court users.
  - A **$44M** staffing need for self-help centers.
  - Both figures are old (R, [Judicial Council](https://courts.ca.gov/sites/default/files/courts/default/2024-12/rpt_leg_self_help.pdf)).
- **Movement:** Arizona has **114** licensed alternative business structures. Utah is drafting a rule-based AI carve-out (4/17/2026 minutes).

**37. Line of sight, line of delay: drones**
- **Line item:** the pilot "must be able to see the unmanned aircraft throughout the entire flight" ([14 CFR 107.31](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-107/subpart-B/section-107.31)).
- **Status:** EO 14307 required a final BVLOS rule within 240 days. As of 11/14/2026 it is **286 days late** (C). **239** operators fly on case-by-case waivers ([NPRM](https://www.federalregister.gov/documents/2025/08/07/2025-14992/normalizing-unmanned-aircraft-systems-beyond-visual-line-of-sight-operations)) ⏱.
- **SaaS:** drone-in-a-box bridge and pipe inspection for DOTs and public works ([Skydio](https://www.skydio.com), [Zipline](https://www.flyzipline.com)).

---

## 4. Proof that redlines work

| Win | What changed | Source |
|---|---|---|
| CA heavy autonomous trucks | DMV removed the ≥10,001 lb testing ban on 4/28/2026 (1M test miles still required; Teamsters suit pending) | [CA DMV](https://www.dmv.ca.gov/portal/?p=321530) |
| Maryland notarized bill of sale | Repealed by HB 251 (2026) | [MGA](https://mgaleg.maryland.gov/mgawebsite/Legislation/Details/hb0251?ys=2026RS) |
| Federal hiring | Self-assessment questionnaires ended. Skills tests went from near zero to **34%** of announcements; USA Hire grew from 138 to 412 occupational series | [OPM report, 2026](https://www.opm.gov/about-us/reports-publications/agency-reports/chance-to-compete-act-of-2024-governmentwide-implementation-plan-for-transition-to-technical-assessments-report-to-congress.pdf) |
| DHS paperwork cut | **21M hours** cut, e.g. TWIC renewal moved online with no in-person visit | [OIRA 2023](https://bidenwhitehouse.archives.gov/wp-content/uploads/2023/07/OIRA-2023-Burden-Reduction-Report.pdf) |
| DOJ Privacy Act requests | 28 CFR 16.41(d) now accepts "approved digital services" for identity | DOJ |
| Hawaii digital seals | Engineers' digital seals allowed since 9/22/2023 | [HAR 16-115-9](https://cca.hawaii.gov/pvl/files/2013/08/115-C-EASLA-09222023.pdf) |

## 5. Method and limits
- Nine research passes, one per domain: identity, benefits, health, procurement, permitting, records, justice, AI, and overall benchmarks. Every source was fetched during research.
- Some official sites block automated access (leginfo.ca.gov, ecfr.gov HTML, fcc.gov, usda.gov). For these we used official APIs or reputable mirrors (Cornell LII, public.law), noted per case.
- Government cost figures are often old (e.g. the IRS FY2020 unit cost, CEQ 2013–18 page counts) or self-reported (GAO's FedRAMP estimates). Each case states this.
- Dropped for weak evidence:
  - state paper-warrant mandates
  - probation in-person reporting statutes (states already allow remote)
  - Texas mail-in birth-certificate notarization (agency policy, and an online channel exists)
  - "45% of states spend >80% on IT maintenance" (unverified)
