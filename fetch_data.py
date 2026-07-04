"""
fetch_data.py
=============
Download the three Colorado House Final Status Sheet PDFs that the analysis
pipeline needs, and save them into ./data/ under the filenames the parser
expects.

These PDFs are the *primary source data* for the paper. They are public
records of the Colorado General Assembly and are not redistributed inside this
package; this script retrieves them directly from the Assembly's servers.

Usage
-----
    python fetch_data.py

If automatic download fails (e.g. the Assembly reorganizes its file paths, or
you are offline), download the three "House Final Status Sheet" PDFs manually
from the sources listed under MANUAL_SOURCES below and place them in ./data/
using the target filenames printed by this script.

The pipeline expects (see parse_status_sheets.SESSIONS):
    data/2022-house-final-status-sheet-accessible.pdf
    data/2023-house-final-status-sheet-accessible.pdf
    data/2024-house-final-status-sheet-accessible.pdf
"""

import os
import sys
import urllib.request

# Target filename (in data/) -> list of candidate source URLs (tried in order).
# The 2024 sheet is published as a "final status sheet"; the 2022/2023 sheets
# are the end-of-session House status sheets. If a URL 404s, try the manual
# sources below.
DOWNLOADS = {
    "2022-house-final-status-sheet-accessible.pdf": [
        "https://content.leg.colorado.gov/sites/default/files/2022_House_Status_Sheet.pdf",
    ],
    "2023-house-final-status-sheet-accessible.pdf": [
        "https://content.leg.colorado.gov/sites/default/files/2023_House_Status_Sheet.pdf",
    ],
    "2024-house-final-status-sheet-accessible.pdf": [
        "https://leg.colorado.gov/sites/default/files/2024_house_final_status_sheet.pdf",
    ],
}

MANUAL_SOURCES = """
Manual download sources (Colorado General Assembly, public records)
-------------------------------------------------------------------
  Bill / publication search:  https://leg.colorado.gov/bill-search
  Publication records:
      https://content.leg.colorado.gov/publications/2023-house-status-sheet
      https://content.leg.colorado.gov/publications/2024-house-status-sheet
  Direct files (if still hosted):
      https://content.leg.colorado.gov/sites/default/files/2022_House_Status_Sheet.pdf
      https://content.leg.colorado.gov/sites/default/files/2023_House_Status_Sheet.pdf
      https://leg.colorado.gov/sites/default/files/2024_house_final_status_sheet.pdf

Save each as ./data/<target-filename> exactly as listed above, then re-run
    python run_all.py
"""

DATA_DIR = "data"
_UA = {"User-Agent": "Mozilla/5.0 (reproduction-package; academic use)"}


def _download(url, dest):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if not data[:5].startswith(b"%PDF"):
        raise ValueError(f"downloaded content is not a PDF (starts with {data[:8]!r})")
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    ok, failed = 0, []
    for fname, urls in DOWNLOADS.items():
        dest = os.path.join(DATA_DIR, fname)
        if os.path.exists(dest) and os.path.getsize(dest) > 10_000:
            print(f"[skip] {dest} already present ({os.path.getsize(dest):,} bytes)")
            ok += 1
            continue
        got = False
        for url in urls:
            try:
                print(f"[get ] {url}")
                n = _download(url, dest)
                print(f"       -> {dest} ({n:,} bytes)")
                ok += 1
                got = True
                break
            except Exception as e:  # noqa: BLE001
                print(f"       FAILED: {e}")
        if not got:
            failed.append(fname)

    print(f"\n{ok}/{len(DOWNLOADS)} files ready in ./{DATA_DIR}/")
    if failed:
        print("Could not download:", ", ".join(failed))
        print(MANUAL_SOURCES)
        sys.exit(1)
    print("All status sheets present. Next:  python run_all.py")


if __name__ == "__main__":
    main()
