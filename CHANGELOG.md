# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - Unreleased

First release. Nothing has been published yet.

### Added

- `parse(path | bytes) -> Batch`: reads an ICH E2B(R3) ICSR batch (N.1 → N.2.r → ICSR) into typed
  pydantic v2 models for the v0.1 core subset (C.1.1–C.1.5, C.1.8.1, C.1.11, C.2.r, C.4.r, D.1,
  D.2.2, D.5, E.i, G.k including G.k.9.i relatedness, H.1).
- Every field is `Value | Null(nullFlavor) | None (absent)`; nullFlavor is never collapsed to `None`.
- Coded values are kept as code + code-system OID + version + displayName, with no dictionary lookup.
- FDA and EU regional elements kept as raw key-value pass-through (`ICSR.regional`).
- `validate(path | bytes, schema_dir=None)`: XSD validation against a local ICH ICSR Schema Set v2.5,
  returning errors with line and column numbers.
- Export: `to_dict()` and `to_json()` (nullFlavor exported as `{"nullFlavor": "UNK"}`),
  `to_rows()` (four tidy tables as lists of dicts) and `to_frames()` (pandas DataFrames, optional
  `pandas` extra). Tables: `cases`, `reactions`, `drugs`, `drug_reaction`, keyed by
  `<file>#<C.1.1>`.
- CLI: `e2br3 validate | show | to-json | to-csv FILE...`, also as `python -m e2br3`.
- `to-csv` writes UTF-8 with a BOM, so Excel shows non-Latin terms correctly. Piped or redirected CLI output is UTF-8.
- `NOTICE` file acknowledging ICH copyright for transcribed example values, the HL7 schemas (not bundled) and MedDRA (never bundled).

### Security

- XXE-safe parsing (`resolve_entities=False`, `no_network=True`, no DTD loading); documents
  with a DOCTYPE are refused. Schemas are never fetched from the network.

### Known issues

- See [docs/known-issues.md](docs/known-issues.md): ICH golden values match 222/237 raw and
  237/237 when the 15 cells covered by KI-1 to KI-5 are excluded; KI-6 (a shared drug id in
  FDA Scenario 5-3) is handled in export without guessing.
- The ICH XSD set is not bundled until its redistribution terms are confirmed; `validate()`
  needs `schema_dir=`, `$E2BR3_SCHEMA_DIR` or a source checkout.
