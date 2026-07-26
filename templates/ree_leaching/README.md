# `ree_leaching` — REE leaching recipe search

Acid leaching of rare-earth-rich deep-sea mud (Minamitorishima EEZ, Japan) as an
AI Scientist v1 template. The wet experiment is replaced by a PHREEQC equilibrium
oracle that scores a recipe in seconds.

Part of [Project REE](https://github.com/moozwen/ree-scientist). The scientific
design lives there:

| Document | What it covers |
|---|---|
| `notes/phase-0/results/calibration_report.md` | How the oracle was calibrated and where it fails (verdict: partial pass, rho ~ 0.72-0.77) |
| `notes/phase-1/oracle_aware_loop.md` | The three-arm experiment this template implements |

## Prerequisite

`ree_oracle` must be importable, and it needs the `llnl.dat` thermodynamic
database (not redistributed — see `db/PROVENANCE.md` in the project repo).

```bash
pip install -e ~/Projects/sakana/ree-scientist/src/ree_oracle
python -c "import ree_oracle; print('ok')"
```

## Generate the baseline, then launch

`templates/*/run_0/` is gitignored upstream, so `run_0` has to be created before
the first launch. That is also true of every other template here.

```bash
cd templates/ree_leaching
REE_ORACLE_ARM=B python experiment.py --out_dir=run_0

cd ../..
python launch_scientist.py --experiment ree_leaching --model gpt-4o-mini --num-ideas 4
```

## Environment variables

The agent edits only `RECIPES` in `experiment.py`. Everything that defines the
*experimental condition* is passed through the environment so the agent cannot
see or change it.

| Variable | Values | Meaning |
|---|---|---|
| `REE_ORACLE_ARM` | `A` | Ground truth. Returns the published measurement. Zero error by construction |
| | `B` | The calibrated PHREEQC oracle. Imperfect, and says nothing about it |
| | `C` | The same oracle, plus disclosure of where it is trustworthy |
| `REE_SUBSPACE` | `all` | Scenario S1 — all 120 measured conditions. The true optimum is inside the oracle's validated regime |
| | `h2so4` | Scenario S2 — the 60 sulfuric-acid conditions. The true optimum sits **outside** the validated regime, 8.2 points above the best in-regime recipe |

Arms B and C return **identical numbers**. The only difference is whether
`in_domain`, `reliability` and `domain_note` are exposed. That keeps the
comparison about disclosure rather than about accuracy.

## How scoring stays honest

`perform_experiments.py` forwards only the `means` block of `final_info.json`
into the agent's prompt. The ground truth is written to a sibling key,
`ground_truth`, so the agent never sees it during the search.

The agent optimises what the oracle claims. We score it against a reality it
cannot observe. The gap between those two is the measurement this template
exists to make.

## Baseline

`run_0` is the naive engineering default — concentrated acid, long contact,
heated (3.0 M HCl / 60 min / 75 °C). It ranks 32nd of the 120 reachable
conditions. The published optimum for this ore is counter-intuitively mild
(dilute acid, minutes, room temperature), so rediscovering it is a real task
rather than a formality.

Under arm B the oracle claims 100% recovery for this baseline. The measured
value is 87.27%. Arm C reports the same 100% but flags the condition as outside
the calibrated regime.
