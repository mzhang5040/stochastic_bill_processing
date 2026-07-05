"""
generate_figures.py
Regenerates the six submitted manuscript figures FROM DATA, with relative
paths, one consistent Times-compatible serif typeface, and the exact submission
filenames. Figures 2-6 are computed from the parsed status sheets and the two
derived-data CSVs; Figure 1 is a separately maintained schematic of the chain.

Run standalone (`python generate_figures.py`) or via `python run_all.py`.
"""
import os
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

from parse_status_sheets import SESSIONS, parse_session
from markov_chain import compute_chain
import chamber_coding

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 11,
})

FIGDIR = "."
YEARS = ["2022", "2023", "2024"]
COL = ["#2b6cb0", "#dd6b20", "#38a169"]
PARTY_CSV = os.path.join("data", "sponsor_parties.csv")


def _out(name):
    return os.path.join(FIGDIR, name)


def _load_sessions():
    out = {}
    for yr in YEARS:
        path, bmax = SESSIONS[yr]
        out[yr] = parse_session(path, yr, bmax)
    return out


def _party_map():
    pm = {}
    with open(PARTY_CSV) as f:
        for r in csv.DictReader(f):
            pm[(int(r["bill_num"]), r["year"])] = r["party"]
    return pm


def _wald(k, n, z=1.96):
    """Normal-approximation (Wald) 95% CI for a binomial proportion, in percent."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    hw = z * np.sqrt(p * (1 - p) / n)
    return (max(0.0, p - hw) * 100, min(1.0, p + hw) * 100)


# --------------------------------------------------------------------------
# Figure 1: chain schematic (separately maintained; not derived from data)
# --------------------------------------------------------------------------
def fig_chain():
    fig, ax = plt.subplots(figsize=(9.2, 3.7))
    ax.set_xlim(0, 13.2); ax.set_ylim(-3.4, 2.2); ax.axis("off")

    def rbox(cx, cy, text, w=2.5, h=1.0, double=False):
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                    boxstyle="round,pad=0.02,rounding_size=0.18",
                    fc="white", ec="black", lw=1.3))
        if double:
            m = 0.10
            ax.add_patch(FancyBboxPatch((cx - w / 2 + m, cy - h / 2 + m), w - 2 * m, h - 2 * m,
                        boxstyle="round,pad=0.02,rounding_size=0.14", fc="none", ec="black", lw=1.1))
        ax.text(cx, cy, text, ha="center", va="center", fontsize=11)

    T = {"s0": (1.5, 0), "s1": (4.6, 0), "s2": (7.9, 0), "s3": (11.0, 0)}
    rbox(*T["s0"], "Introduced"); rbox(*T["s1"], "In Committee")
    rbox(*T["s2"], "Out of Committee", w=2.9); rbox(*T["s3"], "On Floor", w=2.2)
    P = (11.0, 1.6); Fl = (7.9, -2.7)
    rbox(*P, "Passed", w=2.0, h=0.9, double=True)
    rbox(*Fl, "Failed", w=2.0, h=0.9, double=True)

    def arrow(a, b, rad=0.0):
        ax.add_patch(FancyArrowPatch(a, b, connectionstyle=f"arc3,rad={rad}",
                    arrowstyle="-|>", mutation_scale=14, lw=1.2, color="black", shrinkA=2, shrinkB=2))

    def lab(x, y, t, dx=0, dy=0.22):
        ax.text(x + dx, y + dy, t, ha="center", va="center", fontsize=10)

    arrow((T["s0"][0] + 1.25, 0), (T["s1"][0] - 1.25, 0)); lab(3.05, 0, r"$1$")
    arrow((T["s1"][0] + 1.25, 0), (T["s2"][0] - 1.45, 0)); lab(6.25, 0, r"$Q_{1,2}$")
    arrow((T["s2"][0] + 1.45, 0), (T["s3"][0] - 1.10, 0)); lab(9.55, 0, r"$Q_{2,3}$")
    arrow((T["s3"][0], 0.5), (P[0], P[1] - 0.5)); lab(11.0, 0.95, r"$R_{3,0}$", dx=0.55, dy=0)
    arrow((T["s1"][0], -0.5), (Fl[0] - 0.9, Fl[1] + 0.4), rad=-0.28); lab(5.4, -1.7, r"$R_{1,1}$")
    arrow((T["s2"][0], -0.5), (Fl[0], Fl[1] + 0.5)); lab(8.2, -1.4, r"$R_{2,1}$")
    arrow((T["s3"][0], -0.5), (Fl[0] + 0.9, Fl[1] + 0.4), rad=0.28); lab(10.4, -1.7, r"$R_{3,1}$")
    fig.tight_layout(); fig.savefig(_out("Figure1_chain.png"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------------------
# Figure 2: transition probabilities (from data)
# --------------------------------------------------------------------------
def fig_transition_probabilities(sessions=None):
    sessions = sessions or _load_sessions()
    labels = ["Introduced \u2192\nIn Committee", "In Committee \u2192\nOut of Committee",
              "In Committee \u2192\nFailed", "Out of Committee \u2192\nOn Floor",
              "Out of Committee \u2192\nFailed", "On Floor \u2192\nPassed", "On Floor \u2192\nFailed"]
    P = {}
    for yr in YEARS:
        r = compute_chain(sessions[yr], yr)
        P[yr] = [1.0, r.Q[1, 2], r.R[1, 1], r.Q[2, 3], r.R[2, 1], r.R[3, 0], r.R[3, 1]]
    x = np.arange(len(labels)); w = 0.26
    fig, ax = plt.subplots(figsize=(10.0, 4.9))
    for i, yr in enumerate(YEARS):
        ax.bar(x + (i - 1) * w, P[yr], w, label=yr, color=COL[i])
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=0, ha="center", fontsize=8.5)
    ax.set_ylabel("Estimated Transition Probability"); ax.set_ylim(0, 1.05)
    ax.legend(title="Session", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(_out("Figure2_transition_probabilities.png"), dpi=300); plt.close(fig)


# --------------------------------------------------------------------------
# Figure 3: sensitivity magnitudes + bootstrap 95% intervals (from data)
# --------------------------------------------------------------------------
def fig_sensitivities(sessions=None):
    sessions = sessions or _load_sessions()
    stages = ["First Committee", "Floor", "Out of Committee"]
    scol = ["#2b6cb0", "#dd6b20", "#38a169"]; mark = ["o", "s", "^"]
    pt = {s: [] for s in stages}; lo = {s: [] for s in stages}; hi = {s: [] for s in stages}
    for yr in YEARS:
        bills = sessions[yr]
        base = compute_chain(bills, yr)
        pts = {"First Committee": -base.B[2, 0], "Floor": base.floor_sensitivity,
               "Out of Committee": base.ooc_sensitivity}
        rng = np.random.default_rng(42)
        boot = {s: [] for s in stages}
        n = len(bills)
        for _ in range(2000):
            samp = [bills[i] for i in rng.integers(0, n, n)]
            try:
                r = compute_chain(samp, yr)
                boot["First Committee"].append(-r.B[2, 0])
                boot["Floor"].append(r.floor_sensitivity)
                boot["Out of Committee"].append(r.ooc_sensitivity)
            except Exception:
                continue
        for s in stages:
            pt[s].append(abs(pts[s]))
            arr = np.abs(np.array(boot[s]))
            lo[s].append(np.percentile(arr, 2.5)); hi[s].append(np.percentile(arr, 97.5))
    x = np.arange(len(YEARS))
    fig, ax = plt.subplots(figsize=(6.8, 4.4), constrained_layout=True)
    for i, s in enumerate(stages):
        p = np.array(pt[s]); l = p - np.array(lo[s]); u = np.array(hi[s]) - p
        ax.errorbar(x + (i - 1) * 0.11, p, yerr=[l, u], fmt=mark[i], color=scol[i],
                    label=s, capsize=3, ms=6, lw=1.3, elinewidth=1.2)
    ax.set_xticks(x); ax.set_xticklabels(YEARS); ax.set_ylabel("Sensitivity Magnitude")
    ax.set_ylim(0.65, 0.95)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(_out("Figure3_sensitivities.png"), dpi=300); plt.close(fig)


# --------------------------------------------------------------------------
# Figure 4: first-committee death rate by sponsoring party (from data)
# --------------------------------------------------------------------------
def fig_party_gap(sessions=None):
    sessions = sessions or _load_sessions()
    pm = _party_map()
    maj, mn = [], []
    for yr in YEARS:
        bills = sessions[yr]
        D = [b for b in bills if pm.get((b["bill_num"], yr)) == "D"]
        R = [b for b in bills if pm.get((b["bill_num"], yr)) == "R"]
        def died(bs):
            k = sum(1 for b in bs if b["state_seq"] == "Introduced -> In_Committee -> Failed")
            return 100 * k / len(bs) if bs else 0
        maj.append(died(D)); mn.append(died(R))
    x = np.arange(len(YEARS)); w = 0.36
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    b1 = ax.bar(x - w / 2, maj, w, label="Majority (D) Sponsor", color="#2b6cb0")
    b2 = ax.bar(x + w / 2, mn, w, label="Minority (R) Sponsor", color="#c53030")
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.8, f"{b.get_height():.0f}%",
                ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(YEARS)
    ax.set_ylabel("First-Committee Death Rate (% of Introduced Bills)"); ax.set_ylim(0, 60)
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(_out("Figure4_party_gap.png"), dpi=300); plt.close(fig)


# --------------------------------------------------------------------------
# Figure 5: on-floor failure decomposition, % of introduced (from CSV)
# --------------------------------------------------------------------------
def fig_bicameral(sessions=None):
    sessions = sessions or _load_sessions()
    counts = chamber_coding.component_counts()
    comp = ["Senate-Side", "House-Side", "Gubernatorial Veto", "Session-End"]
    key = {"Senate-Side": "Senate-side", "House-Side": "House-side",
           "Gubernatorial Veto": "Veto", "Session-End": "Session-end"}
    ccol = ["#2c5282", "#63b3ed", "#dd6b20", "#a0aec0"]
    intro = {yr: len(sessions[yr]) for yr in YEARS}
    vals = {c: [100 * counts[yr][key[c]] / intro[yr] for yr in YEARS] for c in comp}
    x = np.arange(len(YEARS)); bottom = np.zeros(len(YEARS))
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for c, cc in zip(comp, ccol):
        ax.bar(x, vals[c], 0.55, bottom=bottom, label=c, color=cc); bottom += np.array(vals[c])
    ax.set_xticks(x); ax.set_xticklabels(YEARS)
    ax.set_ylabel("On-Floor Failures (% of Introduced Bills)"); ax.set_ylim(0, 7.5)
    ax.legend(frameon=False, fontsize=9); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(_out("Figure5_bicameral.png"), dpi=300); plt.close(fig)


# --------------------------------------------------------------------------
# Figure 6: conditional OOC failure rate by introduction cohort (from data)
# --------------------------------------------------------------------------
def fig_cohorts(sessions=None):
    sessions = sessions or _load_sessions()
    tert = ["Early", "Middle", "Late"]; mark = ["o", "s", "^"]
    x = np.arange(len(tert))
    fig, ax = plt.subplots(figsize=(6.8, 4.4), constrained_layout=True)
    for i, yr in enumerate(YEARS):
        bills = sessions[yr]; n = len(bills); t1, t2 = n // 3, 2 * n // 3
        cohorts = [bills[:t1], bills[t1:t2], bills[t2:]]
        pts, lo, hi = [], [], []
        for c in cohorts:
            reached = sum(1 for b in c if "-> Out_of_Committee" in b["state_seq"])
            failed = sum(1 for b in c if b["state_seq"] == "Introduced -> In_Committee -> Out_of_Committee -> Failed")
            p = 100 * failed / reached if reached else 0
            l, u = _wald(failed, reached); pts.append(p); lo.append(p - l); hi.append(u - p)
        ax.errorbar(x, pts, yerr=[lo, hi], fmt=mark[i] + "-", color=COL[i], label=yr,
                    capsize=3, ms=6, lw=1.4, elinewidth=1.1)
    ax.set_xticks(x); ax.set_xticklabels(tert)
    ax.set_ylabel("Conditional OOC Failure Rate (%)"); ax.set_xlabel("Introduction-Date Tertile")
    ax.set_ylim(0, 22.5); ax.legend(title="Session", frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(_out("Figure6_cohorts.png"), dpi=300); plt.close(fig)


def main():
    s = _load_sessions()
    fig_chain()
    fig_transition_probabilities(s)
    fig_sensitivities(s)
    fig_party_gap(s)
    fig_bicameral(s)
    fig_cohorts(s)
    print("Wrote Figure1_chain.png .. Figure6_cohorts.png to", FIGDIR)
    print("(Figure 1 is a separately maintained schematic; Figures 2-6 are computed from data.)")


if __name__ == "__main__":
    main()
