"""Figures for the REE leaching template.

Reads every `run_*/final_info.json` and produces two figures:

  recovery_vs_acid.png  the recovery / reagent-cost trade-off, which is the
                        actual decision the process engineer faces
  oracle_vs_truth.png   what the oracle claimed against what was really
                        measured, for the recipes that were tried

The second figure uses the `ground_truth` block, which the agent never sees
during the search. It exists so the write-up can be checked against reality.
"""

import json
import os
import os.path as osp

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Validated categorical palette (light surface), see the dataviz reference.
COLOR = {"HCl": "#2a78d6", "H2SO4": "#eb6834"}
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#dedcd6"

final_results = {}
for folder in sorted(os.listdir("./")):
    path = osp.join(folder, "final_info.json")
    if folder.startswith("run") and osp.isdir(folder) and osp.exists(path):
        with open(path) as f:
            final_results[folder] = json.load(f)


def _style(ax, xlabel, ylabel, title):
    ax.set_facecolor(SURFACE)
    ax.set_xlabel(xlabel, color=INK_MUTED, fontsize=10)
    ax.set_ylabel(ylabel, color=INK_MUTED, fontsize=10)
    ax.set_title(title, color=INK, fontsize=12, loc="left", pad=10)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_MUTED, labelsize=9)


def _rows(key):
    for run, payload in final_results.items():
        block = payload.get("leaching_search", {})
        for entry in block.get("evaluated", []):
            yield run, entry, block.get(key, {})


# --- Figure 1: the recovery / reagent-cost trade-off -----------------------
fig, ax = plt.subplots(figsize=(7.2, 5.2), facecolor=SURFACE)
seen = set()
for _run, entry, _gt in _rows("ground_truth"):
    acid = entry["recipe"]["acid"]
    label = acid if acid not in seen else None
    seen.add(acid)
    ax.scatter(entry["acid_consumption_mol_per_kg"], entry["rey_recovery_pct"],
               s=64, c=COLOR.get(acid, INK_MUTED), edgecolors=SURFACE,
               linewidths=2.0, alpha=0.9, label=label, zorder=3)
_style(ax, "Acid consumed [mol per kg mud]", "REY recovery (oracle) [%]",
       "Recovery against reagent cost")
if seen:
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_MUTED)
fig.tight_layout()
fig.savefig("recovery_vs_acid.png", dpi=200, facecolor=SURFACE)
plt.close(fig)

# --- Figure 2: oracle claim against measured truth ------------------------
pairs = []
for run, payload in final_results.items():
    block = payload.get("leaching_search", {})
    gt = block.get("ground_truth")
    means = block.get("means", {})
    if gt and "true_rey_recovery_pct_of_selected" in gt:
        pairs.append((run, means.get("best_rey_recovery_pct"),
                      gt["true_rey_recovery_pct_of_selected"]))

if pairs:
    fig, ax = plt.subplots(figsize=(6.4, 6.0), facecolor=SURFACE)
    lo, hi = 30, 105
    ax.plot([lo, hi], [lo, hi], color=INK_MUTED, lw=1.2, ls="--", zorder=1,
            label="perfect agreement")
    for run, claimed, actual in pairs:
        ax.scatter(actual, claimed, s=72, c="#2a78d6", edgecolors=SURFACE,
                   linewidths=2.0, zorder=3)
        ax.annotate(run, (actual, claimed), textcoords="offset points",
                    xytext=(6, 4), fontsize=8, color=INK_MUTED)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    _style(ax, "Measured recovery of the selected recipe [%]",
           "Recovery claimed by the oracle [%]",
           "What the oracle promised against what was measured")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_MUTED, loc="lower right")
    fig.tight_layout()
    fig.savefig("oracle_vs_truth.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)
