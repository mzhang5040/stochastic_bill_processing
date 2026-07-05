"""
parse_status_sheets.py
======================
Parse Colorado House Daily Status Sheet PDFs into bill trajectory records.

Each record maps one bill to a sequence of Markov states:
    Introduced -> In_Committee -> Out_of_Committee -> On_Floor -> {Passed|Failed}

The six-state model
-------------------
Transient states (by index in all downstream matrices):
    0  Introduced          -- all bills upon filing
    1  In_Committee        -- upon committee assignment
    2  Out_of_Committee    -- upon the first House committee reporting
                             the bill out (report date recorded, not PI)
    3  On_Floor            -- upon second reading date recorded

Absorbing states:
    0  Passed              -- governor signature (SIG) or becomes law (BL)
    1  Failed              -- PI, Lost, DeemedPI, DeemedLost, Vetoed,
                             or no recorded disposition

Important note on OOC classification
------------------------------------
A bill is considered to have reached Out_of_Committee only if its first
House committee either (a) reported it out on a specific date, or
(b) referred it to a subsequent House committee via an R-referral.
A bill whose first committee action is ``PI<date>`` (Postponed Indefinitely)
is coded as In_Committee -> Failed, NOT Out_of_Committee -> Failed.

This distinction matters because the FI/NFI fiscal-impact notation is
recorded for essentially every bill that receives a committee hearing,
including bills that are killed in that same committee.  An earlier
version of this parser used a date-before-FI/NFI pattern as the OOC
signal, which incorrectly captured the PI date itself and misclassified
10.6-18.3% of bills per session (15.8%, 18.3%, 10.6% in 2022, 2023, 2024).  See `_classify_first_committee`
for the corrected rule.

Verification
------------
Running this module directly (python parse_status_sheets.py) prints
the passage rate per session.  After excluding supplemental
appropriations (which all passed in the observed sample; see parse_session below):
    2022: 76.5%    2023: 70.1%    2024: 73.3%

Input files
-----------
    Colorado House Daily Status Sheet PDFs, available at:
    https://leg.colorado.gov/bill-search

    Place in data/ subdirectory:
        data/2022-house-final-status-sheet-accessible.pdf
        data/2023-house-final-status-sheet-accessible.pdf
        data/2024-house-final-status-sheet-accessible.pdf

Usage
-----
    from parse_status_sheets import parse_session, SESSIONS

    bills_2024 = parse_session(*SESSIONS['2024'])
    # Returns list of dicts: {bill_num, year, markov, state_seq}

    from parse_status_sheets import parse_all_sessions
    all_bills = parse_all_sessions()
"""

import re
import pdfplumber


# ---------------------------------------------------------------------------
# Session configuration
# ---------------------------------------------------------------------------

# Maps year -> (pdf_path, bill_max).
# bill_max: highest bill number belonging to standard House bills (HB 1001..N).

SESSIONS = {
    '2022': ('data/2022-house-final-status-sheet-accessible.pdf', 1418),
    '2023': ('data/2023-house-final-status-sheet-accessible.pdf', 1311),
    '2024': ('data/2024-house-final-status-sheet-accessible.pdf', 1472),
}

# State labels used throughout the project
TRANSIENT_STATES = ['Introduced', 'In_Committee', 'Out_of_Committee', 'On_Floor']
ABSORBING_STATES = ['Passed', 'Failed']

# Committee abbreviations as they appear in the status sheets
_COMMITTEE_RE = (r'(?:BUS|HHS|JUD|THL|TLG|FIN|AWN|ALW|ED|SA|ENE|'
                 r'APP|AGR|BLT|LGH|LG|TRA|LC|LS|HI|PBH)')

# Lines containing these strings are page headers/footers, not bill data.
# These cause the current block to be flushed but parsing continues after.
_HEADER_KEYWORDS = [
    'PREPARED AS', 'DAILY STATUS', 'COLORADO GENERAL', 'Bill #', 'SEVENTY',
    'Status of all', 'ortnI', 'HOUSE BILLS', '___',
    'Intro Comm', 'ntro Comm',
]

# Lines containing these strings mark the end of the HOUSE BILLS section.
# Everything after these markers is HCR/HJR/Memorials/Resolutions, which reuse
# the 1001.. numbering and must be excluded from the Markov analysis.
_END_OF_HB_MARKERS = [
    'HOUSE CONCURRENT RESOLUTIONS',
    'HOUSE JOINT RESOLUTIONS',
    'HOUSE MEMORIALS',
    'HOUSE RESOLUTIONS',
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_text(pdf_path):
    """Extract and concatenate text from all pages of a PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        return ''.join(page.extract_text() or '' for page in pdf.pages)


def _strip_page_header(line):
    """
    Strip page-header text that is sometimes concatenated to the end
    of a bill's data line.

    Example: "SIG5/15Status of all House Bills as of 8:00 A.M. ..." --
    the PDF extractor occasionally joins the SIG notation with the
    next page's header without a separator. We want to preserve the
    "SIG5/15" portion and drop the header.

    Returns (cleaned_line, was_trimmed).
    """
    for kw in _HEADER_KEYWORDS:
        idx = line.find(kw)
        if idx > 0:
            # Keep only the part before the header keyword.
            return line[:idx].rstrip(), True
        if idx == 0:
            # Header keyword is at start of line: this is a pure header line.
            return '', True
    return line, False


def _split_into_bill_blocks(raw_text):
    """
    Split raw PDF text into one block of lines per bill.

    Bills start with a 4-digit number (e.g. '1042' or '1042*').
    Header and footer lines are discarded.  Parsing STOPS entirely
    when we cross into the HCR/HJR/Memorials/Resolutions sections,
    since those reuse the 1001+ numbering space.

    Lines that contain bill data concatenated with a page header
    (e.g. "SIG5/15Status of all House Bills...") are trimmed so the
    bill data is retained.
    """
    bills_raw = []
    current = []

    for line in raw_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # End of House Bills section: stop parsing entirely.
        if any(marker in line for marker in _END_OF_HB_MARKERS):
            if current:
                bills_raw.append(current)
                current = []
            break

        # If the line has a header keyword, strip the header part but
        # KEEP any bill data that precedes it on the same line.
        cleaned, was_trimmed = _strip_page_header(line)
        if was_trimmed:
            if cleaned:
                # Bill data preceded the header - keep it as part of current
                if current:
                    current.append(cleaned)
                # (If current is empty, this line was pure header or stray data.)
            else:
                # Pure header line - flush current block
                if current:
                    bills_raw.append(current)
                current = []
            continue

        if re.match(r'^\d{4}[\*\s]', line):
            if current:
                bills_raw.append(current)
            current = [line]
        else:
            if current:
                current.append(line)

    if current:
        bills_raw.append(current)
    return bills_raw


def _classify_first_committee(text):
    """
    Classify what happened to a bill in its first House committee.

    Returns
    -------
    'PI_in_committee'     : first committee action was PI<date> --
                            the bill was killed In_Committee.
    'reported_or_referred': first committee reported the bill out
                            (report date) or referred it to another
                            House committee (R<date>) -- the bill
                            reached Out_of_Committee.
    'no_committee'        : no committee code found (very rare).

    Logic
    -----
    On the status sheets, each bill's row begins with the introduction
    date, then the first committee assignment:

        <intro> <COMM1> <action1> ... [<COMM2> <action2> ...]

    The first committee action immediately follows COMM1.  The action
    is one of:
        PI<date>         -- Postponed Indefinitely (dead)
        R<date>          -- Referred to another committee (advances)
        <date>[*]        -- Reported out on this date (advances)
        <date>[*] R...   -- Reported then re-referred (advances)

    The earlier version of this parser looked for any date preceding
    FI/NFI and treated that as evidence the committee reported the
    bill.  That rule misfires because "PI<date>" followed by "FI"
    matches the same pattern -- the PI date was being read as a
    report date.
    """
    first_comm = re.search(rf'\b({_COMMITTEE_RE})\b', text)
    if first_comm is None:
        return 'no_committee'

    # Examine what comes right after the first committee code.
    after = text[first_comm.end():first_comm.end() + 80].lstrip()

    # PI<date> : bill was killed in committee
    if re.match(r'PI\d{1,2}/\d{1,2}', after):
        return 'PI_in_committee'

    # R<date> : referred to another committee (advances)
    if re.match(r'R\d{1,2}/\d{1,2}', after):
        return 'reported_or_referred'

    # Bare <date> : committee reported the bill
    if re.match(r'\d{1,2}/\d{1,2}\*?', after):
        return 'reported_or_referred'

    # Another committee code follows directly (rare layout quirk)
    if re.match(rf'\b{_COMMITTEE_RE}\b', after):
        return 'reported_or_referred'

    # If we can't tell, assume PI in committee -- this is the
    # conservative choice for a bill that shows no report activity.
    return 'PI_in_committee'


def _detect_second_reading(text):
    """
    Detect whether the bill received a second reading on the House floor.

    A bill reaches On_Floor when a second-reading date is recorded.
    On the status sheets, the 2nd and 3rd reading dates appear as two
    consecutive dates with no intervening committee code.

    Strong positive signals (used directly, no further check needed):
      SIG, BL : governor action (implies floor passage)
      V, PV, PVO, VO, VS : veto-related (implies floor passage)
      CC, CRAS, CRAH, HAD, SRE, SRL, SRC : conference/concurrence action
      L<date>  : lost on a floor vote

    Structural rule (used when no strong signal is present):
      After the first FI/NFI anchor, find all dates and all committee
      codes. If there exist two dates in a row (with no committee code
      between them), those are the 2nd and 3rd readings and the bill
      reached the floor.

    This rule correctly handles:
      - Simple bills: "BUS R2/2* APP 4/25* FI-$ 4/26* 4/29 SIG" — two
        dates (4/26, 4/29) in a row after FI, so On_Floor=True.
      - Bills killed in Appropriations: "FIN R3/8 FI-$ DeemedPI APP 5/14"
        — only one date after FI (5/14), preceded by APP, so On_Floor=False.
      - Bills with multi-committee path: "FIN R4/4* FI-$ DeemedLost APP
        5/2* 5/2* 5/3" — two consecutive dates (5/2, 5/3) after APP, so
        On_Floor=True.

    An earlier version of this function accepted any single date after
    FI as evidence of a 2nd reading, which misclassified bills whose
    only post-FI date was a committee-assignment date (e.g. "APP 5/14").
    """
    # Strong positive signals
    if re.search(r'\b(?:SIG\d|BL\d|V\d|PV\d|PVO\d|VO\d|VS\d)', text):
        return True
    if re.search(r'\b(?:CC\d|CRAS\d|CRAH\d|SRC\d|HAD\d|SRE\d|SRL\d)', text):
        return True
    if re.search(r'\bL\d{1,2}/\d{1,2}\*?', text):
        return True

    fi_pos = re.search(r'(?:NFI|FI-\$|FI)\b', text)
    if not fi_pos:
        return False
    tail = text[fi_pos.end():]

    # Collect tokens of type 'date', 'comm', or 'ref' in the tail.
    tokens = []
    for m in re.finditer(r'\b\d{1,2}/\d{1,2}\*?', tail):
        ctx = tail[max(0, m.start() - 3):m.start()]
        if 'PI' in ctx or 'LO' in ctx:
            continue
        tokens.append((m.start(), 'date'))
    for m in re.finditer(rf'\b{_COMMITTEE_RE}\b', tail):
        tokens.append((m.start(), 'comm'))
    for m in re.finditer(r'\bR\d{1,2}/\d{1,2}\*?', tail):
        tokens.append((m.start(), 'ref'))
    tokens.sort()

    # Look for two consecutive 'date' tokens (no comm/ref between).
    prev = None
    for _, typ in tokens:
        if typ == 'date' and prev == 'date':
            return True
        prev = typ

    return False


def _parse_bill_block(lines, year):
    """
    Parse a single bill block into a trajectory record.

    State detection (corrected)
    ---------------------------
    Introduced      : always (every bill starts here)

    In_Committee    : a committee code appears in the block
                      (a bill is In_Committee once it receives an
                      assignment, whether or not it advances).

    Out_of_Committee: the first House committee either reported the
                      bill out on a specific date OR referred it to a
                      subsequent House committee. A bill with first
                      action ``PI<date>`` did NOT reach Out_of_Committee.

    On_Floor        : a second-reading date was recorded, OR a strong
                      downstream-of-floor signal is present (SIG, BL,
                      veto, conference committee, Senate concurrence).

    Passed          : SIG[digit] or BL[digit] present
    Failed          : all other outcomes

    A bill's state sequence is monotone: once it reaches state k, it
    passes through all states 0..k-1.

    Returns None if bill number cannot be parsed.
    """
    text = re.sub(r'\s+', ' ', ' '.join(lines)).strip()

    num_m = re.match(r'^(\d{4})\*?', text)
    if not num_m:
        return None
    bill_num = int(num_m.group(1))

    # Outcome
    if re.search(r'SIG\d', text) or re.search(r'BL\d', text):
        markov = 'Passed'
    else:
        markov = 'Failed'

    # In_Committee
    in_committee = bool(re.search(rf'\b({_COMMITTEE_RE})\b', text))

    # Out_of_Committee (corrected rule)
    first_committee_fate = _classify_first_committee(text)
    out_of_committee = (first_committee_fate == 'reported_or_referred')

    # On_Floor (requires OOC)
    on_floor = out_of_committee and _detect_second_reading(text)

    # Consistency: a Passed bill must have reached every earlier stage.
    if markov == 'Passed':
        out_of_committee = True
        on_floor = True

    # Build sequence
    seq = ['Introduced']
    if in_committee:
        seq.append('In_Committee')
    if out_of_committee:
        seq.append('Out_of_Committee')
    if on_floor:
        seq.append('On_Floor')
    seq.append(markov)

    return {
        'bill_num': bill_num,
        'year': year,
        'markov': markov,
        'state_seq': ' -> '.join(seq),
    }


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def parse_session(pdf_path, year, bill_max):
    """
    Parse one Colorado House session status sheet PDF.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.
    year : str
        Session label, e.g. '2022'.  Stored in each returned record.
    bill_max : int
        Highest bill number to include.

    Returns
    -------
    list of dict, one per bill, with keys:
        bill_num  : int
        year      : str
        markov    : str  ('Passed' or 'Failed')
        state_seq : str  (e.g. 'Introduced -> In_Committee -> Out_of_Committee -> Passed')

    Deduplication
    -------------
    If the same bill number appears multiple times in the PDF (an
    occasional artifact of the source document - e.g. HB23-1233 is
    printed twice in the 2023 sheet), only the first complete record
    is retained.  When duplicates disagree on outcome, the record
    with a more complete trajectory is preferred.
    """
    raw_text = _extract_text(pdf_path)
    blocks = _split_into_bill_blocks(raw_text)

    parsed = {}  # bill_num -> record, keeps first/more-complete record
    for block in blocks:
        nm = re.match(r'^(\d{4})', block[0].strip())
        if not nm:
            continue
        num = int(nm.group(1))
        if num < 1001 or num > bill_max:
            continue

        text = ' '.join(block)

        # Exclude supplemental appropriations bills. These follow a JBC
        # fast-track with "N/A" in the fiscal impact column (the bill IS
        # the appropriation, so fiscal impact is inapplicable):
        #
        #   introduced -> APP reports same day -> 2nd/3rd readings
        #   next day -> SIG within weeks
        #
        # Including them would inflate the passage rate and distort the
        # Markov chain because they all passed in the observed sample. Pattern:
        # N/A present, APP committee activity, SIG present, no PI marker.
        #
        # An earlier version of this filter was broader and also dropped a
        # small number of PI-in-committee bills that happened to have "N/A"
        # in place of FI notation (e.g. HB22-1116, HB23-1092, HB24-1070).
        # Those bills legitimately belong in the In_Committee -> Failed
        # category and are now retained.
        if ('N/A' in text
                and 'APP' in text
                and re.search(r'SIG\d', text)
                and not re.search(r'PI\d', text)):
            continue

        record = _parse_bill_block(block, year)
        if record is None or record['bill_num'] <= 0:
            continue

        bn = record['bill_num']
        if bn not in parsed:
            parsed[bn] = record
        else:
            # Prefer record with a longer (more complete) trajectory.
            existing_len = len(parsed[bn]['state_seq'].split(' -> '))
            new_len = len(record['state_seq'].split(' -> '))
            if new_len > existing_len:
                parsed[bn] = record
            elif new_len == existing_len and record['markov'] == 'Passed':
                # Prefer Passed over Failed when trajectories tie.
                parsed[bn] = record

    return sorted(parsed.values(), key=lambda r: r['bill_num'])


def parse_all_sessions(session_config=None):
    """
    Parse all configured sessions and return a combined bill list.

    Parameters
    ----------
    session_config : dict, optional
        Defaults to module-level SESSIONS.

    Returns
    -------
    list of dict
    """
    if session_config is None:
        session_config = SESSIONS

    all_bills = []
    for year, (path, bill_max) in sorted(session_config.items()):
        bills = parse_session(path, year, bill_max)
        all_bills.extend(bills)
        n_pass = sum(1 for b in bills if b['markov'] == 'Passed')
        print(f"  {year}: {len(bills)} bills  "
              f"({n_pass} passed, {n_pass/len(bills):.1%} passage rate)")
    return all_bills


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import json, sys

    print("Parsing all sessions...\n")
    bills = parse_all_sessions()
    print(f"\nTotal: {len(bills)} bills\n")

    from collections import Counter
    print("Most common trajectories:")
    for seq, n in Counter(b['state_seq'] for b in bills).most_common(8):
        print(f"  {n:4d}  {seq}")

    if '--json' in sys.argv:
        with open('bills.json', 'w') as f:
            json.dump(bills, f, indent=2)
        print("\nWrote bills.json")
