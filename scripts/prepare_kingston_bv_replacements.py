#!/usr/bin/env python3
"""Prepare four linked replacements for the November 11 Kingston BV failures.

Run from the thesis repository root. Reads IBM calibration; never submits jobs.
An existing replacement manifest is validated and reused without cloud access.
"""

from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.bv.bv_ibm import BVIBMExperiment
from experiments.ibm_campaign import manifest_record_path, service_from_env, write_json
from experiments.ibm_experiment_base import resolve_ibm_credentials

STEM = "bv-kingston-full-oracle-growth-d2026-11-11-replacements-r1"
PLAN = ROOT / "experiments/bv/plans" / f"{STEM}.json"
MANIFEST = PLAN.with_name(f"{STEM}_manifest.json")
SOURCE = PLAN.with_name("bv-kingston-full-oracle-growth-d2026-11-11_manifest_part01.json")
CONFIGS = ("BV2-ALT", "BV2-SINGLE", "BV3-ONES", "BV3-ALT")


def main():
    campaign = BVIBMExperiment().campaign()
    source = json.loads(SOURCE.read_text())
    originals = {}
    links = {}
    for config in CONFIGS:
        item = next(i for i in source["items"] if i["config"] == config)
        record_path = manifest_record_path(SOURCE, item)
        journal, frozen, _ = campaign.store.load(record_path)
        failed = [
            e
            for e in journal["submission_journal"]
            if e.get("error") and "1217" in e["error"] and e["run_index"] == 1
        ]
        if len(failed) != 1 or not failed[0].get("job_id"):
            raise ValueError(f"Expected one saved second-repetition failure for {config}")
        originals[config] = frozen
        links[config] = {
            "campaign_id": source["campaign_id"],
            "record_path": record_path.relative_to(ROOT).as_posix(),
            "prepared_hash": journal["prepared_hash"],
            "job_id": failed[0]["job_id"],
            "run_index": failed[0]["run_index"],
            "reason": "IBM terminal ERROR 1217: Session has been closed; verified read-only",
        }
    plan = {
        "backend": "ibm_kingston",
        "campaign_id": "kingston-full-oracle-growth-2026-11-11-bv-replacements-r1",
        "window": 20261111,
        "shots": 1024,
        "optimization_level": 3,
        "seed_transpiler": 11,
        "order_seed": 202611111,
        "runs": 1,
        "planned_executions": 4,
        "purpose": "One replacement for each of four terminal BV failures; preserve original attempts",
        "source_manifest": SOURCE.relative_to(ROOT).as_posix(),
        "items": [{"config": c, "replacement_of": links[c]} for c in CONFIGS],
    }
    if PLAN.exists():
        if json.loads(PLAN.read_text()) != plan:
            raise ValueError("Existing replacement plan differs; refusing to overwrite")
    else:
        write_json(PLAN, plan)
    if not MANIFEST.exists():
        build = campaign.store.hooks.build

        def build_linked(config):
            item = build(config)
            return replace(item, payload={**item.payload, "replacement_of": links[config]})

        campaign.store.hooks.build = build_linked
        campaign.prepare_plan(PLAN, service_from_env(**resolve_ibm_credentials()))
    manifest = json.loads(MANIFEST.read_text())
    if manifest["jobs_planned"] != 4 or [i["config"] for i in manifest["items"]] != list(CONFIGS):
        raise ValueError("Replacement manifest has an unexpected workload")
    for item in manifest["items"]:
        _, frozen, _ = campaign.store.load(manifest_record_path(MANIFEST, item))
        for field in (
            "logical_circuit_hash",
            "shots",
            "optimization_level",
            "seed_transpiler",
            "runtime_options",
            "reference",
        ):
            if frozen[field] != originals[item["config"]][field]:
                raise ValueError(f"Replacement differs in {field}: {item['config']}")
        if frozen["payload"]["replacement_of"] != links[item["config"]]:
            raise ValueError("Frozen replacement provenance differs")
    print(f"Verified four linked replacements; manifest status: {manifest['status']}")
    print(MANIFEST.relative_to(ROOT))
    print("No QPU jobs submitted.")


if __name__ == "__main__":
    main()
