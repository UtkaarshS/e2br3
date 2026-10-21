# e2br3 — E2B(R3) ICSR Parser: Feasibility & SRS

Oct 20, 2026 · @Utkaarsh

## Verdict

**Go, but as a time-boxed portfolio and open-source project, not a product.** The technical risk is low: all 27 public R3 sample files validate and parse with lxml today. The gap is real, since no open-source library reads E2B(R3) ICSRs into typed objects in any language. Demand is narrow, because commercial safety databases already import E2B.

- **Why build it:** a high-signal portfolio piece for PV-tech jobs, a dogfood path for PharmaCO's literature cases (section C.4.r), and India's PvPI now asks MAHs for E2B(R3) by email, which creates a QC and validation niche.
- **Why keep it small:** almost no one will pay for it. It must not displace job-search hours.
- **Licence:** ship it as your own Apache-2.0 library. Don't contribute the core to hypokrates (AGPL-3.0, one maintainer); offer an adapter through an issue instead.
- **Hard constraint:** never bundle MedDRA. Its licence forbids redistribution, so carry codes only.

## Feasibility study

Technical and regulatory feasibility are high, market feasibility is low, and legal feasibility holds as long as no MedDRA content ships.

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Technical | High | 27 public samples (FDA 10, EMA 11, ICH 6) pass XSD validation against ICH Schema Set v2.5 with lxml. A 30-line XPath prototype pulled C.1.1, E.i, G.k and H.1 from all 27. xsdata generated 707 HL7 classes, but only with the single-package option. |
| Main technical risk | Medium | The work is in the mapping layer: data-element IDs to XPath for roughly 250+ elements, nullFlavor handling, and nested repeating groups such as G.k.9.i, which cross-references reactions. XML input and output is not the problem. |
| Supply gap | Real | No open-source typed R3 reader exists. The existing tools cover adjacent jobs: FAERS quarterly parsers (openFDA, the R faers package), AI demos that only write R3, and ICH/EMA XSLT converters. The PyPI names `e2br3`, `pye2b` and `icsr-parser` are free. |
| Demand | Low to medium | BPOs use Argus, Veeva and ArisG, which already import E2B. Realistic users are academics with EudraVigilance or partner exports, open-source PV tool developers, small MAHs and QC teams, and you. |
| Regulatory pull | Rising | FDA has required R3 for postmarketing reports since 1 Oct 2026. EMA has required it since 30 Jun 2022. PvPI guidance v2.0 (2024) asks MAHs for E2B-XML (R3) by email, within 15 days for serious cases and 90 days for non-serious ones. |
| Legal | OK, with a constraint | The MedDRA licence forbids distributing the terminology, so ship codes and OIDs only. Redistribution terms for the sample files are unknown, so download them in a test script rather than committing them. Use the Apache-2.0 licence. |
| hypokrates fit | Weak | It is AGPL-3.0 with one maintainer, 4 stars, a last commit on 12 Jun 2026, Portuguese commit messages, and a public-database scope. Offer an optional local-file adapter through an issue. |
| Opportunity cost | High | Every hour comes out of the job search, the top priority. This only pays off if it doubles as a portfolio asset and a LinkedIn post. |

### Risks

1. **Scope creep in the mapping table.** Mitigation: freeze a core subset for v0.1 (see the SRS).
2. **No adoption.** Mitigation: judge it as a portfolio piece first, and treat adoption as a bonus.
3. **Reaching into MedDRA by accident.** Mitigation: CI check that no dictionary files are in the package.
4. **Spec version confusion.** PMDA lists schema v1.00 while FDA hosts v2.5. Mitigation: pin to the FDA-hosted v2.5 that was validated here.

### Pre-registered criteria

- **Success:** 0 exceptions across all 27 public samples; 100% match on core fields against the ICH example golden values; published on PyPI; used in one real PharmaCO flow; and one external signal (a non-friend issue, PR or star, or a reply from the hypokrates maintainer).
- **Kill or freeze:** no external signal within 12 weeks of a public post; or the mapping grows past the core subset before v0.1 ships; or it pushes job-search hours below your weekly floor.

## Software requirements specification (v0.1)

`e2br3` v0.1 is a read-only Python library and CLI. It validates ICH E2B(R3) ICSR XML and parses a core subset of fields into typed, JSON- and pandas-exportable objects.

### Purpose and users

- **Users:**
  - PV researchers and analysts holding R3 exports
  - QC staff at small MAHs and BPOs
  - open-source PV tool developers
  - PharmaCO, as the first internal consumer
- **Standard:** ICH E2B(R3) Implementation Guide v5.03 (Jul 2025), the ICH ICSR XML Schema Set v2.5, and ISO/HL7 27953-2:2011.

### Functional requirements

| ID | Requirement | Acceptance test |
| --- | --- | --- |
| FR-1 | `parse(path) -> Batch`, structured as Batch (N.1) → Message (N.2.r) → ICSR | All 27 public samples plus 1 synthetic multi-message batch parse with 0 exceptions |
| FR-2 | Typed core-subset models (pydantic v2), listed below | Fields match the ICH Example Instances v2.0 XLS golden values 100% |
| FR-3 | Every field is `Value \| NullFlavor \| absent`, never collapsed to None. The NullFlavor codes are NI, MSK, UNK, NA, ASKU, NASK, NINF and PINF | Unit tests for each flavor seen in the FDA and EMA samples |
| FR-4 | Coded values are stored as code + system OID + version + displayName, with no dictionary lookup | MedDRA LLT codes round-trip unchanged |
| FR-5 | `validate(path)` checks against a locally fetched ICH XSD Set v2.5 (not bundled: it contains third-party HL7 schemas; decided 2026-10-21) and returns errors with line numbers | Known-bad fixtures produce the expected errors |
| FR-6 | Export: `to_dict()`, `to_json()`, and `to_frames()` returning cases, reactions, drugs and drug\_reaction tables keyed by case | Row counts match the source XML |
| FR-7 | CLI: `e2br3 validate \| show \| to-json \| to-csv FILE...` | Runs on Windows and Linux |
| FR-8 | Regional elements (FDA.\*, EU) are kept as raw pass-through key–value pairs | FDA scenario files keep their FDA.\* nodes |

**Core field subset:**

- **Case:** C.1.1–C.1.5, C.1.8.1, C.1.11
- **Primary source:** C.2.r qualification and country
- **Literature:** C.4.r
- **Patient:** D.1, D.2.2, D.5
- **Reactions (E.i):** verbatim term, MedDRA LLT code and version, dates, seriousness flags, outcome
- **Drugs (G.k):** role, product name, substance, dosage text and route, action taken, G.k.9.i relatedness
- **Narrative:** H.1

### Non-functional requirements

- **Security:** parse with lxml `resolve_entities=False` and `no_network=True` (XXE-safe), and never fetch remote schemas. The EMA's remote XSD URL returns HTML, not a schema.
- **Performance:** the 2 MB FDA Scenario 6 file parses in under 0.5 s on a laptop. The baseline here was 0.08 s with xsdata.
- **Portability:** Python ≥ 3.10, Windows and Linux CI. Dependencies are lxml and pydantic only.
- **Licensing:** Apache-2.0, with no MedDRA, EDQM or other licensed dictionaries in the package (enforced by a CI check).
- **Quality:** ≥ 85% test coverage, mypy strict, and fixtures downloaded by script rather than committed.

### Out of scope for v0.1

- Writing or generating R3
- R2 parsing (point users to the ICH/EMA conversion XSLTs)
- FDA, EU or India business-rule validation
- ACK messages
- Attachments beyond base64 pass-through
- A hypokrates adapter (comes after v0.1)

### Test data

- FDA FAERS2022 Scenarios 1–8 (10 XML files, including the all-elements Scenario 6) plus ACK examples
- EMA test cases 01A–10 (11 XML files)
- ICH Example Instances v2.0 with golden-value XLS, and Reference Instance v3.1
- 1 synthetic multi-message batch (no public sample exists)
- No Indian sample exists; ask a PvPI contact

### Milestones

1. Mapping table for the core subset, plus the models (FR-2, FR-3, FR-4)
2. `parse` and `validate` with tests on all public samples (FR-1, FR-5)
3. Export functions and CLI, then the first PyPI release (FR-6, FR-7)
4. Wire it into PharmaCO, write the public post, open the hypokrates issue

### Open questions

- Which is current: schema v1.00 as listed by PMDA, or v2.5 as hosted by FDA? v2.5 was used here.
- Does PvPI accept Indian regional data elements, and does India route submissions through VigiFlow? Unverified.
- What do the per-element rules in FDA's business-rules Excel file (Apr 2024) say? Not yet read.

## Sources

- [ICH E2B(R3) IG v5.03 (Jul 2025)](<https://database.ich.org/sites/default/files/ICH_E2B(R3)_EWG_IWG_ICSR_Implementation_Guide_(QA%20integration)_Step3_2025_0718_Assembly_Approved_0.pdf>)
- [FDA E2B(R3) IG and data-element files page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e2br3-electronic-transmission-individual-case-safety-reports-implementation-guide-data-elements-and)
- [ICH ICSR XML Schema Set v2.5](https://www.fda.gov/media/157992/download?attachment)
- [FDA AEMS electronic submissions timeline](https://www.fda.gov/drugs/fda-adverse-event-monitoring-system-aems/fda-adverse-event-monitoring-system-aems-electronic-submissions)
- [FDA Regional IG v3.1](https://www.fda.gov/media/180748/download)
- [EMA EudraVigilance e-reporting](https://www.ema.europa.eu/en/human-regulatory-overview/research-development/pharmacovigilance-research-development/eudravigilance/eudravigilance-electronic-reporting)
- [PvPI Guidance Document for MAHs v2.0](https://ipc.gov.in/images/Guidance_Document_-_17.9.2024_5_mb.pdf)
- [MedDRA data-sharing statement](https://files.meddra.org/www/Website%20Files/Welcome%20Pages/001418%20Statement%20on%20MedDRA%20Data%20Sharing.pdf)
- [hypokrates](https://github.com/bruno-portfolio/hypokrates)
- [xsdata](https://github.com/tefra/xsdata)
