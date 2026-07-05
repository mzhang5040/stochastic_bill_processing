"""
build_all_figures.py
Generate all six manuscript figures with ONE consistent typeface
(Liberation Serif, metric-compatible with Times New Roman) so every figure
matches the manuscript font, per the JHSS figure-format instruction.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 11,
    "axes.titlesize": 12,
})

sessions = ["2022", "2023", "2024"]
col = ["#2b6cb0", "#dd6b20", "#38a169"]


# ---------------------------------------------------------------------------
# Figure 1: the four-state absorbing Markov chain (matplotlib redraw)
# ---------------------------------------------------------------------------
def figure1():
    fig, ax = plt.subplots(figsize=(9.2, 3.7))
    ax.set_xlim(0, 13.2); ax.set_ylim(-3.4, 2.2); ax.axis("off")

    def rbox(cx, cy, text, w=2.5, h=1.0, double=False):
        style = "round,pad=0.02,rounding_size=0.18"
        ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h, boxstyle=style,
                                    fc="white", ec="black", lw=1.3))
        if double:  # absorbing: second inner outline
            m = 0.10
            ax.add_patch(FancyBboxPatch((cx-w/2+m, cy-h/2+m), w-2*m, h-2*m,
                                        boxstyle="round,pad=0.02,rounding_size=0.14",
                                        fc="none", ec="black", lw=1.1))
        ax.text(cx, cy, text, ha="center", va="center", fontsize=11)

    # transient row
    T = {"s0": (1.5, 0), "s1": (4.6, 0), "s2": (7.9, 0), "s3": (11.0, 0)}
    rbox(*T["s0"], "Introduced")
    rbox(*T["s1"], "In Committee")
    rbox(*T["s2"], "Out of Committee", w=2.9)
    rbox(*T["s3"], "On Floor", w=2.2)
    # absorbing
    P = (11.0, 1.6); Fl = (7.9, -2.7)
    rbox(*P, "Passed", w=2.0, h=0.9, double=True)
    rbox(*Fl, "Failed", w=2.0, h=0.9, double=True)

    def arrow(a, b, rad=0.0):
        ax.add_patch(FancyArrowPatch(a, b, connectionstyle=f"arc3,rad={rad}",
                                     arrowstyle="-|>", mutation_scale=14,
                                     lw=1.2, color="black",
                                     shrinkA=2, shrinkB=2))

    def lab(x, y, t, dx=0, dy=0.22):
        ax.text(x+dx, y+dy, t, ha="center", va="center", fontsize=10)

    # advancing edges
    arrow((T["s0"][0]+1.25, 0), (T["s1"][0]-1.25, 0)); lab(3.05, 0, r"$1$")
    arrow((T["s1"][0]+1.25, 0), (T["s2"][0]-1.45, 0)); lab(6.25, 0, r"$Q_{1,2}$")
    arrow((T["s2"][0]+1.45, 0), (T["s3"][0]-1.10, 0)); lab(9.55, 0, r"$Q_{2,3}$")
    arrow((T["s3"][0], 0.5), (P[0], P[1]-0.5)); lab(11.0, 0.95, r"$R_{3,0}$", dx=0.55, dy=0)
    # failing edges (curved to Failed)
    arrow((T["s1"][0], -0.5), (Fl[0]-0.9, Fl[1]+0.4), rad=-0.28); lab(5.4, -1.7, r"$R_{1,1}$")
    arrow((T["s2"][0], -0.5), (Fl[0], Fl[1]+0.5)); lab(8.2, -1.4, r"$R_{2,1}$")
    arrow((T["s3"][0], -0.5), (Fl[0]+0.9, Fl[1]+0.4), rad=0.28); lab(10.4, -1.7, r"$R_{3,1}$")

    fig.tight_layout(); fig.savefig("Figure1_chain.png", dpi=300,
                                    bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2: transition probabilities
# ---------------------------------------------------------------------------
def figure2():
    labels = ["Introduced \u2192\nIn Committee", "In Committee \u2192\nOut of Committee",
              "In Committee \u2192\nFailed", "Out of Committee \u2192\nOn Floor",
              "Out of Committee \u2192\nFailed", "On Floor \u2192\nPassed",
              "On Floor \u2192\nFailed"]
    P = {"2022": [1.0000, 0.8425, 0.1575, 0.9496, 0.0504, 0.9563, 0.0437],
         "2023": [1.0000, 0.8167, 0.1833, 0.9331, 0.0669, 0.9198, 0.0802],
         "2024": [1.0000, 0.8944, 0.1056, 0.8920, 0.1080, 0.9183, 0.0817]}
    x = np.arange(len(labels)); w = 0.26
    fig, ax = plt.subplots(figsize=(10.0, 4.9))
    for i, s in enumerate(sessions):
        ax.bar(x + (i-1)*w, P[s], w, label=s, color=col[i])
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=0, ha="center", fontsize=8.5)
    ax.set_ylabel("Estimated Transition Probability")
    ax.set_ylim(0, 1.05); ax.legend(title="Session", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig("Figure2_transition_probabilities.png", dpi=300); plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3: sensitivity magnitudes with bootstrap 95% CIs
# ---------------------------------------------------------------------------
def figure3():
    stages = ["First Committee", "Floor", "Out of Committee"]
    pt = {"First Committee": [0.908, 0.858, 0.819],
          "Floor": [0.800, 0.762, 0.798],
          "Out of Committee": [0.806, 0.751, 0.821]}
    lo = {"First Committee": [0.878, 0.813, 0.780],
          "Floor": [0.760, 0.711, 0.757],
          "Out of Committee": [0.768, 0.700, 0.783]}
    hi = {"First Committee": [0.938, 0.900, 0.857],
          "Floor": [0.838, 0.807, 0.836],
          "Out of Committee": [0.842, 0.797, 0.858]}
    scol = ["#2b6cb0", "#dd6b20", "#38a169"]
    mark = ["o", "s", "^"]
    x = np.arange(len(sessions))
    fig, ax = plt.subplots(figsize=(6.8, 4.4), constrained_layout=True)
    for i, st in enumerate(stages):
        p = np.array(pt[st]); l = p - np.array(lo[st]); u = np.array(hi[st]) - p
        ax.errorbar(x + (i-1)*0.11, p, yerr=[l, u], fmt=mark[i], color=scol[i],
                    label=st, capsize=3, ms=6, lw=1.3, elinewidth=1.2)
    ax.set_xticks(x); ax.set_xticklabels(sessions)
    ax.set_ylabel("Sensitivity Magnitude")
    ax.set_ylim(0.65, 0.95)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3,
              frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig("Figure3_sensitivities.png", dpi=300); plt.close(fig)


def figure4():
    maj = [4.3, 9.2, 4.8]; mn = [51.0, 48.6, 34.1]
    x = np.arange(len(sessions)); w = 0.36
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    b1 = ax.bar(x - w/2, maj, w, label="Majority (D) Sponsor", color="#2b6cb0")
    b2 = ax.bar(x + w/2, mn, w, label="Minority (R) Sponsor", color="#c53030")
    for b in list(b1) + list(b2):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.8,
                f"{b.get_height():.0f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(sessions)
    ax.set_ylabel("First-Committee Death Rate (% of Introduced Bills)")
    ax.set_ylim(0, 60); ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig("Figure4_party_gap.png", dpi=300); plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5: floor-failure decomposition (title-case labels)
# ---------------------------------------------------------------------------
def figure5():
    comp = ["Senate-Side", "House-Side", "Gubernatorial Veto", "Session-End"]
    vals = {"Senate-Side": [1.5, 3.2, 2.7], "House-Side": [0.5, 0.3, 0.7],
            "Gubernatorial Veto": [1.0, 1.9, 1.1], "Session-End": [0.5, 0.6, 2.0]}
    ccol = ["#2c5282", "#63b3ed", "#dd6b20", "#a0aec0"]
    x = np.arange(len(sessions)); bottom = np.zeros(len(sessions))
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for k, c in zip(comp, ccol):
        ax.bar(x, vals[k], 0.55, bottom=bottom, label=k, color=c)
        bottom += np.array(vals[k])
    ax.set_xticks(x); ax.set_xticklabels(sessions)
    ax.set_ylabel("On-Floor Failures (% of Introduced Bills)")
    ax.set_ylim(0, 7.5); ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig("Figure5_bicameral.png", dpi=300); plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 6: conditional OOC failure rate by introduction cohort (binomial CIs)
# ---------------------------------------------------------------------------
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d
    hw = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return (max(0, c-hw)*100, (c+hw)*100)

def figure6():
    counts = {"2022": [(8,101),(6,105),(3,131)],
              "2023": [(4,81),(9,78),(4,95)],
              "2024": [(17,124),(17,127),(9,147)]}
    tert = ["Early", "Middle", "Late"]
    mark = ["o", "s", "^"]
    x = np.arange(len(tert))
    fig, ax = plt.subplots(figsize=(6.8, 4.4), constrained_layout=True)
    for i, sn in enumerate(sessions):
        pts = [k/n*100 for k, n in counts[sn]]
        cis = [wilson(k, n) for k, n in counts[sn]]
        lo = [p-l for p, (l, u) in zip(pts, cis)]
        hi = [u-p for p, (l, u) in zip(pts, cis)]
        ax.errorbar(x, pts, yerr=[lo, hi], fmt=mark[i]+"-", color=col[i],
                    label=sn, capsize=3, ms=6, lw=1.4, elinewidth=1.1)
    ax.set_xticks(x); ax.set_xticklabels(tert)
    ax.set_ylabel("Conditional OOC Failure Rate (%)")
    ax.set_xlabel("Introduction-Date Tertile")
    ax.set_ylim(0, 22.5)
    ax.legend(title="Session", frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig("Figure6_cohorts.png", dpi=300); plt.close(fig)

for f in (figure1, figure2, figure3, figure4, figure5, figure6):
    f()
print("wrote Figure1_chain.png .. Figure6_cohorts.png (Liberation Serif, Times-compatible)")
