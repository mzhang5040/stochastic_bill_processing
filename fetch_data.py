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
        "https://content.leg.colorado.gov/sites/default/files/2022-house-final-status-sheet-accessible.pdf",
        "https://content.leg.colorado.gov/sites/default/files/2022_House_Status_Sheet.pdf",
    ],
    # 2023: the regular-session sheet (14 pp, HB 23-1001 onward). NOT the two-page
    # First Extraordinary Session sheet at .../2023_House_Status_Sheet.pdf.
    "2023-house-final-status-sheet-accessible.pdf": [
        "https://content.leg.colorado.gov/sites/default/files/2023-house-final-status-sheet-accessible.pdf",
    ],
    "2024-house-final-status-sheet-accessible.pdf": [
        "https://content.leg.colorado.gov/sites/default/files/2024-house-final-status-sheet-accessible.pdf",
        "https://leg.colorado.gov/sites/default/files/2024_house_final_status_sheet.pdf",
    ],
}

# Post-download sanity check: each sheet must identify its own session, which
# distinguishes the 2023 regular-session file from the extraordinary-session one.
EXPECTED_SESSION = {
    "2022-house-final-status-sheet-accessible.pdf": "SECOND REGULAR SESSION",
    "2023-house-final-status-sheet-accessible.pdf": "FIRST REGULAR SESSION",
    "2024-house-final-status-sheet-accessible.pdf": "SECOND REGULAR SESSION",
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
      https://content.leg.colorado.gov/sites/default/files/2023-house-final-status-sheet-accessible.pdf
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



def verify(fname):
    """Confirm the downloaded sheet identifies the expected session (guards
    against fetching the wrong 2023 file)."""
    import pdfplumber
    dest = os.path.join(DATA_DIR, fname)
    want = EXPECTED_SESSION[fname]
    with pdfplumber.open(dest) as pdf:
        head = (pdf.pages[0].extract_text() or "").upper()
    if want not in head:
        raise SystemExit(
            f"SANITY CHECK FAILED: {dest} does not identify '{want}'. "
            f"You likely fetched the wrong file. See MANUAL_SOURCES below.\n{MANUAL_SOURCES}")
    print(f"[ok  ] {fname}: '{want}' confirmed")


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
    for fname in DOWNLOADS:
        verify(fname)
    print("All status sheets present and session-verified. Next:  python run_all.py")


if __name__ == "__main__":
    main()
