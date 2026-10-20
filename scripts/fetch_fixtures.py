"""Download the public E2B(R3) sample files and ICH XSD set into tests/fixtures/ and schemas/.

Sources (official, publicly downloadable):
- FDA ICSR XML instances (FAERS2022 scenarios + ACKs): https://www.fda.gov/media/157983/download?attachment
- ICH Example Instances v2.0:                          https://www.fda.gov/media/157990/download?attachment
- ICH Reference Instances v3.1:                        https://www.fda.gov/media/157991/download?attachment
- ICH ICSR XML Schema Set v2.5:                        https://www.fda.gov/media/157992/download?attachment
- EMA EU example instances:                            https://www.ema.europa.eu/en/documents/other/european-union-example-instances-e2br3-testing-files_en.zip

Each archive is downloaded and extracted into its own folder. Inspect the result before relying on it.
"""
from __future__ import annotations

import io
import pathlib
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


def main() -> None:
    for rel, url in SOURCES.items():
        dest = ROOT / rel
        if dest.exists() and any(dest.iterdir()):
            print(f"skip  {rel} (already present)")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        print(f"fetch {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "e2br3-fixtures/0.1"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for member in zf.namelist():
                target = (dest / member).resolve()
                if not str(target).startswith(str(dest.resolve())):
                    raise RuntimeError(f"unsafe path in archive: {member}")
            zf.extractall(dest)
        print(f"ok    {rel}")


if __name__ == "__main__":
    main()
