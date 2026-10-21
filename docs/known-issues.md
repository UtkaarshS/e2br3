# Known issues (v0.1, milestones 1–3)

Problems found while testing against the public samples. Nothing here was "fixed" by bending a test: each golden-value row affected is tagged with its `KI-n` in `tests/golden/ich_examples.json`, and the test asserts that it still differs, so a fix on either side gets noticed.

## Golden-value match rate (FR-2)

**222 of 237 transcribed core-subset cells match (93.7%).** The other 15 are KI-1 to KI-5 below. Each is an error or a convention in the ICH spreadsheets, or a defect in a sample. None is a parser bug as far as I can tell. The SRS success criterion is 100%. That is not met as written, and it can't be met against these spreadsheets without overriding them.

**Decision:** Success criterion unchanged (100%). Reported as 222/237 raw; 237/237 when the 15 cells covered by KI-1…KI-5 are excluded. KI-1, KI-3, KI-4 and KI-5 were independently re-verified against the ICH sample XML on 2026-10-21.

| ID | Element | Files (rows) | Spreadsheet says | XML says / parser returns | Classification |
| --- | --- | --- | --- | --- | --- |
| KI-1 | N.1.1 | all 5 (row 6) | `ichicsr` | `name/@code="1"` in ICH code list 1 (`…1.1.1`) | The sheet shows the code's label, not the code. The parser keeps the code and does not decode ICH code lists. |
| KI-2 | G.k.4.r.10.2a/b | 1-1, 1-2 (row 244); 2-1, 2-2 (row 238) | `048` in the **10.2a** "TermID Version" row; 10.2b empty | `routeCode/@code="048"` with no `codeSystemVersion`, so 10.2b = `048` and 10.2a is absent | Spreadsheet row shift. The same sheets also swap F.r.2.2a/b and G.k.2.1.1a/b, both outside the core subset. |
| KI-3 | D.2.2b | 3 (row 91) | `Years` | `value/@unit="a"` (UCUM) | The sheet shows a label, not the UCUM code. |
| KI-4 | E.i.1.1b | 3 (row 167, columns D and E) | `gb` | `originalText/@language="GB"` for all three reactions | Case differs only for reactions 2 and 3. `GB` is also not an ISO 639-2 language code; English is `eng`. The sample is wrong too. |
| KI-5 | G.k.9.i.1 | 3 (row 254, columns C to E) | `fever`, `neutropenia`, `neutropenia` | Reactions have ids `rid-1`…`rid-3`, but the matrix references `r-id1`, `r-id3` (and the G.k.9.i.4 items `r-id2`) | A broken internal cross-reference in the ICH sample. The parser keeps the raw `reaction_id` and leaves `reaction_index=None`; it never guesses. The XSD can't catch this, because id references are not keys in the schema. |

Transcription notes, which are not mismatches:

- Example 3 E.i.4/E.i.5 (rows 179–180) are Excel date cells (`2003-05-11 00:00:00`). They were transcribed as `20030511` and `20030518`, with the original cell kept in the JSON `cell` field. An Excel date carries no TS precision.
- Example 3's sheet has one column per *iteration*. For G.k.9.i, the n-th column was matched to the n-th causality assessment in document order across all drugs. The sheet doesn't say which drug each column belongs to.
- The `.xls` sheets (examples 2-1, 2-2, 3) can't be read without `xlrd`, which is not installed and not allowed as a dependency. They were dumped once through the locally installed Excel (COM, read-only) by a throwaway script that is not in the repo. The `.xlsx` sheets were read with stdlib `zipfile` and lxml. The values were reviewed by hand against the XML.
- The `.xlsx` shared strings for the Japanese term contain furigana runs (`<rPh>`). Those were excluded, so `間質性肺炎` is compared, not `間質性肺炎カンシツセイハイエン`.

## Sample-data observations (not parser issues)

- **KI-6 (found in milestone 3, not a golden-value cell):** in FDA `FAERS2022Scenario5-3.xml`, two G.k drugs ("Drug Z (No drug exposure)" and "Drug X") carry the same internal id `59d6f5ce-…`. Since G.k.1 and G.k.9.i refer to drugs by id, the parser cannot tell them apart and gives both the same role and relatedness matrix. The parser was left unchanged. `to_rows()`/`to_frames()`/`to_csv` emit each G.k.9.i.2.r assessment exactly once and set `drug_index` to empty for it, so row counts still match the XML and nothing is attributed by guesswork. A test asserts this.
- Example 3 says `D.5 = 1` (male), but its narrative says "A 50 year-old female patient". The parser reports what D.5 says.
- The ICH Reference Instance v3.1 uses placeholder values (`C.1.1` = "C.1.1", `G.k.1` = "G.k.1"). It parses and validates, but it is useless for value checks.

## Scope and design notes

- **"28 public samples":** the fixture set holds 27 ICSR batches plus 1 ICH ACK reference instance. All 28 pass XSD validation; each is checked against the XSD for its own root element. `parse()` covers the 27 ICSRs. For the ACK it raises a clear `E2BParseError("…acknowledgement messages are out of scope")`, because the SRS puts ACKs out of scope. The test asserts this.
- **Bundled XSD (FR-5):** the SRS says "the bundled XSD v2.5", but the schemas are gitignored because their redistribution terms are unconfirmed. `validate()` therefore looks in this order: the `schema_dir=` argument, then `$E2BR3_SCHEMA_DIR`, then `schemas/ich-v2.5` in a checkout. Bundling has to wait until the licence question is answered.
- **DOCTYPE refused:** with `resolve_entities=False`, lxml still expands *internal* entities when the text is read through XPath `string()`, so a "billion laughs" payload would blow up at read time. `parse()` and `validate()` therefore refuse any document with a DOCTYPE. E2B(R3) is XSD-based and never needs one. External entities are never loaded, and a separate test checks this at parser level.
- **nullFlavor outside the IG set** (for example `OTH`, valid in HL7) raises `E2BParseError` and names the line. None of the samples contain one.
- **G.k.9.i:** only relatedness is modelled (G.k.9.i.1 and G.k.9.i.2.r.1–3), per the core subset. G.k.9.i.3 (intervals) and G.k.9.i.4 (recurrence) are not parsed yet, although example 3's sheet carries G.k.9.i.4.
- **Regional pass-through (FR-8):** an element counts as regional when its `codeSystem`, or an `id/@root`, falls under the EU arc `2.16.840.1.113883.3.989.5.1.1`, the FDA arc `…989.5.1.2`, or the NCI Thesaurus OID (`2.16.840.1.113883.3.26.1.1`, which FDA uses for its regional codes). Keys are the code-system OID plus the code, not the IG's `FDA.D.11.r.1`-style IDs, because mapping them would mean a regional mapping table, which is out of scope. **Assumption:** the NCI OID is treated as FDA-regional everywhere. An EU file that used NCI codes would be labelled `FDA:`. No sample does this.
- **Unverified:** IG section numbers in `mapping.py` comments use the data-element section IDs (C.1, E.i…). I could not cross-check the IG PDF page numbers in this session.
