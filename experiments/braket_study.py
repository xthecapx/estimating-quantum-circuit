"""Budgeted collection on two Braket QPUs. The unit of observation is one task."""

import argparse
from collections import Counter
from decimal import Decimal
from pathlib import Path
import json
import random
import time
from tempfile import TemporaryDirectory

import pandas as pd

from experiments import aws_campaign as aws
from experiments.campaign_matrix import PAPERS, RUNNERS
from experiments.dataset_export import flatten

DEVICES = {"rigetti": aws.DEVICE_ARN, "ionq": aws.IONQ_ARN}
SHOTS = {"rigetti": 1024, "ionq": 100}
# The first three configurations in each family are training groups, the fourth is test.
DEVELOPMENT = {
    "ghz": ("GHZ3", "GHZ6", "GHZ10", "GHZ8"),
    "bv": ("BV3-ALT", "BV5-ONES", "BV8-ONES", "BV6-SINGLE"),
    "qft": ("SR3", "SR6", "SP6-P4", "SR4"),
    "pe": ("PE-T3", "PE-S4", "PE-Z6", "PE-T5"),
    "grover": ("S2-10", "S3-1", "M4-2", "H3-2"),
    "rv": ("RV2-D2", "RV3-D6", "RV5-D10", "RV4-D8"),
}
# Groups refer to prior exposure on this AWS device. Scaling is a design intention.
VALIDATION = (
    ("ghz", "GHZ3", "anchor"),
    ("rv", "RV2-D2", "anchor"),
    ("qft", "IV3-011", "new"),
    ("bv", "BV5-PAIR", "new"),
    ("rv", "RV2-D4-S7", "new"),
    ("rv", "RV7-D14", "larger"),
)
# Fully measured circuits allow the same post-processing on both devices.
IONQ_DEV = {"GHZ3", "GHZ10", "SR3", "SR6", "S3-1", "RV2-D2", "RV5-D10", "SR4", "RV4-D8", "H3-2"}
IONQ_VAL = {"GHZ3", "IV3-011", "RV2-D4-S7", "RV7-D14"}
STAGES = ("development-1", "development-2", "validation")
CAP = Decimal("200")
CAMPAIGN = "braket-repetitions-v1"
CAMPAIGN_DIR = PAPERS / "data" / CAMPAIGN
IONQ_CHECK_KEY = "ionq-1-SR6-r1"
IONQ_CHIP_PILOT = {
    "key": "ionq-sr8-r1",
    "vendor": "ionq",
    "stage": "chip-pilot",
    "window": 0,
    "repetition": 1,
    "algorithm": "qft",
    "config": "SR8",
    "split": "pilot",
    "group": "chip-pilot",
    "shots": 100,
}


def task_directory(root, row):
    """Resolve an algorithm record within this checkout, including older flat runs."""
    root = Path(root)
    if root.parts[-2:] == ("data", CAMPAIGN):
        algorithm_dir = RUNNERS[row["algorithm"]]["dir"]
        return root.parents[1] / algorithm_dir / "data" / "qpu" / "aws" / CAMPAIGN / row["key"]
    return root / row["key"]


def dataset_path(root):
    root = Path(root)
    if root.parts[-2:] == ("data", CAMPAIGN):
        return root.parents[1] / "dataset_out" / CAMPAIGN / "dataset.csv"
    return root / "dataset.csv"


def plan():
    """The agreed 108-task Rigetti and 14-task IonQ schedule."""
    rows = []
    for vendor in DEVICES:
        matched = vendor == "ionq"
        for window, stage in enumerate(STAGES, 1):
            if window == 2 and matched:
                continue
            if stage == "validation":
                selected = [
                    (a, c, "validation", g)
                    for a, c, g in VALIDATION
                    if not matched or c in IONQ_VAL
                ]
            else:
                selected = [
                    (a, c, "train" if i < 3 else "test", "development")
                    for a, configs in DEVELOPMENT.items()
                    for i, c in enumerate(configs)
                    if not matched or c in IONQ_DEV
                ]
            batch = []
            for algo, config, split, group in selected:
                for rep in range(1, 2 if matched else 3):
                    batch.append(
                        dict(
                            key=f"{vendor}-{window}-{config}-r{rep}",
                            vendor=vendor,
                            stage=stage,
                            window=window,
                            repetition=rep,
                            algorithm=algo,
                            config=config,
                            split=split,
                            group=group,
                            shots=SHOTS[vendor],
                        )
                    )
            random.Random(11 + window).shuffle(batch)
            rows.extend(batch)
    return rows


def estimate(rows):
    return sum((aws.task_price(DEVICES[r["vendor"]], r["shots"]) for r in rows), Decimal(0))


def check_budget(rows, available):
    available = Decimal(str(available))
    if not available.is_finite() or not estimate(rows) <= available <= CAP:
        raise ValueError(
            f"Full plan costs USD {estimate(rows)}. Enter available QPU funds up to 200."
        )


def open_campaign(root):
    root = Path(root)
    if root == CAMPAIGN_DIR and (PAPERS.parent / "braket-study-run" / "manifest.json").exists():
        raise ValueError(
            "Found an earlier braket-study-run campaign. Resume it with --run-dir braket-study-run."
        )
    root.mkdir(parents=True, exist_ok=True)
    return root


def prepare_task(root, row, bucket):
    """Freeze once under the campaign lock; preserve its client token across restarts."""
    directory = task_directory(root, row)
    if not directory.exists():
        directory.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=directory.parent) as scratch:
            temp = Path(scratch) / "task"
            aws.prepare(
                temp,
                bucket=bucket,
                prefix="qward/braket-study-v1",
                algorithm=row["algorithm"],
                config_id=row["config"],
                shots=row["shots"],
                device_arn=DEVICES[row["vendor"]],
                collection=row,
            )
            temp.rename(directory)
    prepared, journal = aws.load(directory)
    request = aws.read_json(directory / "request.json")
    completed_check = row["key"] == IONQ_CHECK_KEY and journal["status"] == "completed"
    if (
        prepared["collection"] != row
        or request["deviceArn"] != DEVICES[row["vendor"]]
        or request["shots"] != row["shots"]
        or prepared["config_id"] != row["config"]
        or (request["outputS3Bucket"] != bucket and not completed_check)
    ):
        raise ValueError(f"Existing task conflicts with this preparation: {row['key']}")
    return journal


def prepare(root, buckets):
    """Freeze all requests, retaining the IonQ hardware check's original task and result."""
    root = open_campaign(root)
    rows = plan()
    with aws.locked(root):
        manifest = root / "manifest.json"
        spec = {"design": "repetitions-v1", "rows": rows, "buckets": buckets}
        if manifest.exists():
            saved = aws.read_json(manifest)
            if any(saved[k] != v for k, v in spec.items()):
                raise ValueError("Frozen plan or bucket differs from the selected campaign")
            list(records(root))
            return
        hashes = {}
        for row in rows:
            key = row["key"]
            journal = prepare_task(root, row, buckets[row["vendor"]])
            if key != IONQ_CHECK_KEY and journal["status"] != "prepared":
                raise ValueError(f"Unexpected submitted record before campaign freeze: {key}")
            hashes[key] = journal["prepared_hash"]
        aws.write_json(manifest, {**spec, "hashes": hashes})


def records(root):
    root = Path(root)
    manifest = aws.read_json(root / "manifest.json")
    if manifest["rows"] != plan():
        raise ValueError("Plan differs from the frozen version. Use the original checkout.")
    for row in manifest["rows"]:
        path = task_directory(root, row)
        p, j = aws.load(path)
        if (
            j["prepared_hash"] != manifest["hashes"][row["key"]]
            or p["collection"] != row
            or p["device_arn"] != DEVICES[row["vendor"]]
            or p["shots"] != row["shots"]
        ):
            raise ValueError(f"Frozen task differs from manifest: {path}")
        yield row, path, p, j


def ionq_check(root, bucket, profile=None, *, submit=False, task_arn=None):
    """Run only the scheduled one-hundred-shot SR6 task and verify its exported result."""
    root = open_campaign(root)
    row = next(r for r in plan() if r["key"] == IONQ_CHECK_KEY)
    path = task_directory(root, row)
    with aws.locked(root):
        if (root / "manifest.json").exists():
            # A missing or replaced task in a frozen campaign must never be re-created.
            list(records(root))
        journal = prepare_task(root, row, bucket)
    return run_ionq_record(path, row, journal, profile, submit, task_arn)


def ionq_chip_pilot(root, bucket, profile=None, *, submit=False, task_arn=None):
    """Collect one SR8 task outside the training and validation campaign."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    row = IONQ_CHIP_PILOT
    with aws.locked(root):
        journal = prepare_task(root, row, bucket)
    path = task_directory(root, row)
    exported = run_ionq_record(path, row, journal, profile, submit, task_arn)
    if exported is not None:
        from experiments.chip_inventory import write_inventory

        print("Chip metadata inventory:", write_inventory(path))
    return exported


def run_ionq_record(path, row, journal, profile, submit, task_arn):
    print(
        f"{row['key']} | {aws.IONQ_ARN} | {row['shots']} shots | "
        f"USD {estimate([row]):.2f} | {path}",
        flush=True,
    )
    if not submit and not task_arn:
        return
    if journal["status"] != "completed":
        client = aws.AWSClient(profile, aws.IONQ_ARN.split(":")[3])
        if task_arn is None:
            if journal["status"] in {"submitting", "submission_unknown"}:
                raise ValueError(
                    f"Find the task tagged qward-run-id={aws.read_json(path / 'prepared.json')['run_id']} "
                    "in Braket and rerun with --task-arn ARN"
                )
            print(aws.submit(path, client), flush=True)
        while True:
            result = aws.recover(path, client, task_arn)
            print(result, flush=True)
            if result["status"] == "completed":
                break
            if result["status"] in {"failed", "cancelled"}:
                raise RuntimeError(f"IonQ task ended {result['status']}: {result.get('error')}")
            time.sleep(60)
    prepared, journal = aws.load(path)
    if task_arn and task_arn != journal["task_arn"]:
        raise ValueError("Task ARN differs from the saved task")
    exported = dataset_row(row, path, prepared, journal)
    counts = json.loads(exported["f.counts_json"])
    (expected,) = prepared["success_set"]
    print(
        f"Recovered {sum(counts.values())} shots; measured {expected} {counts.get(expected, 0)} times. "
        f"Result: {path / 'result.json'}"
    )
    return exported


def clients(profile):
    return {vendor: aws.AWSClient(profile, arn.split(":")[3]) for vendor, arn in DEVICES.items()}


def preflight(root, connections, stage):
    """Check every selected action before allowing the first paid call in the stage."""
    entries = list(records(root))
    for row, path, _, journal in entries:
        if row["stage"] == stage and journal["status"] == "prepared":
            aws.preflight(path, connections[row["vendor"]])


def submit_stage(root, connections, stage, available, *, first_per_device=False):
    if stage not in STAGES:
        raise ValueError("Unknown collection stage")
    with aws.locked(root):
        entries = list(records(root))
        check_budget([r for r, *_ in entries], available)
        for row, _, _, journal in entries:
            if STAGES.index(row["stage"]) < STAGES.index(stage) and journal["status"] not in {
                "completed",
                "failed",
                "cancelled",
            }:
                raise ValueError(f"Recover the earlier stage first: {row['key']}")
        if stage == "validation":
            verify_predictions(root, entries)
        preflight(root, connections, stage)
        selected = set()
        for row, path, _, _ in entries:
            vendor = row["vendor"]
            if row["stage"] != stage or (first_per_device and vendor in selected):
                continue
            aws.submit(path, connections[vendor])
            selected.add(vendor)


def recover_stage(root, connections, stage, reconciled=None):
    """One pass; an unknown submission may be reconciled with its console task ARN."""
    statuses = Counter()
    for row, path, _, journal in records(root):
        if row["stage"] != stage:
            continue
        status = journal["status"]
        if status not in ("completed", "failed", "cancelled", "prepared"):
            arn = (reconciled or {}).get(row["key"])
            if not journal["task_arn"] and not arn:
                raise ValueError(
                    f"Look up the task tagged qward-run-id in {path}/prepared.json; "
                    f"set RECONCILED[{row['key']!r}] to its ARN and recover again."
                )
            status = aws.recover(path, connections[row["vendor"]], arn)["status"]
        statuses[status] += 1
    return dict(statuses)


def dataset_row(row, path, prepared, journal):
    result = aws.read_json(path / "result.json")
    if (
        aws.file_hash(path / "result.json") != journal["result_hash"]
        or aws.file_hash(path / "raw_result.json") != result["raw_result_sha256"]
        or result["task_arn"] != journal["task_arn"]
    ):
        raise ValueError(f"Recovered result failed integrity verification: {path}")
    vendor = row["vendor"]
    out = {
        "meta.provider": vendor,
        "meta.backend_name": prepared["device_arn"].split("/")[-1],
        "meta.algorithm": prepared["algorithm_name"],
        "meta.config_id": prepared["config_id"],
        "meta.job_id": journal["task_arn"],
        "meta.run_id": prepared["run_id"],
        "meta.run_index": row["repetition"],
        "meta.window": row["window"],
        "meta.campaign_id": (
            "ionq-sr8-chip-pilot"
            if row["split"] == "pilot"
            else (
                f"{vendor}-validation-v1"
                if row["split"] == "validation"
                else f"{vendor}-development-v1"
            )
        ),
        "meta.shots": result["shots"],
        "meta.optimization_level": prepared["optimization_level"],
        "meta.split": row["split"],
        "meta.validation_group": row["group"],
        "g.device_arn": prepared["device_arn"],
        "g.region": prepared["region"],
        "g.submitted_at": (
            journal["submitted_at"]
            if "submitted_at" in journal
            else journal["submission_started_at"]
        ),
        "g.finished_at": aws.read_json(path / "task_metadata.json").get("endedAt"),
        "g.seed_transpiler": prepared["seed_transpiler"],
        "g.compiler_policy": prepared["compiler_policy"],
        "g.logical_circuit_hash": prepared["logical_circuit_hash"],
        "g.estimated_usd": prepared["cost_estimate_usd"],
        "f.counts_json": json.dumps(result["counts"], sort_keys=True),
        "f.success_interval_95_wilson": json.dumps(result["success_interval_95_wilson"]),
    }
    for group, values in (
        ("a", prepared["logical_features"]),
        ("submitted", prepared["submitted_qiskit_features"]),
    ):
        features = dict(values)
        flatten(features.pop("qward_metrics", {}), group, out)
        flatten(features, group, out)
    snapshot = aws.read_json(path / "profile_at_submission.json")
    out["g.profile_at_submission"] = snapshot["captured_at"]
    flatten(prepared["config"], "config", out)
    profile = snapshot["profile"]
    if vendor == "ionq":
        flatten((profile["provider"] or {}).get("fidelity", {}), "c.ionq_fidelity", out)
    else:
        # Retain benchmark type and gate name. Provider-specific statistics are device-wide.
        from statistics import median
        from collections import defaultdict

        fidelities = defaultdict(list)
        for section, field in (
            ("oneQubitProperties", "oneQubitFidelity"),
            ("twoQubitProperties", "twoQubitGateFidelity"),
        ):
            for item in (profile["standardized"].get(section) or {}).values():
                for benchmark in item.get(field) or []:
                    name = (benchmark.get("fidelityType") or {}).get("name")
                    value = benchmark.get("fidelity")
                    if name and value is not None:
                        key = ".".join(filter(None, (field, benchmark.get("gateName"), name)))
                        fidelities[key].append(value)
        for key, values in fidelities.items():
            out[f"c.rigetti_fidelity.{key}.median"] = median(values)
    flatten(prepared["package_versions"], "g.version", out)
    flatten(result["targets"], "f", out)
    return out


def export_csv(root):
    """Rebuild the completed task table from the checked-out records, entirely offline."""
    root = Path(root)
    rows = [
        dataset_row(row, path, p, j)
        for row, path, p, j in records(root)
        if j["status"] == "completed"
    ]
    if not rows:
        raise ValueError("No completed tasks have been recovered")
    frame = pd.DataFrame(rows)
    if not frame["meta.job_id"].is_unique:
        raise ValueError("Repeated task ARN in frozen campaign")
    destination = dataset_path(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as scratch:
        tmp = Path(scratch) / "dataset.csv"
        frame.to_csv(tmp, index=False)
        tmp.replace(destination)
    return frame


def prediction_keys(entries):
    return {(row["vendor"], row["config"]) for row, *_ in entries if row["split"] == "validation"}


def freeze_predictions(root, predictions, model_id):
    """Bind one out-of-sample prediction per QPU/config/target to the prepared requests."""
    from experiments.ml_dataset import TARGETS

    root = Path(root)
    with aws.locked(root):
        entries = list(records(root))
        file = root / "predictions.json"
        if file.exists():
            verify_predictions(root, entries)
            raise ValueError("Predictions already frozen; use the existing predictions.json")
        if any(j["status"] != "prepared" for r, _, _, j in entries if r["split"] == "validation"):
            raise ValueError("Freeze predictions before any validation submission")
        if not str(model_id).strip():
            raise ValueError("Identify the frozen model or model revision")
        predictions = predictions[["vendor", "config", *TARGETS]].copy()
        keys = list(zip(predictions["vendor"], predictions["config"]))
        if len(set(keys)) != len(keys) or set(keys) != prediction_keys(entries):
            raise ValueError(
                "Expected exactly one prediction per validation device and configuration"
            )
        for target in TARGETS:
            predictions[target] = pd.to_numeric(predictions[target], errors="raise")
            if not predictions[target].between(0, 1).all():
                raise ValueError(f"Missing or out-of-range prediction for {target}")
        aws.write_json(
            file,
            {
                "model_id": model_id,
                "frozen_at": aws.now(),
                "manifest_sha256": aws.file_hash(root / "manifest.json"),
                "predictions": predictions.to_dict("records"),
            },
        )
        aws.write_json(root / "prediction_hash.json", aws.file_hash(file))


def verify_predictions(root, entries):
    root = Path(root)
    file = root / "predictions.json"
    if not file.exists():
        raise ValueError("Freeze prospective predictions before submitting validation")
    frozen = aws.read_json(file)
    if (
        aws.read_json(root / "prediction_hash.json") != aws.file_hash(file)
        or frozen["manifest_sha256"] != aws.file_hash(root / "manifest.json")
        or {(p["vendor"], p["config"]) for p in frozen["predictions"]} != prediction_keys(entries)
    ):
        raise ValueError("Frozen predictions or their campaign have changed")


def prediction_template(root):
    from experiments.ml_dataset import TARGETS

    path = root / "validation-input.csv"
    if not path.exists():
        keys = sorted(prediction_keys(records(root)))
        grid = pd.DataFrame(keys, columns=["vendor", "config"])
        grid[list(TARGETS)] = float("nan")
        grid.to_csv(path, index=False)
    return path


def training_baseline(root):
    """Predict each prospective circuit using training configuration means on its device."""
    from experiments.ml_dataset import TARGETS

    entries = list(records(root))
    if any(j["status"] != "completed" for r, _, _, j in entries if r["split"] == "train"):
        raise ValueError("Complete the training collection before fitting the baseline")
    frame = export_csv(root)
    train = frame.loc[frame["meta.split"] == "train"]
    by_config = train.groupby(["meta.provider", "meta.algorithm", "meta.config_id"])
    means = by_config.mean(numeric_only=True).groupby(level=[0, 1]).mean()
    predictions = {}
    for row, _, prepared, _ in entries:
        if row["split"] == "validation":
            values = means.loc[(row["vendor"], prepared["algorithm_name"])]
            predictions[(row["vendor"], row["config"])] = {
                "vendor": row["vendor"],
                "config": row["config"],
                **{target: values[col] for target, (col, _, _) in TARGETS.items()},
            }
    return pd.DataFrame(predictions.values())


def validation_errors(root):
    from experiments.ml_dataset import TARGETS

    verify_predictions(root, list(records(root)))
    frame = export_csv(root)
    observed = frame.loc[frame["meta.split"] == "validation"].rename(
        columns={"meta.provider": "vendor", "meta.config_id": "config"}
    )
    frozen = pd.DataFrame(aws.read_json(root / "predictions.json")["predictions"])
    joined = observed.merge(frozen, on=["vendor", "config"], validate="many_to_one")
    errors = pd.DataFrame(
        {target: (joined[target] - joined[col]).abs() for target, (col, _, _) in TARGETS.items()}
    )
    return errors.groupby([joined["vendor"], joined["config"]]).mean()


def main(argv=None):
    """Python entry point shared by scripts/run.py and the notebook."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="campaign manifest directory (defaults to this checkout)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="list scheduled tasks and total QPU price")
    for name, help_text in (
        ("ionq-check", "verify the scheduled SR6 task on Forte-1"),
        ("ionq-chip-pilot", "collect one independent SR8 task and inventory the chip metadata"),
    ):
        check = commands.add_parser(name, help=help_text)
        check.add_argument("--bucket", required=True, help="existing result bucket in us-east-1")
        check.add_argument("--profile")
        action = check.add_mutually_exclusive_group()
        action.add_argument("--submit", action="store_true", help="submit once (USD 8.30) and wait")
        action.add_argument("--task-arn", help="recover the original ARN after an ambiguous submit")
    prep = commands.add_parser("prepare", help="freeze the requests offline")
    prep.add_argument("--rigetti-bucket", required=True)
    prep.add_argument("--ionq-bucket", required=True)
    prep.add_argument("--available-usd", required=True)
    for name in ("preflight", "submit", "recover"):
        command = commands.add_parser(name)
        command.add_argument("--stage", choices=STAGES, required=True)
        command.add_argument("--profile")
        if name == "submit":
            command.add_argument("--available-usd", required=True)
            command.add_argument("--first-per-device", action="store_true")
        if name == "recover":
            command.add_argument("--wait", action="store_true")
            command.add_argument(
                "--task",
                nargs=2,
                action="append",
                metavar=("KEY", "ARN"),
                help="reconcile an ambiguous submission using its saved run ID tag",
            )
    commands.add_parser("export", help="rebuild the AWS CSV offline from recovered records")
    commands.add_parser("prediction-template")
    freeze = commands.add_parser("freeze-predictions")
    model = freeze.add_mutually_exclusive_group(required=True)
    model.add_argument("--baseline", action="store_true")
    model.add_argument(
        "--model-id", help="revision for predictions entered in validation-input.csv"
    )
    commands.add_parser("score", help="report prospective errors by device and configuration")
    args = parser.parse_args(argv)
    default_root = (
        PAPERS / "data" / "aws_pilot" if args.command == "ionq-chip-pilot" else CAMPAIGN_DIR
    )
    root = (args.run_dir or default_root).resolve()
    if args.command == "plan":
        rows = plan()
        print(pd.DataFrame(rows).to_string(index=False))
        print(f"{len(rows)} tasks, USD {estimate(rows):.4f}")
    elif args.command == "ionq-chip-pilot":
        ionq_chip_pilot(root, args.bucket, args.profile, submit=args.submit, task_arn=args.task_arn)
    elif args.command == "ionq-check":
        ionq_check(root, args.bucket, args.profile, submit=args.submit, task_arn=args.task_arn)
    elif args.command == "prepare":
        check_budget(plan(), args.available_usd)
        prepare(root, {"rigetti": args.rigetti_bucket, "ionq": args.ionq_bucket})
        print(root / "manifest.json")
    elif args.command == "export":
        frame = export_csv(root)
        print(frame.groupby(["meta.provider", "meta.split"]).size().to_string())
        print(dataset_path(root))
    elif args.command == "prediction-template":
        print(prediction_template(root))
    elif args.command == "freeze-predictions":
        if args.baseline:
            freeze_predictions(root, training_baseline(root), "train-config-family-mean-v1")
        else:
            freeze_predictions(root, pd.read_csv(root / "validation-input.csv"), args.model_id)
        print(root / "predictions.json")
    elif args.command == "score":
        print(validation_errors(root).to_string())
    else:
        connections = clients(args.profile)
        if args.command == "preflight":
            print({vendor: client.identity()["Account"] for vendor, client in connections.items()})
            preflight(root, connections, args.stage)
            print(f"Preflight passed for {args.stage}")
        elif args.command == "submit":
            submit_stage(
                root,
                connections,
                args.stage,
                args.available_usd,
                first_per_device=args.first_per_device,
            )
        else:
            while True:
                states = recover_stage(root, connections, args.stage, dict(args.task or []))
                print(states, flush=True)
                if not args.wait or not (
                    set(states) - {"prepared", "completed", "failed", "cancelled"}
                ):
                    break
                time.sleep(60)


if __name__ == "__main__":
    main()
