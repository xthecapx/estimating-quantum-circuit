"""validation-v1: the QAQS prospective validation workload.

One profile, run once per chip. Every configuration belongs to exactly one group:

* ``anchor`` -- configurations already in the training data. A new calibration cycle
  with known circuits; isolates calibration drift.
* ``new`` -- configurations never executed, inside the measured size range of their
  algorithm (compiled two-qubit gates <= the largest measured configuration). Tests H1 on unseen circuits *and* a new calibration cycle.
* ``extrapolation`` -- configurations larger than anything measured for their
  algorithm, in compiled two-qubit gates (the H2 scaling axis). Tests H2 scaling (the decay limit).

The groups are fixed here, before any execution, and are part of the pre-registration
(``experiments/qaqs_prospective.py`` records them next to each prediction).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

PROFILE_NAME = "validation-v1"
RUNS = 2
SHOTS = 1024

# (algorithm key, config_id, group)
ITEMS: Tuple[Tuple[str, str, str], ...] = (
    # --- anchors: low / mid / high compiled size per algorithm, success > 15% on Kingston
    ("ghz", "GHZ3", "anchor"),
    ("ghz", "GHZ16", "anchor"),
    ("bv", "BV3-ONES", "anchor"),
    ("bv", "BV9-SINGLE", "anchor"),
    ("bv", "BV14-ONES", "anchor"),
    ("vtp", "VTP-S1-FIVE", "anchor"),
    ("vtp", "VTP-S3-TRIPLE", "anchor"),
    ("vtp", "VTP-V5-TRIPLE", "anchor"),
    ("qft", "SR2", "anchor"),
    ("qft", "IV4-0001", "anchor"),
    ("qft", "SR8", "anchor"),
    ("pe", "PE-Z2", "anchor"),
    ("pe", "PE-S5", "anchor"),
    ("pe", "PE-T8", "anchor"),
    ("grover", "M3-4", "anchor"),
    ("grover", "H3-2", "anchor"),
    ("grover", "H5-0", "anchor"),
    ("rv", "RV2-D2", "anchor"),
    ("rv", "RV8-D8", "anchor"),
    ("shor", "SHOR-N15-A4-M3", "anchor"),
    # --- new: never executed, inside the measured range
    ("bv", "BV5-PAIR", "new"),
    ("bv", "BV7-HALF", "new"),
    ("bv", "BV9-EDGE", "new"),
    ("bv", "BV11-PAIR", "new"),
    ("qft", "IV3-011", "new"),
    ("qft", "IV5-10011", "new"),
    ("qft", "IV6-110100", "new"),
    ("qft", "IV7-1001011", "new"),
    ("rv", "RV2-D4-S7", "new"),
    ("rv", "RV3-D6-S7", "new"),
    ("rv", "RV4-D8-S7", "new"),
    ("rv", "RV5-D10-S7", "new"),
    ("rv", "RV6-D12", "new"),
    # --- extrapolation: larger than any measured configuration of the algorithm
    ("ghz", "GHZ18", "extrapolation"),
    ("ghz", "GHZ20", "extrapolation"),
    ("pe", "PE-T9", "extrapolation"),
    ("pe", "PE-S9", "extrapolation"),
    ("pe", "PE-Z10", "extrapolation"),
    ("qft", "SR10", "extrapolation"),
    ("qft", "SP12-P8", "extrapolation"),
    ("rv", "RV7-D14", "extrapolation"),
    ("rv", "RV9-D9", "extrapolation"),
)

GROUPS = ("anchor", "new", "extrapolation")


def group_of() -> Dict[str, str]:
    """config_id -> group."""
    return {config: group for _, config, group in ITEMS}


def items_by_algorithm() -> Dict[str, List[str]]:
    """Algorithm key -> config_ids, in declaration order."""
    out: Dict[str, List[str]] = {}
    for key, config, _ in ITEMS:
        out.setdefault(key, []).append(config)
    return out


def validate() -> None:
    """Fail fast on duplicates, unknown groups or config ids the runners cannot build."""
    from experiments.bv.bv_configs import CONFIGS_BY_ID as BV
    from experiments.ghz.ghz_configs import CONFIGS_BY_ID as GHZ
    from experiments.grover.grover_configs import CONFIGS_BY_ID as GROVER
    from experiments.phase_estimation.pe_configs import CONFIGS_BY_ID as PE
    from experiments.qft.qft_configs import CONFIGS_BY_ID as QFT
    from experiments.random_volumetric.rv_configs import CONFIGS_BY_ID as RV
    from experiments.shor.shor_configs import CONFIGS_BY_ID as SHOR
    from experiments.vtp.vtp_configs import CONFIGS_BY_ID as VTP

    known = {"ghz": GHZ, "bv": BV, "vtp": VTP, "qft": QFT, "pe": PE, "grover": GROVER, "rv": RV, "shor": SHOR}
    configs = [config for _, config, _ in ITEMS]
    if len(set(configs)) != len(configs):
        raise ValueError("validation-v1 lists a configuration twice")
    for key, config, group in ITEMS:
        if group not in GROUPS:
            raise ValueError(f"Unknown group {group!r} for {config}")
        if config not in known[key]:
            raise ValueError(f"{key} runner cannot build {config}")


def planned_jobs() -> int:
    return RUNS * len(ITEMS)
