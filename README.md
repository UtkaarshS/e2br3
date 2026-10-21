# e2br3

A read-only Python library and CLI that validates **ICH E2B(R3) ICSR** XML and parses it into typed objects that export to JSON, CSV and pandas.

Status: **alpha, v0.1.0 unreleased.** Nothing is published yet. See [`CHANGELOG.md`](CHANGELOG.md).

- Spec and feasibility: [`docs/feasibility-srs.md`](docs/feasibility-srs.md)
- Known issues and sample-data problems: [`docs/known-issues.md`](docs/known-issues.md)
- Research notes (the standard, regional variants, existing tools, difficulty): [`docs/research.md`](docs/research.md)

## Install

Not on PyPI yet. From a checkout:

```
pip install .            # lxml + pydantic only
pip install ".[pandas]"  # adds pandas, for to_frames()
```

Python 3.10 or newer, on Windows or Linux.

## Quickstart: Python

```python
import e2br3

batch = e2br3.parse("case.xml")           # Batch (N.1) -> messages (N.2.r) -> icsr
icsr = batch.messages[0].icsr
icsr.safety_report_id                     # C.1.1
icsr.reactions[0].meddra.code             # E.i.2.1b, MedDRA LLT code as sent
icsr.drugs[0].relatedness                 # G.k.9.i, resolved to reactions by internal id
icsr.regional                             # FDA / EU regional elements, raw pass-through

errors = e2br3.validate("case.xml", schema_dir="schemas/ich-v2.5")  # [] when valid

data = batch.to_dict()                    # JSON-safe; a nullFlavor is {"nullFlavor": "UNK"}
text = batch.to_json(indent=2)
same = e2br3.Batch.model_validate_json(text)   # round-trips unchanged

tables = batch.to_rows("case.xml")        # {"cases": [...], "reactions": [...], "drugs": [...], "drug_reaction": [...]}
frames = batch.to_frames("case.xml")      # the same four tables as DataFrames (needs the pandas extra)
```

Every field is `value | Null(nullFlavor) | None`, where `None` means the element was absent. A nullFlavor is never collapsed to `None`. The four tables are keyed by `case_key` = `"<file>#<C.1.1>"`, and `drug_reaction` has one row per G.k.9.i.2.r assessment. The data-element-to-XPath table is in [`src/e2br3/mapping.py`](src/e2br3/mapping.py).

## Quickstart: CLI

```
e2br3 validate --schema-dir schemas/ich-v2.5 case.xml other.xml   # exit 0 if all valid, 1 if any fails
e2br3 show case.xml                                                # short human summary per ICSR
e2br3 to-json case.xml -o case.json                                # or to stdout without -o
e2br3 to-csv -o out/ *.xml                                         # cases/reactions/drugs/drug_reaction.csv
python -m e2br3 --help                                             # same CLI without the script
```

`to-csv` uses the standard `csv` module, so it works without pandas. Wildcards are expanded by the CLI itself, so they also work in cmd.exe and PowerShell. Errors are one line on stderr, never a traceback.

`validate` needs the ICH ICSR XML Schema Set v2.5 locally: pass `--schema-dir`, set `E2BR3_SCHEMA_DIR`, or run `python scripts/fetch_fixtures.py` in a checkout. It is not bundled (see below).

## Principles

- Read-only. No R3 writing in v0.1.
- Parsing is XXE-safe (`resolve_entities=False`, `no_network=True`), and documents with a DOCTYPE are refused. Schemas are never fetched from the network.
- Coded values are kept as code + OID + version + displayName. Nothing is looked up.

## Known issues

The ICH example golden values match 222 of 237 cells raw, and 237 of 237 when the 15 cells covered by documented spreadsheet or sample errors are excluded. Details, and the other sample-data problems, are in [`docs/known-issues.md`](docs/known-issues.md).

## Test data

The public FDA, EMA and ICH sample files and the ICH XSD set are not committed, because their redistribution terms are unconfirmed. Fetch them, then run the tests:

```
python scripts/fetch_fixtures.py
python -m pytest
```

## Licence and MedDRA

e2br3 is licensed under Apache-2.0 (see [`LICENSE`](LICENSE)).

**MedDRA:** e2br3 does not include, bundle or distribute MedDRA or any other licensed terminology (EDQM, WHODrug and so on). It only passes through the codes, code-system OIDs and versions that appear in your XML. MedDRA® is a registered trademark of ICH, and using MedDRA terms requires your own licence from the MSSO. The same applies to the ICH sample files and schemas, which are downloaded by a script and not redistributed here.
