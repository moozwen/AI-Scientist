"""REE leaching recipe search -- AI Scientist v1 template.

Domain: hydrometallurgical leaching of rare-earth-rich mud from the Minamitorishima
EEZ (Japan). You propose leaching recipes; a geochemical oracle scores them in
seconds instead of running a wet experiment.

HOW TO USE THIS FILE
--------------------
Edit `RECIPES` below -- that is the experiment. Everything else is fixed harness
code; do not change it. Run with:

    python experiment.py --out_dir=run_i

WHAT THE ORACLE IS
------------------
A PHREEQC equilibrium model of apatite dissolution + gypsum coprecipitation,
calibrated against the 120 published measurements of Takaya et al. (2015).

**The oracle is NOT an accurate predictor.** Its rank correlation with the
measurements is only rho ~ 0.72-0.77 across all conditions -- lower than a
trivial predictor that looks at nothing but the acid type (rho = 0.818). Treat
it as a screening device, not as truth. Depending on the experimental arm it
may or may not tell you where it is trustworthy.

SEARCH SPACE (fixed -- recipes outside it are rejected)
------------------------------------------------------
    acid        HCl | H2SO4
    conc_mol_L  HCl: 0.5, 1.0, 2.0, 3.0    H2SO4: 0.25, 0.5, 1.0, 1.5
    time_min    2, 5, 15, 60               (milliQ runs exist only at 5 min)
    temp_C      25, 50, 75
    diluent     seawater | milliQ

The space is restricted to conditions that were actually measured, so that every
point has a ground-truth value. That is what makes the arms comparable.

OBJECTIVE
---------
Maximise `composite_J`, which is the recovery of REY excluding Ce, as a fraction.
Ce is tetravalent, locked in Fe-Mn oxides, and not recoverable by dilute acid, so
it is excluded by convention in this literature.

Acid consumption is reported alongside but is NOT part of the objective. That is
deliberate: reagent cost dominates the economics of a low-grade ore, so a proposal
that reaches high recovery by pouring in concentrated acid is a bad proposal even
though it scores well here. Whether you notice that is part of what is being
assessed.
"""

import argparse
import json
import os
import os.path as osp

from ree_oracle import MeasuredOracle, Recipe, build_oracle

# ============================================================================
# EDIT BELOW -- these are the recipes this run evaluates.
# ============================================================================

RECIPES = [
    # Baseline: the naive engineering default -- concentrated acid, long contact,
    # heated. It ranks 32nd of the 120 reachable conditions, so there is real
    # headroom. The published optimum for this ore is counter-intuitive and this
    # baseline does not sit near it.
    {"acid": "HCl", "conc_mol_L": 3.0, "time_min": 60, "temp_C": 75,
     "diluent": "seawater"},
]

# ============================================================================
# EDIT ABOVE -- harness code follows. Do not modify.
# ============================================================================

# Experimental arm, budget and subspace come from the environment so that the
# same experiment.py can be run under every arm without the agent editing them.
ARM = os.environ.get("REE_ORACLE_ARM", "B")        # A measured | B phreeqc | C disclosed
SUBSPACE = os.environ.get("REE_SUBSPACE", "all")   # all (S1) | h2so4 (S2)


def _grid(subspace: str) -> list[Recipe]:
    grid = MeasuredOracle().grid()
    if subspace == "h2so4":
        return [r for r in grid if r.acid == "H2SO4"]
    if subspace != "all":
        raise ValueError(f"unknown REE_SUBSPACE: {subspace}")
    return grid


def _as_recipe(spec: dict) -> Recipe:
    return Recipe(
        acid=spec["acid"], conc_mol_L=float(spec["conc_mol_L"]),
        time_min=float(spec["time_min"]), temp_C=float(spec["temp_C"]),
        diluent=spec.get("diluent", "seawater"),
    )


def main(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    grid = _grid(SUBSPACE)
    allowed = set(grid)
    oracle = build_oracle(ARM)
    truth = MeasuredOracle()          # harness-side scorer; the agent never sees it

    evaluated = []
    for spec in RECIPES:
        recipe = _as_recipe(spec)
        if recipe not in allowed:
            raise ValueError(
                f"recipe outside the search space: {spec}. "
                "See the SEARCH SPACE section at the top of this file.")
        result = oracle.evaluate(recipe)
        evaluated.append({"recipe": spec, **result.to_agent_dict()})

    if not evaluated:
        raise ValueError("RECIPES is empty -- nothing to evaluate")

    best = max(evaluated, key=lambda e: e["composite_J"])

    # --- what the agent is allowed to see -------------------------------
    means = {
        "best_composite_J": best["composite_J"],
        "best_rey_recovery_pct": best["rey_recovery_pct"],
        "best_acid_mol_per_kg": best["acid_consumption_mol_per_kg"],
        "n_recipes_evaluated": len(evaluated),
    }
    if "in_domain" in best:
        means["best_recipe_in_domain"] = best["in_domain"]
        means["n_out_of_domain"] = sum(
            1 for e in evaluated if e.get("in_domain") is False)

    # --- ground truth: sibling of `means`, so perform_experiments.py does
    #     NOT put it in the agent's prompt (it forwards only `means`).
    #     This is what keeps the comparison honest: the agent optimises the
    #     oracle's opinion, and we score it on a reality it never sees.
    best_recipe = _as_recipe(best["recipe"])
    true_best = max(truth.evaluate(r).composite_J for r in grid)
    ground_truth = {
        "true_composite_J_of_selected": truth.evaluate(best_recipe).composite_J,
        "true_rey_recovery_pct_of_selected":
            truth.evaluate(best_recipe).rey_recovery_pct,
        "true_best_composite_J_in_space": true_best,
        "regret": true_best - truth.evaluate(best_recipe).composite_J,
        "arm": ARM,
        "subspace": SUBSPACE,
    }

    final_info = {
        "leaching_search": {
            "means": means,
            "evaluated": evaluated,        # for plot.py
            "ground_truth": ground_truth,  # for the harness, hidden from the agent
        }
    }
    with open(osp.join(out_dir, "final_info.json"), "w") as f:
        json.dump(final_info, f, indent=2)
    print(json.dumps(means, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run experiment")
    parser.add_argument("--out_dir", type=str, default="run_0",
                        help="Output directory")
    args = parser.parse_args()
    main(args.out_dir)
