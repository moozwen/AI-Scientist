"""Write `prompt.json` and `experiment.py`'s header for one experimental arm.

Run this before `launch_scientist.py`. It exists to keep the three arms honest.

Why this is needed
------------------
The three-arm design (see `notes/phase-1/oracle_aware_loop.md` in the Project REE
repo) says arms B and C return **identical numbers**, and differ only in whether
the oracle discloses where it is trustworthy. That only holds if the disclosure
lives in exactly one place.

The first version of this template failed that: `prompt.json` stated the
calibration statistics and the time blindness, so arms A and B were told the
oracle's limitations too. An idea generated under arm C then correctly reasoned
about those limits -- but it would have done the same under arm B, because the
prompt gave the game away. That is a confound, not a result.

So: `arm_prompts/prompt.base.json` is arm-neutral, and
`arm_prompts/disclosure_C.txt` is appended only for arm C. The same rule applies
to `experiment.py`'s docstring, which the agent also reads.

Usage
-----
    python materialize_arm.py --arm C
    REE_ORACLE_ARM=C python experiment.py --out_dir=run_0
    cd ../.. && python launch_scientist.py --experiment ree_leaching --model claude-sonnet-5
"""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PROMPT = HERE / "arm_prompts" / "prompt.base.json"
DISCLOSURE_C = HERE / "arm_prompts" / "disclosure_C.txt"
PROMPT = HERE / "prompt.json"
EXPERIMENT = HERE / "experiment.py"

# The docstring paragraph in experiment.py that describes the oracle. Replaced
# wholesale so the file the agent reads matches the arm it is running under.
MARKER_START = "WHAT THE ORACLE IS\n------------------\n"
MARKER_END = "\nSEARCH SPACE"

NEUTRAL_BODY = """A computational oracle that scores a leaching recipe in seconds instead of running a
wet experiment. It is a screening device: treat its output as a ranking signal,
not as a measured truth."""

DISCLOSED_BODY = """A PHREEQC equilibrium model of apatite dissolution + gypsum coprecipitation,
calibrated against the 120 published measurements of Takaya et al. (2015).

**The oracle is NOT an accurate predictor.** Its rank correlation with the
measurements is only rho ~ 0.72-0.77 across all conditions -- lower than a
trivial predictor that looks at nothing but the acid type (rho = 0.818). It
reaches rho = 0.876-0.929 only near 25 C; at 50 C and 75 C it invents a
temperature dependence the measurements do not show, and the ranking inverts.
It is blind to leaching time by construction. Every score carries `in_domain`,
`reliability` and `domain_note` saying whether that condition is inside the
calibrated regime."""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", required=True, choices=["A", "B", "C"],
                    help="A measured | B phreeqc | C phreeqc + disclosure")
    args = ap.parse_args()

    prompt = json.loads(BASE_PROMPT.read_text())
    if args.arm == "C":
        prompt["task_description"] += " " + DISCLOSURE_C.read_text().strip()
    PROMPT.write_text(json.dumps(prompt, indent=4, ensure_ascii=False) + "\n")

    src = EXPERIMENT.read_text()
    i, j = src.index(MARKER_START) + len(MARKER_START), src.index(MARKER_END)
    body = DISCLOSED_BODY if args.arm == "C" else NEUTRAL_BODY
    EXPERIMENT.write_text(src[:i] + body + "\n" + src[j:])

    disclosed = args.arm == "C"
    print(f"arm {args.arm}: disclosure={'on' if disclosed else 'off'}")
    print(f"  {PROMPT.name}: task_description "
          f"{'includes' if disclosed else 'omits'} the calibration summary")
    print(f"  {EXPERIMENT.name}: oracle section "
          f"{'includes' if disclosed else 'omits'} it")
    print(f"\n  次: REE_ORACLE_ARM={args.arm} python experiment.py --out_dir=run_0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
