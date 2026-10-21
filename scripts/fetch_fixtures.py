"""Download the public E2B(R3) sample files and ICH XSD set into tests/fixtures/ and schemas/.

Sources (official, publicly downloadable):
- FDA ICSR XML instances (FAERS2022 scenarios + ACKs): https://www.fda.gov/media/157983/download?attachment
- ICH Example Instances v2.0:                          https://www.fda.gov/media/157990/download?attachment
- ICH Reference Instances v3.1:                        https://www.fda.gov/media/157991/download?attachment
- ICH ICSR XML Schema Set v2.5:                        https://www.fda.gov/media/157992/download?attachment
- EMA EU example instances:                            https://www.ema.europa.eu/en/documents/other/european-union-example-instances-e2br3-testing-files_en.zip

fda.gov blocks scripted downloads (it redirects them to an "abuse detection" page).
If a source cannot be downloaded, this script prints a warning and continues, and
the tests that need that source skip. To get a blocked source, open its link in a
browser, save the zip, and pass it with --zip:

    python scripts/fetch_fixtures.py --zip schemas/ich-v2.5=C:/Downloads/schemas.zip

Exit codes: 0 if every source is present after the run, or if --allow-missing is
given; 1 otherwise. Each archive is extracted into its own folder. Inspect the
result before relying on it.
"""
from __future__ import annotations

import argparse
import io
import pathlib
import sys
import urllib.error
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = {
    "tests/fixtures/fda": "https://www.fda.gov/media/157983/download?attachment",
    "tests/fixtures/ich-examples": "https://www.fda.gov/media/157990/download?attachment",
    "tests/fixtures/ich-reference": "https://www.fda.gov/media/157991/download?attachment",
    "schemas/ich-v2.5": "https://www.fda.gov/media/157992/download?attachment",
    "tests/fixtures/ema": "https://www.ema.europa.eu/en/documents/other/european-union-example-instances-e2br3-testing-files_en.zip",
}


def _extract(data: bytes, dest: pathlib.Path) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise RuntimeError(f"unsafe path in archive: {member}")
        dest.mkdir(parents=True, exist_ok=True)
        zf.extractall(dest)


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "e2br3-fixtures/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        if "apology" in resp.geturl():
            raise RuntimeError("blocked by the site's bot protection")
        return resp.read()


def _present(dest: pathlib.Path) -> bool:
    return dest.is_dir() and any(dest.iterdir())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--zip",
        action="append",
        default=[],
        metavar="FOLDER=PATH",
        help="extract a manually downloaded zip into FOLDER (e.g. schemas/ich-v2.5=schemas.zip)",
    )
    ap.add_argument(
        "--allow-missing",
        action="store_true",
        help="exit 0 even if some sources could not be fetched (used by CI)",
    )
    args = ap.parse_args(argv)

    manual: dict[str, pathlib.Path] = {}
    for item in args.zip:
        folder, sep, path = item.partition("=")
        folder = folder.strip().replace("\\", "/")
        if not sep or folder not in SOURCES:
            ap.error(f"--zip expects FOLDER=PATH with FOLDER one of: {', '.join(SOURCES)}")
        manual[folder] = pathlib.Path(path.strip())

    missing: list[str] = []
    for rel, url in SOURCES.items():
        dest = ROOT / rel
        if rel in manual:
            _extract(manual[rel].read_bytes(), dest)
            print(f"ok    {rel} (from {manual[rel]})", flush=True)
            continue
        if _present(dest):
            print(f"skip  {rel} (already present)", flush=True)
            continue
        print(f"fetch {url}", flush=True)
        try:
            _extract(_download(url), dest)
        except (urllib.error.URLError, RuntimeError, zipfile.BadZipFile, TimeoutError) as exc:
            print(f"WARN  {rel}: could not download ({exc})", flush=True)
            missing.append(rel)
            continue
        print(f"ok    {rel}", flush=True)

    if missing:
        print("\nMissing sources. Tests that need them will skip.", flush=True)
        print("Open each link in a browser, save the zip, then run:", flush=True)
        for rel in missing:
            print(f"  python scripts/fetch_fixtures.py --zip {rel}=PATH/TO/download.zip", flush=True)
            print(f"      link: {SOURCES[rel]}", flush=True)
        return 0 if args.allow_missing else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
