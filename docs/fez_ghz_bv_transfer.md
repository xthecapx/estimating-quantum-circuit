# H2 discovery campaign on Fez, November 23, 2026

One collection window, `20261123`. Both algorithm plans use campaign ID
`fez-ghz-bv-transfer-v1-2026-11-23`. The 10 configurations each receive two
independent jobs of 1,024 shots, for 20 jobs and 20,480 shots total.

## Research question

Can the change in GHZ success with logical two-qubit gate count predict the
change in Bernstein–Vazirani (BV) success for previously unmeasured secrets at
a fixed width? GHZ uses a chain of CNOTs. BV directs CNOTs from the selected
data qubits to a common ancilla. They have different success criteria and
routing costs. Transfer of the measured change across these constructions is
an empirical question.

The existing Fez runs cover BV12 at secret weights 1, 6, and 12. Earlier
comparisons aggregated BV configurations of different widths at the same gate
count. This window fills four missing levels specifically at 12 data qubits
(13 total). Each new secret consists of a prefix of ones followed by zeros.
Each GHZ source circuit has one more qubit than its logical CNOT count.
The mid-range pair, GHZ7 and BV12-ALT, connects the new window to the old ones.

| Logical CNOTs | GHZ | BV12 secret | BV role | FakeFez compiled CZs, GHZ / BV |
|---:|---|---|---|---|
| 3 | GHZ4 | 111000000000 | New | 3 / 3 |
| 5 | GHZ6 | 111110000000 | New | 5 / 11 |
| 6 | GHZ7 | 101010101010 | Historical anchor | 6 / 16 |
| 7 | GHZ8 | 111111100000 | New | 7 / 17 |
| 9 | GHZ10 | 111111111000 | New | 9 / 25 |

All ten logical circuits gave unit ideal success on their runner's accepted
outcomes in a noiseless statevector check. FakeFez counts use optimization
level 3 and transpiler seed 11. Use the actual prepared ISA counts, depth,
layout, and calibration for interpretation after execution.

## Predictions set before collection

Use raw accepted-shot probability as the primary outcome. Historical input is
the Fez export with dataset manifest SHA-256
`df66b9188c68d1d8864f24e78e5669e123133cb9c79bc0f9810518e2bd5784c8`.
Use the three Fez development windows containing all five GHZ configurations
and BV12-SINGLE, BV12-ALT, and BV12-ONES together: dataset-v2 window 1,
November 5 full collection, and November 6 full Shor-growth collection. Average
job success for each configuration within a window, then average windows equally.

Let G(k) denote historical mean GHZ success at k logical CNOTs and B(k) mean
BV12 success. The transfer prediction is B(6) + G(k) − G(6). This uses one
historical target anchor. The BV-only comparator linearly interpolates B(1),
B(6), and B(12). The constant comparator predicts B(6) everywhere.

| New BV configuration | GHZ transfer | BV-only interpolation | Constant |
|---|---:|---:|---:|
| BV12-PREFIX3 | 0.688802 | 0.787826 | 0.642904 |
| BV12-PREFIX5 | 0.658529 | 0.691211 | 0.642904 |
| BV12-PREFIX7 | 0.625488 | 0.607042 | 0.642904 |
| BV12-PREFIX9 | 0.551432 | 0.535319 | 0.642904 |

After recovery, average the two real job success rates for each new BV secret.
Report per-secret signed errors (prediction minus observation) and the mean
absolute error across the four secrets with equal weight. Lower MAE for GHZ
transfer than both comparators favors transfer in this window. Report ties,
disagreements and missing jobs explicitly. Use the new GHZ and BV anchor jobs
to describe drift and the two observed curves separately from the frozen score.

This tests transfer to unseen configurations within the historical resource
range. The four secrets and one collection date support a descriptive comparison.
GHZ width varies with gate count, and compiled CZ counts and BV bit positions
also vary. These runs cannot identify a per-gate causal effect or establish
repeatability across calibration windows.

## Results

All 20 jobs completed. Scored as stated above: mean of the two jobs per new
secret, error = prediction − observation.

| New BV configuration | Observed | GHZ transfer error | BV-only interpolation error | Constant error |
|---|---:|---:|---:|---:|
| BV12-PREFIX3 | 0.818 | −0.130 | −0.031 | −0.176 |
| BV12-PREFIX5 | 0.738 | −0.079 | −0.047 | −0.095 |
| BV12-PREFIX7 | 0.612 | +0.014 | −0.005 | +0.031 |
| BV12-PREFIX9 | 0.443 | +0.109 | +0.092 | +0.200 |
| **Mean absolute error** | | **0.083** | **0.044** | **0.125** |

**The pre-stated criterion was not met.** GHZ transfer has a lower MAE than the
constant comparator and a higher MAE than BV-only interpolation. This window
does not favor transfer of the GHZ change to BV12.

The miss is in the slope. From 3 to 9 logical CNOTs, BV12 success fell 37.6
percentage points and GHZ success fell 10.7. Drift does not explain it:
replacing the historical anchors with this window's GHZ7 and BV12-ALT jobs
gives a transfer MAE of 0.082. The two jobs of a configuration differ by at
most 0.044, well below the transfer errors at the ends of the range.

Anchors in this window against the historical means: BV12-ALT 0.674 against
0.643; GHZ4, GHZ6, GHZ7, GHZ8 and GHZ10 at 0.948, 0.941, 0.915, 0.874 and
0.841 against 0.939, 0.909, 0.893, 0.875 and 0.801.

Compiled circuits differ more than the logical count suggests. The prepared ISA
circuits have 3, 5, 6, 7 and 9 two-qubit gates for GHZ and 3, 11, 16, 17 and 25
for BV at the same logical CNOT counts. Per compiled two-qubit gate the two
losses are close, about 1.8 points for GHZ and 1.7 for BV. That comparison was
made after seeing the data. It is a hypothesis for a new window with predictions
fixed in advance, not a result of this one.

**Pre-registration cannot be verified from this repository.** The prediction
table, this document and the recovered job data entered git in one commit
(`805a3d2`, 2026-11-23 14:38 −05:00), minutes after the jobs ran (19:32 UTC).
The table reproduces to six decimals from the export with the manifest hash
cited above, which is the export that preceded this window. That is consistent
with predictions computed before collection. The history cannot prove it.

The transfer window is exploratory data. It is part of the Fez development
cohort in the decay and regression reports, so it cannot serve as a holdout.

## Collection

Run from the repository root with the project environment. The dated plans are
already generated. The first command validates them offline. Preparation reads
the current Fez calibration and freezes the hardware circuits. Submit only when
ready to use QPU time. Recover by the saved job IDs.

```sh
.venv/bin/python scripts/run.py ibm validate --date 2026-11-23 --backend ibm_fez --profile ghz-bv-transfer-v1
.venv/bin/python scripts/run.py ibm prepare --date 2026-11-23 --backend ibm_fez --profile ghz-bv-transfer-v1
.venv/bin/python scripts/run.py ibm submit-only --date 2026-11-23 --backend ibm_fez --profile ghz-bv-transfer-v1
.venv/bin/python scripts/run.py ibm recover --date 2026-11-23 --backend ibm_fez --profile ghz-bv-transfer-v1
```

The driver uses one 10-job batch per algorithm. Check recovered timestamps to
document their separation. If collection moves to a different date, generate
plans for the actual Bogotá date and use that identity for the single window.
Preserve the prediction table before submission. After recovery, export using
`scripts/run.py export-ibm` and follow the [decay runbook](DECAY_ANALYSIS.md)
to refresh the dashboard. Its full historical BV rows can mix widths, so use
the named configurations above for the primary H2 comparison.
