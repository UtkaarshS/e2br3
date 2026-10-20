# Research: E2B(R3) ICSR parser (Product 1) and PV outreach CRM (Product 2)

Research date: 19–20 Oct 2026. Labels used throughout:
- **[V]** verified from a primary source or by running code here.
- **[S]** secondary source only.
- **[U]** could not verify.
- **[I]** my inference.

---

## BLUF

1. **There is a real but narrow gap for the E2B(R3) parser.**
   - I found no Python, R or Java open-source library on PyPI or GitHub that parses ICH E2B(R3) HL7 v3 ICSR XML into typed objects.
   - The existing open-source tools fall into three groups:
     - FAERS quarterly-data parsers (R2-style `ichicsr` XML or ASCII);
     - LLM "agent" demos that *export* R3 XML;
     - the official ICH/EMA XSLT converters (R2↔R3).
   - The demand side is also narrow. Commercial safety databases (Argus, Veeva, ArisG and others) already import E2B, so PV BPOs do not need a parser. Likely users are academics, small vendors, developers of open-source signal tools, and people who receive EudraVigilance bulk downloads (which arrive as E2B(R3) XML).
2. **The project is technically feasible and cheap to start. I proved this here:**
   - I downloaded 27 public R3 sample files (FDA, EMA, ICH) and the ICH XSD v2.5.
   - All 27 validate against the XSD with `lxml` in about 0.04 s.
   - xsdata generated full bindings (707 classes) and parsed the samples.
   - A 30-line XPath prototype extracted C.1.1, E.i, G.k and H.1 from all 27.
   - The hard part is not parsing. It is the semantic mapping layer: data-element IDs to HL7 RIM paths, nullFlavor, repeating groups, and regional extensions.
3. **India changes the story in your favour.**
   - The IPC/PvPI *PV Guidance Document for MAHs v2.0 (2024)* says ICSRs "should be reported in current version of E2B XML format to NCC-PvPI".
   - Its FAQ says serious and non-serious ADRs go "in E2B-XML (R3) format via email" to CDSCO and PvPI.
   - Transport is email, not a gateway. No hard mandate date was found. [V]
4. **hypokrates exists, but the fit is weak.**
   - It is AGPL-3.0, has one maintainer (Bruno Escalhão, GitHub `bruno-portfolio`), 4 stars, and its last commit was 12 Jun 2026.
   - Its scope is *public* PV databases. E2B parsing fits only as an optional input adapter.
   - Ship the parser as your own permissive-licence library. Offer hypokrates an issue or adapter, not the core code.
5. **The CRM spreadsheet is not in Google Drive.**
   - I searched by title, full text and spreadsheet MIME type. The only spreadsheets present are the AI_Jobs sheets and a few shared ones.
   - **Do not build a custom CRM.** Your prior holds. A single sheet, or an Obsidian Base, measures the 60-attempt kill criterion with roughly 12 columns and 3 formulas.

---

# PRODUCT 1: E2B(R3) ICSR parser

## 1. The standard

### Versions [V]
Source: the ICH IG v5.03 PDF, document history.

| Date | Version | Status |
|---|---|---|
| Feb 2001 | E2B(M), renamed E2B(R2) in 2005; ICH ICSR DTD v2.1 | Step 4 |
| Nov 2012 | IG v5.0 | Reached Step 4 |
| Apr 2013 | v5.01 | Step 4 publication |
| Nov 2016 | v5.02 | Q&A corrections |
| **18 Jul 2025** | **v5.03** | "Editorial corrections and updates based on Q&A document" (Q&A integrated into the IG). Title page reads "Step3 … Assembly Approved". |

- Underlying message standard: **ISO/HL7 27953-2:2011**. The IG says other versions should not be used. [V] ([ICH guideline summary 2025](https://database.ich.org/sites/default/files/ICH_E2B(R3)_EWG_IWG_Guideline%20Summary_FINAL_2025_0626.pdf))
- ICH work plan, Feb 2025: Q&A to be folded into the IG; code list 8 updated for E2D(R1) alignment; ISO TC215 WG6 adding a logical-model Part 3 to ISO/HL7 27953. [V] ([work plan](https://database.ich.org/sites/default/files/ICH_E2BR3_EWG_WorkPlan_2025_0221.pdf))
- FDA states AEMS "is now accepting the new values for data element C.5.4", tied to the E2D(R1) information paper. [V] ([FDA AEMS E2B(R3) standards](https://www.fda.gov/drugs/fda-adverse-event-monitoring-system-aems/fda-adverse-event-monitoring-system-aems-e2br3-data-standards))

### Official documents and locations

| Item | Location | Status |
|---|---|---|
| IG v5.03 (Jul 2025) | https://database.ich.org/sites/default/files/ICH_E2B(R3)_EWG_IWG_ICSR_Implementation_Guide_(QA%20integration)_Step3_2025_0718_Assembly_Approved_0.pdf | [V] downloaded, 170 pp |
| ICH package page | https://ich.org/page/e2br3-individual-case-safety-report-icsr-specification-and-related-files | [V] exists; JavaScript-rendered, so links were not extractable |
| Package 1.09 contents (via PMDA mirror) | https://www.pmda.go.jp/int-activities/int-harmony/ich/0093.html | [V] see below |
| **ICH ICSR XML Schema Set v2.5** | https://www.fda.gov/media/157992/download?attachment | [V] downloaded, 167 XSDs |
| ICH Reference Instances v3.1 | https://www.fda.gov/media/157991/download?attachment | [V] |
| ICH Example Instances v2.0 | https://www.fda.gov/media/157990/download?attachment | [V] 5 XML + XLS |
| ICH OIDs (zip) and OID paper | https://www.fda.gov/media/83131/download?attachment , https://www.fda.gov/media/83122/download?attachment | [V] links exist; not downloaded |
| BFC Appendix I(B) | https://www.fda.gov/media/81913/download?attachment | [V] |
| BFC mapping spreadsheet | https://www.fda.gov/media/157987/download?attachment | [V] link exists |
| R2↔R3 conversion XSLTs | https://www.fda.gov/media/157988/download?attachment | [V] downloaded; contents are "EU BFC conversion v2.5" (`upgrade-icsr.xsl`, `downgrade-icsr.xsl`, etc.) |
| FDA page listing all of the above | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e2br3-electronic-transmission-individual-case-safety-reports-implementation-guide-data-elements-and | [V] |

Package 1.09, as listed on PMDA:
- IG v5.02
- BFC v2.03 and conversions v2.02
- Schema files v1.00
- Reference Instances v3.1
- Example Instances v1.0
- OID and code lists v2.9
- Technical Information v1.02
- Data Element Structure v1.10
- EU BFC v2.5
- Dose forms and routes user guide v1.1
- Core data elements and business rules v1.0

There is a version-label mismatch:
- PMDA lists "Schema files ver 1.00" and "Example Instances ver 1.0".
- FDA hosts "Schema Set version 2.5" and "Example Instances version 2.0".

I did not resolve which is newer. **[U]** Use the FDA-hosted set, which is what I validated against.

The EMA sample files reference `https://eudravigilance.ema.europa.eu/XSD/multicacheschemas/MCCI_IN200100UV01.xsd`. That URL returned a 245-byte HTML response, not an XSD, so it is not usable as a remote schema. [V] Ship local XSDs.

### Message structure [V] (from the IG and the sample files)
```
MCCI_IN200100UV01            ← batch wrapper (N.1: N.1.1 type, N.1.2 batch no., N.1.3 sender, N.1.4 receiver, N.1.5 date)
 └─ PORR_IN049016UV (1..n)   ← message wrapper (N.2.r.1–N.2.r.4), "repeat as necessary"
     └─ controlActProcess
         └─ subject/investigationEvent   ← the ICSR (C.1.1 id, H.1 narrative in <text>, C.1.4/C.1.5 dates)
             ├─ component/adverseEventAssessment/subject1/primaryRole  ← D patient, E.i reactions, F.r tests, G.k drugs (organizer code 4)
             ├─ outboundRelationship (SPRT) ← C.2.r primary source, C.4.r literature
             ├─ subjectOf1/controlActEvent  ← C.3 sender
             └─ subjectOf2/investigationCharacteristic ← C.1.3 report type, C.1.7, etc.
```
- The schema set also includes the acknowledgement wrappers (`MCCI_IN200101UV01`, `MCCI_IN000002UV01`). [V] (IG Appendix I(A))
- All 27 public samples hold exactly 1 message per batch. I found no multi-message batch sample. [V] Synthesise one for tests.

### Sections (IG table of contents) [V]
| Section | Content |
|---|---|
| **C.1** | Case identification: C.1.1 sender's ID, C.1.2 creation date, C.1.3 type, C.1.4/C.1.5 dates, C.1.6 documents, C.1.7 expedited, C.1.8 worldwide ID, C.1.9 other IDs, C.1.10.r linked reports, C.1.11 nullification/amendment |
| **C.2.r** | Primary source(s) |
| **C.3** | Sender |
| **C.4.r** | Literature reference(s) and included documents. This is directly relevant to PharmaCO literature monitoring. |
| **C.5** | Study identification: C.5.1.r registration, C.5.4 study type |
| **D** | Patient: D.1 initials, D.2 age, D.5 sex, D.7 history, D.8.r past drugs, D.9 death, D.10 parent |
| **E.i** | Reactions/events (repeating) |
| **F.r** | Tests and procedures (repeating) |
| **G.k** | Drugs (repeating), with nested G.k.4.r dosage, G.k.7.r indication, G.k.9.i drug–reaction matrix |
| **H** | Narrative (H.1), sender's diagnosis (H.3.r), comments, native-language summary (H.5.r) |

The IG's minimum valid ICSR has four elements: an identifiable patient, an identifiable reporter, one event, and one suspect or interacting drug. [V] (IG §3.3.1)

### Controlled vocabularies [V] (IG §3.2)
- **MedDRA** coded at LLT. OID `2.16.840.1.113883.6.163`. Only one MedDRA version per ICSR (also restated by FDA).
  - Licence warning from the MSSO: subscribers may not "publish, or otherwise distribute MedDRA Terminology"; examples must use fewer than 1,000 terms.
  - Use of MedDRA content in open-source or AI contexts accessible to non-subscribers is a violation. [V] ([MSSO data-sharing statement](https://files.meddra.org/www/Website%20Files/Welcome%20Pages/001418%20Statement%20on%20MedDRA%20Data%20Sharing.pdf), [T&Cs](https://www.meddra.org/node/2773))
  - **Implication: the parser must carry MedDRA codes as opaque integers and never bundle the dictionary.**
- **ISO IDMP**:
  - ISO 11615 MPID and ISO 11616 PhPID (G.k.2.1.x);
  - ISO 11238 substance (G.k.2.3.r.2b);
  - ISO 11239 dose form and route (G.k.4.r.9–11).
  - EDQM Standard Terms are the EU implementation of the ISO 11239 terms. EMA made them mandatory with R3 on 30 Jun 2022. [V] ([EMA EV e-reporting](https://www.ema.europa.eu/en/human-regulatory-overview/research-development/pharmacovigilance-research-development/eudravigilance/eudravigilance-electronic-reporting))
  - The IG allows temporary free text until IDMP vocabularies exist.
- **ISO 3166-1 alpha-2** (country) — OID `1.0.3166.1.2.2`, seen in every sample.
- **ISO 5218** (sex) — `1.0.5218`.
- **ISO 639-2** (language).
- **UCUM** (case-sensitive). F.r.3.3 test units allow the full UCUM list.
- **ICH code lists** under `2.16.840.1.113883.3.989.2.1.1.*` (1–27). The samples use about 23 distinct lists. [V]
- Code system *versions* in the ICH reference instances are not the latest. Senders must update them (IG note). [V]

### nullFlavor [V] (IG §3.3.6)
- Allowed codes: **NI, MSK, UNK, NA, ASKU, NASK, NINF, PINF**.
- NINF and PINF are only for F.r.3.2 test-result ranges.
- Not all nullFlavors are valid for all data types.
- Each element lists its allowed set; for example, C.2.r.x allows "MSK, ASKU, NASK, UNK".
- Observed in the samples:
  - FDA files: NI, ASKU, NASK, NA, NINF, PINF.
  - EMA files: UNK, NI, NA, PINF, NINF.
- Mandatory elements must appear even when empty, carrying a nullFlavor.
- **Design rule [I]:** model every field as `Value | NullFlavor | absent`, and never collapse these to `None`. That distinction matters for regulatory semantics.

## 2. Regional variants

### FDA [V]
**Timeline** (from the [AEMS electronic submissions page](https://www.fda.gov/drugs/fda-adverse-event-monitoring-system-aems/fda-adverse-event-monitoring-system-aems-electronic-submissions)):
- R3 accepted for postmarketing ICSRs from 16 Jan 2024, and for IND ICSRs from 1 Apr 2024.
- R3 **required for IND ICSRs via ESG NextGen from 1 Apr 2026**.
- R2 postmarketing ICSRs accepted through **30 Sep 2026**.
- **R3 required for all postmarketing ICSRs from 1 Oct 2026**.
- The Federal Register notice (6 Apr 2026, 2026-06660) confirms the 1 Oct 2026 date. ([FR](https://www.federalregister.gov/documents/2026/04/06/2026-06660/electronic-submission-of-postmarketing-individual-case-safety-reports-to-the-food-and-drug))
- The AEMS page calls this a "six-month extension". [I] The prior required date was therefore likely 1 Apr 2026. [U]

**FDA Regional Implementation Guide v3.1** (Aug 2024): https://www.fda.gov/media/180748/download [V]
- Regional elements include:
  - `FDA.C.1.7.1` local criteria report type
  - `FDA.C.1.12` combination product indicator
  - `FDA.C.5.5a` IND number where AE occurred
  - `FDA.C.5.5b` pre-ANDA number
  - `FDA.C.5.6.r` cross-reported IND
  - `FDA.D.11.r.1` race
  - `FDA.D.12` ethnicity
  - `FDA.G.k.10.1` specialised product category
  - `FDA.G.k.10a.r`
  - the device block `FDA.G.k.12.r.1–11`
- Dates use one format, `CCYYMMDD[hhmmss[.UUUU]][+/-ZZzz]`. Minimum precision is set per element in the business rules. **Future dates are not acceptable.** Metric units. One MedDRA version per ICSR.
- The per-element mandatory and precision rules are in the Excel file *FDA E2B(R3) Core and Regional Data Elements and Business Rules* (Apr 2024): https://www.fda.gov/media/175373/download?attachment [V link; contents not parsed — **U**]

Other FDA resources:
- FDA ICSR XML Instances (Jul 2024), 10 scenarios plus positive and negative ACK: https://www.fda.gov/media/157983/download?attachment [V]
- FDA online validator: https://faers-validator.fda.gov/LSMV/Validator [V link]. It is a web tool, not open source.

### EMA / EudraVigilance [V]
- R3 mandatory for all ICSRs and SUSARs since **30 Jun 2022**. EV does not accept R2.
- EU ICSR IG: EMA/51938/2013 Rev 2, updated 07/04/2021.
- Business-rule spreadsheets ZIP updated 29/08/2024.
- **EU example instances ZIP**: 11 test cases, file dates Jan 2026. Downloaded and all validated.
- Test-case RTFs updated 23/05/2025.
- Source for all of the above: [EMA EV e-reporting page](https://www.ema.europa.eu/en/human-regulatory-overview/research-development/pharmacovigilance-research-development/eudravigilance/eudravigilance-electronic-reporting).
- EVWEB "ICSR Download" bulk output is "a zip file containing ICH E2B(R3) format XML files". [S] (EVWEB manual v1.6 copy) This is a concrete parser use case for MAHs and their vendors.
- I found no open-source tools from EMA. EMA's BFC is a set of XSLTs. EMA's training slide warns that "a system should not be called E2B(R3) compliant if it uses these XSLTs" and that conversions must be done by the receiver only. [V] ([EMA BFC training](https://www.ema.europa.eu/en/documents/presentation/presentation-implementing-iso-icsr-ich-e2br3-submodule-b-backwards-and-forwards-conversion_en.pdf))

### India (CDSCO / PvPI)
- **IPC/NCC-PvPI *PV Guidance Document for MAHs, Version 2.0* (© 2024)** [V]. The quotes below are from the copy at https://ipc.gov.in/images/Guidance_Document_-_17.9.2024_5_mb.pdf.
  - §2.5: "The ICSR should be reported in current version of E2B XML format to NCC-PvPI, IPC."
  - FAQ Q1: "the MAH should submit serious ADRs in E2B-XML-(R3) format via email: pharma.covig@cdsco.nic.in and mah.nccpvpi-ipc@gov.in within 15 days".
  - FAQ Q2: non-serious "in E2B, XML format (R3)" within 90 days. The earlier v2 draft said 30 days.
- The earlier Jan 2024 draft (https://www.ipc.gov.in/images/PV_Guidance_Docs_for_MAH_Version_2_as_on_18.01.2024.pdf) only says to report by email, with no E2B wording. [V] The E2B(R3) wording therefore came in with the final v2.0.
- The IPC guidance page also hosts the ICH IG v5.02 PDF (https://ipc.gov.in/images/1_ICH_ICSR_Implementation_Guide_v5_02.pdf). [V link]
- **Transport is email. There is no gateway and no published Indian regional schema or business rules.** [V for email; U that no regional rules exist]
- CDSCO circular of 3 Jun 2026 on implementing PV systems under Schedule M: listed, but not read. [U for its content]
- ICH status: CDSCO joined as an ICH **observer** in Feb 2016. It was still not a full member as of Apr 2025. [S] ([FDAnews 2020](https://fdanews.com/articles/196280-ich-to-bring-india-on-board), [Business Standard Apr 2025](https://www.business-standard.com/health/india-should-expedite-efforts-to-become-full-ich-member-iscr-president-125040600369_1.html)) Status as of Oct 2026: **[U]**.
- VigiFlow eReporting for Industry exists at WHO-UMC, but I could not verify that India uses it for MAH submissions. **[U]**
- **[I] Implication for PharmaCO and the BPOs:**
  - Indian BPOs already produce R3 for FDA and EMA clients through commercial safety databases.
  - The India-specific need is lighter-weight: validating, reading and QC-ing R3 XML that is emailed around. That is a credible niche for a validate-and-inspect CLI.

## 3. Existing tools: is there a gap?

Stars and last-commit dates come from the GitHub repo pages and commit Atom feeds, read 19–20 Oct 2026. The GitHub API was blocked in this session, so these were read through Exa page fetches.

| Tool | Lang | Stars | Licence | Last commit | What it covers | R3 parse? |
|---|---|---|---|---|---|---|
| [ICH/EMA BFC XSLTs](https://www.fda.gov/media/157988/download?attachment) (EU BFC v2.5) | XSLT | n/a | not stated **[U]** | n/a | R2↔R3 conversion | No (it converts, not parses) |
| [FDA/openfda](https://github.com/FDA/openfda) | Python | 717 | CC0 | 2026-06-08 | FAERS quarterly XML/SGML → JSON (R2-style `ichicsr`) | No |
| [WangLabCSU/faers](https://github.com/WangLabCSU/faers) (Bioconductor) | R | 47 | "Other" | 2026-09-29 | FAERS quarterly ASCII/XML, dedup, signals | No (FAERS quarterly XML) |
| [faersquarterlydata](https://github.com/luisgarcez11/faersquarterlydata) (CRAN v1.3.0) | R | 0 | GPL-3 | 2024-06-22 | FAERS XML/ASCII to tibbles | No |
| [JulesBa-Git/FAERS-xml-parser](https://github.com/JulesBa-Git/FAERS-xml-parser) | C++ | 0 | MIT | 2025-01-17 | FAERS XML to CSV | No |
| [vigipy](https://github.com/Shakesbeery/vigipy) (PyPI 3.4.2) | Python | 14 | GPL-3 | 2026-10-18 | Disproportionality | No input parser for E2B |
| [hypokrates](https://github.com/bruno-portfolio/hypokrates) (PyPI 0.7.1) | Python | 4 | AGPL-3.0 | 2026-06-12 | 15 public DBs, signals, MCP | No |
| [PrashantRGore/icsr-multi-agent-pipeline](https://github.com/PrashantRGore/icsr-multi-agent-pipeline) | Python | 0 | MIT (README) | 2026-10-08 | LLM pipeline; *exports* R3-"structured" XML; validates only well-formedness | No (export only) |
| [wissalbenothmen/pharmavig-ai](https://github.com/wissalbenothmen/pharmavig-ai) | Py/TS | 0 | MIT | 2026-05-22 | Signals, claims R3 export | No |
| [TaraSPande/pharmacovigilance-agent](https://github.com/TaraSPande/pharmacovigilance-agent) | Python | 0 | none listed | 2025-12-04 | LLM, text to R3 | No |
| [WeDoCareGlobal-CC/pharma-intelligence-os](https://github.com/WeDoCareGlobal-CC/pharma-intelligence-os) | TS | 0 | Apache-2.0 | 2026-10-14 | Dashboard, "R3 packages" | Unclear **[U]** |
| [molszewski423/pv-workbench](https://github.com/molszewski423/pv-workbench) | Python | 0 | none listed | 2026-10-07 | Local-LLM PV (FAERS) | No |
| [mirko1978/ema](https://github.com/mirko1978/ema) | Java | 4 | none | 2014-07-15 | EMA messaging POC, R2 DTD | No |
| [nexvigilant/.true](https://github.com/nexvigilant/.true) `icsr.rs` | Rust | **[U]** | **[U]** | **[U]** | ICSR struct "modelled after" R3; no XML parser seen | No |
| HL7 FHIR APIX IG | FHIR | n/a | n/a | CI build | Fictional R3 example, "not validated" | No |
| [xsdata](https://github.com/tefra/xsdata) | Python | 452 | MIT | 2026-10-17 | Generic XSD→dataclass generator (tested here) | Enabler only |
| PyPI `e2b` 2.56.0 | — | — | — | — | **Name collision**: E2B agent-sandbox SDK | — |
| PyPI `icsr` 0.0.12 | — | — | — | 2023 | Name collision: "Metrics for ICSR prediction" | — |

- PyPI names checked through the JSON API: `e2br3, e2b-r3, e2b_r3, pye2b, e2b-parser, icsr-parser, pyicsr, hl7-icsr, e2b-validator`, and others. **All are free** as of 19 Oct 2026. [V]
- PyPI full-text search was blocked by a JavaScript challenge, so packages with unusual names may have been missed. **[U]**
- Commercial importers exist (Oracle Argus Interchange, Veeva Vault Safety, CRScube's Java StAX importer). These are not open source. [S]

**Verdict [I]:** there is a genuine gap for an open, typed, validating R3 reader in Python. The weakness is demand, not supply. Target users:
- academics working on EudraVigilance or partner E2B exports;
- open-source PV tool developers;
- QC and validation people in BPOs and small MAHs;
- you, for PharmaCO's C.4.r literature cases.

It is a strong *portfolio* signal for PV-tech job applications even if adoption stays small.

## 4. hypokrates [V]

| Field | Value |
|---|---|
| Purpose | "Normalizes and cross-references 15 global pharmacovigilance and drug safety databases, exposing them via MCP", for hypothesis generation, not clinical use |
| PyPI | https://pypi.org/project/hypokrates/ — v0.7.1. Only 0.7.0 and 0.7.1 are on PyPI, both released 2026-03-17. Python ≥3.11. Alpha. |
| Repo | https://github.com/bruno-portfolio/hypokrates. PyPI metadata still points to `brunoescalhao/hypokrates`, which returned 404/403 here. |
| Maintainer | Bruno Escalhão (single contributor, 104 commits) |
| Licence | **AGPL-3.0-only**. Changed from MIT in 0.7.0 "to protect against commercial appropriation". |
| Activity | 4 stars, 1 fork, 0 open issues, last commit 2026-06-12 |
| Deps | duckdb, httpx, pydantic 2, rapidfuzz, scipy; mypy strict; coverage gate 85% |
| Contribution guide | [CONTRIBUTING.md](https://raw.githubusercontent.com/bruno-portfolio/hypokrates/main/CONTRIBUTING.md): issue first for features ("describe the use case"); fork and branch `feat/...`; tests mandatory; golden data in `tests/golden_data/`; mocked HTTP via respx; Google docstrings; **commit messages in Portuguese**; "every HTTP call goes through DuckDB" cache; contributions licensed AGPL-3.0 |
| Scope fit | Modules are per-*source* (faers, faers_bulk, canada, jader, …). No E2B or ICSR mention anywhere. |

**Fit assessment [I]:**
- hypokrates consumes *public* aggregated databases. There is no public E2B(R3) bulk dataset to plug in.
- An E2B parser fits only as an optional local-file source, for example "load my EV/partner E2B export into the stats engine".
- AGPL is viral. Contributing the core parser there would AGPL-license it and deter vendor use.
- **Recommendation:** keep a permissive library (Apache-2.0 or MIT) as your own repo. Then open a hypokrates issue proposing an `e2b` local source that depends on your package. Accept that the maintainer may decline, since this is one person with a public-data focus.

## 5. Public test files [V]

27 XML files were downloaded and **all 27 pass XSD validation** against the ICH Schema Set v2.5 with lxml 6.1.3:
- FDA FAERS2022 Scenarios 1–8 (10 XML), including the "mega" Scenario 6 (2 MB, "containing all elements"). There are also positive and negative ACK examples. ([zip](https://www.fda.gov/media/157983/download?attachment))
- EMA test cases 01A–10 (11 XML: SE, US, JP, DE, EE, LV, FR, ES origins). ([zip](https://www.ema.europa.eu/en/documents/other/european-union-example-instances-e2br3-testing-files_en.zip))
- ICH Example Instances v2.0: literature initial, nullification, new-number initial and follow-up, clinical trial. These come with XLS describing expected values, which is useful as golden truth.
- ICH Reference Instance v3.1 (ICSR and ACK).

Gaps:
- no multi-message batch;
- no R2 files, except via the BFC downgrade XSLT;
- no Indian sample.

Redistribution terms for these samples are not stated. **[U]** Download them in a test fixture script rather than committing them.

## 6. Difficulty

**R2 vs R3** [V] (BFC appendix and the EMA BFC slides). The changes fall into these categories:
- **Dates**: R2 has separate value and format fields; R3 uses one HL7 TS with variable precision and time zone.
- **Code mapping**: code lists changed.
- **Deletions and additions**: fields removed and new fields added.
- **Field lengths**: narrative went from 20k to 100k characters [S]. R3→R2 downgrades truncate into the narrative.
- **Masking**: nullFlavor replaces R2 conventions.
- **Structure**: R2 `ichicsr` is flat SGML-style XML; R3 is HL7 v3 RIM, with generic `observation code="…"` patterns.
- **Units**: the R2→R3 BFC maps units to a limited UCUM list and falls back to `{..}` curly-bracket units.

**Why parsing is harder than it looks [V from samples, I for effort]:**
- Most data elements are identified by `code`/`codeSystem` pairs on generic `observation` nodes, not by element names. For example, reactions are `observation[code=29, codeSystem=…1.1.19]`.
- A usable parser needs a curated **data-element-ID → XPath table** (C.1.1 … H.5.r) of roughly 250+ elements. **[U]** I did not count exactly.
- Repeating groups nest: G.k → G.k.4.r dosages and G.k.9.i drug–reaction relatedness, which cross-references reactions by internal ids.
- Mandatory-but-null elements and regional extensions (FDA.*, EU) live in the same tree.
- **xsdata test [V]:** generation from the batch XSD failed with "Circular Dependencies" in the default style. It succeeded with `--structure-style single-package`, producing 707 classes in one 43,486-line module. It parsed FAERS Scenario 6 in 0.08 s.
  - These are HL7 RIM-shaped classes, not E2B-shaped.
  - **[I]** Use them only optionally. The public API should be a hand-written E2B-element model (pydantic) filled by XPath.
- **[I]** Expect the bulk of effort in the mapping table plus nullFlavor and type handling, not in XML I/O.

## 7. Likely users and adoption [I unless marked]
- **PV BPOs** (APCER, IQVIA and others): low need. Their safety databases import and export E2B. Possible need for lightweight QC and diff tools.
- **Academics**: moderate, if they receive E2B exports from EV, from partners, or via PvPI. Most academic FAERS work uses ASCII or openFDA JSON, which the existing R and Python tools already cover.
- **Open-source signal tools** (vigipy, hypokrates, R `faers`): currently fed by public aggregates, so E2B is not their input. Adoption would come only through a "bring your own E2B" adapter.
- **India**: PvPI's R3-over-email expectation [V] creates a plausible need for small MAHs and BPO QC teams to validate, view and convert R3 files without a commercial database. Demand size is **[U]**.
- **You**: a high-value portfolio piece for PV-tech roles. It is also a dogfood path, since PharmaCO literature hits could be emitted or checked as C.4.r ICSRs (write support is *not* MVP).

## 8. Realistic MVP scope (for the SRS)

**In scope (v0.1):**
1. `parse(path) -> Batch` built on lxml with `resolve_entities=False, no_network=True` (XXE-safe). Model: `Batch(N.1) → Message(N.2.r) → ICSR`.
2. Pydantic v2 models for a **core subset**:
   - C.1.1–C.1.5, C.1.8.1, C.1.11;
   - C.2.r (qualification, country);
   - C.4.r literature;
   - D.1/D.2.2/D.5;
   - E.i (verbatim, MedDRA LLT code and version, dates, seriousness flags, outcome);
   - G.k (role, product name, substance, dosage text/route, action taken, G.k.9.i relatedness);
   - H.1 narrative.
   - Each field typed as `Value | NullFlavor`.
3. Opaque code handling. MedDRA, EDQM and UCUM are stored as code + system OID + version + displayName. **No bundled dictionaries** (MedDRA licence).
4. `validate(path)` against the bundled ICH XSD v2.5, returning structured errors with line numbers.
5. Export via `to_dict()` and `to_json()`, plus `to_frames()` returning tidy pandas tables keyed by case: cases, reactions, drugs, drug_reaction.
6. CLI (Typer or argparse): `e2br3 validate|show|to-json|to-csv FILE...`.
7. Tests: the 27 public samples (downloaded by script), golden values from the ICH example XLS, and one synthetic multi-message batch.
8. CI on Windows and Linux.

**Out of scope (v0.1):**
- writing or generating R3;
- R2 parsing (offer the BFC XSLT path later);
- FDA, EU and India business-rule validation;
- regional FDA.* elements beyond pass-through;
- ACK messages;
- attachments (beyond base64 pass-through).

**Pre-registered criteria (suggested) [I]:**
- **Success at 8 weeks:**
  - all 27 public samples parse with 0 exceptions;
  - core fields match the ICH example golden values 100%;
  - published to PyPI;
  - one external issue, PR or star from a non-friend, *or* a hypokrates maintainer response;
  - used in PharmaCO for one real flow.
- **Kill or freeze:**
  - no external signal in 12 weeks after a public post; *or*
  - the mapping layer exceeds the core subset before v0.1 ships (scope creep); *or*
  - it displaces job-search hours below your floor.

---
