"""FR-7 command-line interface (stdlib ``argparse`` only).

::

    e2br3 validate [--schema-dir DIR] FILE...
    e2br3 show FILE...
    e2br3 to-json [-o FILE] [--indent N] FILE...
    e2br3 to-csv -o DIR FILE...

Also runnable as ``python -m e2br3``.

Exit codes: 0 success; 1 a file failed validation or could not be read or
parsed; 2 usage error or the ICH XSD set is missing. User errors are reported
on stderr in one line, never as a traceback.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from . import __version__
from .export import COLUMNS, SERIOUSNESS, TABLES, cell, to_rows
from .models import Batch, Coded, ICSR, Quantity
from .parse import E2BParseError, parse
from .validate import SchemaNotFoundError, validate

PROG = "e2br3"

# Display labels for three tiny public code lists (ICH code lists for C.1.3 and
# G.k.1, ISO 5218 for D.5). Used by `show` only; exports keep the raw codes.
REPORT_TYPES = {"1": "spontaneous report", "2": "report from study", "3": "other", "4": "not available to sender"}
SEXES = {"0": "unknown", "1": "male", "2": "female", "9": "not applicable"}
DRUG_ROLES = {"1": "suspect", "2": "concomitant", "3": "interacting", "4": "drug not administered"}
SUSPECT_ROLES = {"1", "3"}
MAX_LISTED = 5


class _Fail(Exception):
    """A user-facing error for one file: reported on stderr, exit code 1."""


def _err(msg: str) -> None:
    print(f"{PROG}: error: {msg}", file=sys.stderr)


def _load(path: str) -> Batch:
    try:
        return parse(path)
    except E2BParseError as exc:
        raise _Fail(f"{path}: {exc}") from None
    except OSError as exc:
        raise _Fail(f"{path}: cannot read file ({exc.strerror or exc})") from None


def _load_all(files: Sequence[str]) -> Optional[list[tuple[str, Batch]]]:
    """Parse every file; on any failure report all of them and return None."""
    out, failed = [], False
    for f in files:
        try:
            out.append((f, _load(f)))
        except _Fail as exc:
            _err(str(exc))
            failed = True
    return None if failed else out


def _safe_stdout() -> None:
    """Never crash on a console that cannot encode a character (e.g. cp1252 and Japanese).

    Piped or redirected output is written as UTF-8, so files and other programs get the
    real characters. An interactive console keeps its own encoding and escapes anything
    it cannot display.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        if sys.stdout.isatty():
            reconfigure(errors="backslashreplace")
        else:
            reconfigure(encoding="utf-8")
    except (ValueError, OSError):  # pragma: no cover
        pass


# --------------------------------------------------------------------------- validate


def cmd_validate(args: argparse.Namespace) -> int:
    _safe_stdout()
    failed = 0
    for f in args.files:
        if not Path(f).is_file():
            print(f"ERROR    {f}: no such file")
            failed += 1
            continue
        try:
            errors = validate(f, schema_dir=args.schema_dir)
        except SchemaNotFoundError as exc:
            _err(f"{exc} On the command line, use --schema-dir DIR.")
            return 2
        except OSError as exc:
            print(f"ERROR    {f}: cannot read file ({exc})")
            failed += 1
            continue
        if not errors:
            print(f"OK       {f}")
            continue
        failed += 1
        print(f"INVALID  {f} ({len(errors)} error{'s' if len(errors) != 1 else ''})")
        for e in errors:
            where = f"{e.line}" if e.column is None else f"{e.line}:{e.column}"
            print(f"  {f}:{where}: [{e.kind}] {e.message}")
    if len(args.files) > 1:
        print(f"{len(args.files) - failed} of {len(args.files)} file(s) valid")
    return 1 if failed else 0


# --------------------------------------------------------------------------- show


def _label(value: Any, labels: dict[str, str]) -> str:
    c = cell(value)
    if c is None:
        return "-"
    return f"{c} ({labels[c]})" if isinstance(value, Coded) and c in labels else str(c)


def _age(icsr: ICSR) -> str:
    age = icsr.patient.age if icsr.patient else None
    if isinstance(age, Quantity):
        return f"{cell(age.value)} {age.unit or ''}".strip()
    return str(cell(age) or "-")


def _listed(items: list[str]) -> str:
    if not items:
        return "none"
    shown = "; ".join(items[:MAX_LISTED])
    return shown + (f"; ... (+{len(items) - MAX_LISTED} more)" if len(items) > MAX_LISTED else "")


def summary(icsr: ICSR) -> list[str]:
    """Human summary lines for one ICSR (used by ``e2br3 show``)."""
    reactions = []
    for rx in icsr.reactions:
        term = cell(rx.native_term) or cell(rx.translated_term) or "?"
        flags = [n.replace("_", " ") for n in SERIOUSNESS if getattr(rx, n) is True]
        llt = f" [LLT {rx.meddra_code}]" if rx.meddra_code else ""
        reactions.append(f"{term}{llt}" + (f" (serious: {', '.join(flags)})" if flags else ""))
    suspects = []
    for drug in icsr.drugs:
        role = cell(drug.role)
        if role in SUSPECT_ROLES:
            name = cell(drug.product_name) or "; ".join(str(cell(s)) for s in drug.substances) or "?"
            suspects.append(f"{name} ({DRUG_ROLES[role]})")
    criteria = sorted({n.replace("_", " ") for rx in icsr.reactions for n in SERIOUSNESS if getattr(rx, n) is True})
    sex = icsr.patient.sex if icsr.patient else None
    return [
        f"  C.1.1  {cell(icsr.safety_report_id) or '-'}",
        f"  Report type  {_label(icsr.report_type, REPORT_TYPES)}",
        f"  Patient  sex {_label(sex, SEXES)}, age {_age(icsr)}",
        f"  Reactions ({len(icsr.reactions)})  {_listed(reactions)}",
        f"  Suspect drugs ({len(suspects)} of {len(icsr.drugs)})  {_listed(suspects)}",
        f"  Serious  {'yes: ' + ', '.join(criteria) if criteria else 'no criterion marked true'}",
    ]


def cmd_show(args: argparse.Namespace) -> int:
    _safe_stdout()
    failed = False
    for f in args.files:
        try:
            batch = _load(f)
        except _Fail as exc:
            _err(str(exc))
            failed = True
            continue
        icsrs = batch.icsrs
        print(f"{f}  ({len(icsrs)} ICSR{'s' if len(icsrs) != 1 else ''})")
        for i, icsr in enumerate(icsrs, 1):
            if len(icsrs) > 1:
                print(f" ICSR {i}")
            print("\n".join(summary(icsr)))
    return 1 if failed else 0


# --------------------------------------------------------------------------- to-json / to-csv


def cmd_to_json(args: argparse.Namespace) -> int:
    loaded = _load_all(args.files)
    if loaded is None:
        return 1
    if len(loaded) == 1:
        data: Any = loaded[0][1].to_dict()
    else:
        data = [{"file": f, "batch": b.to_dict()} for f, b in loaded]
    text = json.dumps(data, ensure_ascii=False, indent=args.indent) + "\n"
    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8")
        except OSError as exc:
            _err(f"{args.output}: cannot write file ({exc.strerror or exc})")
            return 1
        return 0
    sys.stdout.flush()
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:  # JSON is UTF-8, whatever the console code page
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:  # pragma: no cover
        sys.stdout.write(text)
    return 0


def cmd_to_csv(args: argparse.Namespace) -> int:
    loaded = _load_all(args.files)
    if loaded is None:
        return 1
    tables: dict[str, list[dict[str, Any]]] = {t: [] for t in TABLES}
    for f, batch in loaded:
        for t, rows in to_rows(batch, f).items():
            tables[t].extend(rows)
    out = Path(args.output)
    try:
        out.mkdir(parents=True, exist_ok=True)
        for t in TABLES:
            # utf-8-sig: the BOM makes Excel read the file as UTF-8 (non-Latin terms intact).
            with (out / f"{t}.csv").open("w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(COLUMNS[t]))
                writer.writeheader()
                writer.writerows(tables[t])
    except OSError as exc:
        _err(f"{out}: cannot write ({exc.strerror or exc})")
        return 1
    _safe_stdout()
    counts = ", ".join(f"{t}={len(tables[t])}" for t in TABLES)
    print(f"wrote 4 CSV files to {out} ({counts})")
    return 0


# --------------------------------------------------------------------------- main


def expand(files: Sequence[str]) -> list[str]:
    """Expand ``*``/``?``/``[`` patterns ourselves: cmd.exe and PowerShell pass them through literally."""
    out: list[str] = []
    for f in files:
        if not Path(f).exists() and any(ch in f for ch in "*?["):
            out.extend(sorted(glob.glob(f)) or [f])
        else:
            out.append(f)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=PROG, description="Validate and export ICH E2B(R3) ICSR XML (read-only).")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    v = sub.add_parser("validate", help="check files against the local ICH XSD v2.5")
    v.add_argument("--schema-dir", help="root of the ICH XSD set (contains multicacheschemas/)")
    v.add_argument("files", nargs="+", metavar="FILE")
    v.set_defaults(func=cmd_validate)

    s = sub.add_parser("show", help="print a short summary of each ICSR")
    s.add_argument("files", nargs="+", metavar="FILE")
    s.set_defaults(func=cmd_show)

    j = sub.add_parser("to-json", help="export to JSON (one file: the batch; several: a list)")
    j.add_argument("-o", "--output", metavar="FILE", help="write here instead of stdout")
    j.add_argument("--indent", type=int, default=2, help="indent width (default 2)")
    j.add_argument("files", nargs="+", metavar="FILE")
    j.set_defaults(func=cmd_to_json)

    c = sub.add_parser("to-csv", help="export cases/reactions/drugs/drug_reaction CSV tables")
    c.add_argument("-o", "--output", metavar="DIR", required=True, help="output directory")
    c.add_argument("files", nargs="+", metavar="FILE")
    c.set_defaults(func=cmd_to_csv)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    args.files = expand(args.files)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:  # pragma: no cover
        return 130
    except BrokenPipeError:  # pragma: no cover - output piped into `head` and the like
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
