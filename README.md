# e2br3

A read-only Python library and CLI that validates **ICH E2B(R3) ICSR** XML and parses it into typed objects that export to JSON and pandas.

Status: **pre-alpha, v0.1 in progress.** Nothing is published yet.

- Spec and feasibility: [`docs/feasibility-srs.md`](docs/feasibility-srs.md)
- Research notes (the standard, regional variants, existing tools, difficulty): [`docs/research.md`](docs/research.md)
- Early prototypes: [`scratch/prototype/`](scratch/prototype/) (not part of the package)

## Usage (v0.1 dev)

```python
import e2br3

batch = e2br3.parse("case.xml")           # Batch (N.1) -> messages (N.2.r) -> icsr
icsr = batch.messages[0].icsr
icsr.safety_report_id                     # C.1.1
icsr.reactions[0].meddra.code             # E.i.2.1b, MedDRA LLT code as sent
icsr.drugs[0].relatedness                 # G.k.9.i, resolved to reactions by internal id
icsr.regional                             # FDA.* / EU elements, raw pass-through

errors = e2br3.validate("case.xml")       # [] when the local ICH XSD v2.5 accepts it
```

The data-element-to-XPath table is in [`src/e2br3/mapping.py`](src/e2br3/mapping.py). Known gaps and sample-data problems are in [`docs/known-issues.md`](docs/known-issues.md).

## Principles
- Read-only. No R3 writing in v0.1.
- Never bundles MedDRA or other licensed dictionaries. Coded values are kept as code + OID + version + displayName.
- Parsing is XXE-safe (`resolve_entities=False`, `no_network=True`).
- Each field is `Value | NullFlavor | absent`; nullFlavor is never collapsed to `None`.

## Test data
The public FDA, EMA and ICH sample files and the ICH XSD set are not committed, because their redistribution terms are unconfirmed. Run:

```
python scripts/fetch_fixtures.py
```

## Licence
Apache-2.0.
