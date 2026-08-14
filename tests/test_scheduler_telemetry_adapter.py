from __future__ import annotations

import pytest

from scheduler_telemetry_adapter import SchedulerTelemetryError, build_contract_payload
from useful_gpu_minute_contract import UsefulGpuMinuteContract, UsefulGpuMinuteContractRequest


CONTRACT = {
    "min_useful_ratio": 0.70,
    "max_time_to_useful_minutes": 3.0,
    "max_failure_fraction": 0.10,
}


def interval(run: str, phase: str, start: float, end: float):
    return {
        "run_id": run,
        "phase": phase,
        "start_seconds": start,
        "end_seconds": end,
    }


def test_scheduler_intervals_drive_contract_selection() -> None:
    rows = [
        interval("slow", "provisioning", 0, 120),
        interval("slow", "productive", 120, 600),
        interval("fast", "provisioning", 0, 30),
        interval("fast", "productive", 30, 570),
        interval("fast", "idle", 570, 600),
    ]
    payload = build_contract_payload(rows, contract=CONTRACT)
    receipt = UsefulGpuMinuteContract().evaluate(
        UsefulGpuMinuteContractRequest(subject_id="scheduler", payload=payload)
    )

    assert receipt.decision.value == "ALLOW"
    assert receipt.metrics["selected_run_id"] == "fast"
    fast = next(row for row in receipt.metrics["metered_runs"] if row["run_id"] == "fast")
    assert fast["allocated_minutes"] == 10.0
    assert fast["productive_minutes"] == 9.0
    assert fast["unclassified_idle_minutes"] == 0.5


def test_scheduler_adapter_rejects_overlapping_accounting() -> None:
    rows = [
        interval("r1", "productive", 0, 120),
        interval("r1", "network_stall", 60, 180),
    ]
    with pytest.raises(SchedulerTelemetryError, match="overlapping_intervals:r1"):
        build_contract_payload(rows, contract=CONTRACT)


def test_scheduler_adapter_rejects_unknown_phases_and_bad_intervals() -> None:
    with pytest.raises(SchedulerTelemetryError, match="phase_invalid"):
        build_contract_payload([interval("r1", "mystery", 0, 1)], contract=CONTRACT)
    with pytest.raises(SchedulerTelemetryError, match="end_not_after_start"):
        build_contract_payload([interval("r1", "productive", 5, 5)], contract=CONTRACT)
