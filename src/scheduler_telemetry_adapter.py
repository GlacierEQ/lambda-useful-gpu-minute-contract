"""Derive Useful-GPU-Minute inputs from scheduler timeline telemetry."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable


class SchedulerTelemetryError(ValueError):
    pass


PHASE_TO_FIELD = {
    "productive": "productive_minutes",
    "provisioning": "provisioning_minutes",
    "storage_load": "storage_load_minutes",
    "network_stall": "network_stall_minutes",
    "failure": "failure_minutes",
    "retry": "retry_minutes",
    "idle": None,
}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchedulerTelemetryError(f"{label}_invalid")
    number = float(value)
    if not math.isfinite(number):
        raise SchedulerTelemetryError(f"{label}_not_finite")
    return number


def build_contract_payload(
    intervals: Iterable[dict[str, Any]],
    *,
    contract: dict[str, float],
) -> dict[str, Any]:
    """Convert non-overlapping scheduler intervals into metered run inputs.

    Each interval supplies ``run_id``, ``phase``, ``start_seconds`` and
    ``end_seconds`` on a per-run monotonic timeline. Explicit idle contributes to
    allocated time but remains unclassified by the core contract, preserving its
    independent accounting check.
    """
    grouped: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    for index, raw in enumerate(intervals):
        if not isinstance(raw, dict):
            raise SchedulerTelemetryError(f"interval_{index}_not_object")
        run_id = str(raw.get("run_id", "")).strip()
        phase = str(raw.get("phase", "")).strip().lower()
        if not run_id:
            raise SchedulerTelemetryError(f"interval_{index}_run_id_missing")
        if phase not in PHASE_TO_FIELD:
            raise SchedulerTelemetryError(f"interval_{index}_phase_invalid:{phase}")
        start = _number(raw.get("start_seconds"), f"interval_{index}_start_seconds")
        end = _number(raw.get("end_seconds"), f"interval_{index}_end_seconds")
        if start < 0:
            raise SchedulerTelemetryError(f"interval_{index}_start_seconds_below_minimum")
        if end <= start:
            raise SchedulerTelemetryError(f"interval_{index}_end_not_after_start")
        grouped[run_id].append((start, end, phase))

    if not grouped:
        raise SchedulerTelemetryError("intervals_missing")

    runs: list[dict[str, Any]] = []
    for run_id in sorted(grouped):
        rows = sorted(grouped[run_id], key=lambda row: (row[0], row[1], row[2]))
        previous_end: float | None = None
        totals = {field: 0.0 for field in PHASE_TO_FIELD.values() if field is not None}
        allocated_seconds = 0.0
        explicit_idle_seconds = 0.0
        for start, end, phase in rows:
            if previous_end is not None and start < previous_end - 1e-12:
                raise SchedulerTelemetryError(f"overlapping_intervals:{run_id}")
            previous_end = end
            duration = end - start
            allocated_seconds += duration
            field = PHASE_TO_FIELD[phase]
            if field is None:
                explicit_idle_seconds += duration
            else:
                totals[field] += duration / 60.0
        runs.append(
            {
                "run_id": run_id,
                "allocated_minutes": allocated_seconds / 60.0,
                **totals,
                "telemetry": {
                    "interval_count": len(rows),
                    "explicit_idle_minutes": explicit_idle_seconds / 60.0,
                    "timeline_start_seconds": rows[0][0],
                    "timeline_end_seconds": rows[-1][1],
                },
            }
        )

    return {
        "contract": contract,
        "runs": runs,
        "evidence": {
            "source": "scheduler_interval_telemetry",
            "run_count": len(runs),
            "interval_count": sum(len(rows) for rows in grouped.values()),
            "overlap_policy": "REFUSE",
        },
    }
