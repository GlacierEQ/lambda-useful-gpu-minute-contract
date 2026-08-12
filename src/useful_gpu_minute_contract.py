"""Useful-GPU-Minute Contract.

Meters allocated accelerator time into productive and non-productive phases,
then selects the run that maximizes useful compute while enforcing time-to-use,
failure-fraction, and useful-ratio service objectives.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _digest(obj: object) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REFUSE = "REFUSE"


@dataclass(frozen=True)
class UsefulGpuMinuteContractRequest:
    subject_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    budget: float = 1.0
    grant_id: str | None = None
    not_after: float | None = None


@dataclass(frozen=True)
class UsefulGpuMinuteContractReceipt:
    decision: Decision
    reasons: tuple[str, ...]
    digest: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reasons": list(self.reasons),
            "digest": self.digest,
            "metrics": self.metrics,
        }


class ContractError(ValueError):
    pass


class UsefulGpuMinuteContract:
    MIN_BUDGET = 0.0
    WASTE_FIELDS = (
        "provisioning_minutes",
        "storage_load_minutes",
        "network_stall_minutes",
        "failure_minutes",
        "retry_minutes",
    )

    @staticmethod
    def _number(value: Any, label: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ContractError(f"{label}_invalid")
        number = float(value)
        if not math.isfinite(number):
            raise ContractError(f"{label}_not_finite")
        if minimum is not None and number < minimum:
            raise ContractError(f"{label}_below_minimum")
        if maximum is not None and number > maximum:
            raise ContractError(f"{label}_above_maximum")
        return number

    @classmethod
    def _contract(cls, raw: Any) -> dict[str, float]:
        if not isinstance(raw, dict):
            raise ContractError("contract_missing")
        return {
            "min_useful_ratio": cls._number(raw.get("min_useful_ratio"), "min_useful_ratio", minimum=0, maximum=1),
            "max_time_to_useful_minutes": cls._number(raw.get("max_time_to_useful_minutes"), "max_time_to_useful_minutes", minimum=0),
            "max_failure_fraction": cls._number(raw.get("max_failure_fraction"), "max_failure_fraction", minimum=0, maximum=1),
        }

    @classmethod
    def _run(cls, raw: Any, index: int) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ContractError(f"run_{index}_not_object")
        run_id = str(raw.get("run_id", "")).strip()
        if not run_id:
            raise ContractError(f"run_{index}_id_missing")
        allocated = cls._number(raw.get("allocated_minutes"), f"run_{index}_allocated_minutes", minimum=0.001)
        productive = cls._number(raw.get("productive_minutes"), f"run_{index}_productive_minutes", minimum=0)
        row: dict[str, Any] = {
            "run_id": run_id,
            "allocated_minutes": allocated,
            "productive_minutes": productive,
        }
        for field_name in cls.WASTE_FIELDS:
            row[field_name] = cls._number(raw.get(field_name, 0.0), f"run_{index}_{field_name}", minimum=0)
        accounted = productive + sum(row[field_name] for field_name in cls.WASTE_FIELDS)
        if accounted > allocated + 1e-9:
            raise ContractError(f"run_{run_id}_accounting_exceeds_allocation")
        row["unclassified_idle_minutes"] = round(max(0.0, allocated - accounted), 12)
        return row

    @staticmethod
    def _meter(run: dict[str, Any]) -> dict[str, Any]:
        allocated = run["allocated_minutes"]
        productive = run["productive_minutes"]
        useful_ratio = productive / allocated
        failure_fraction = run["failure_minutes"] / allocated
        time_to_useful = (
            run["provisioning_minutes"]
            + run["storage_load_minutes"]
            + run["network_stall_minutes"]
            + run["retry_minutes"]
        )
        waste = allocated - productive
        return {
            **run,
            "useful_gpu_minutes": round(productive, 12),
            "wasted_gpu_minutes": round(waste, 12),
            "useful_ratio": round(useful_ratio, 12),
            "failure_fraction": round(failure_fraction, 12),
            "time_to_useful_minutes": round(time_to_useful, 12),
        }

    @staticmethod
    def _violations(metered: dict[str, Any], contract: dict[str, float]) -> list[str]:
        reasons: list[str] = []
        if metered["useful_ratio"] < contract["min_useful_ratio"]:
            reasons.append("useful_ratio_below_contract")
        if metered["time_to_useful_minutes"] > contract["max_time_to_useful_minutes"]:
            reasons.append("time_to_useful_exceeds_contract")
        if metered["failure_fraction"] > contract["max_failure_fraction"]:
            reasons.append("failure_fraction_exceeds_contract")
        return reasons

    def evaluate(self, req: UsefulGpuMinuteContractRequest) -> UsefulGpuMinuteContractReceipt:
        reasons: list[str] = []
        if not str(req.subject_id or "").strip():
            reasons.append("subject_id_missing")
        try:
            budget = self._number(req.budget, "budget", minimum=0)
        except ContractError as exc:
            budget = 0.0
            reasons.append(str(exc))
        if budget <= self.MIN_BUDGET:
            reasons.append("budget_non_positive")

        payload = req.payload if isinstance(req.payload, dict) else {}
        if not isinstance(req.payload, dict):
            reasons.append("payload_not_object")

        metered_runs: list[dict[str, Any]] = []
        eligible: list[dict[str, Any]] = []
        violations: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        try:
            contract = self._contract(payload.get("contract"))
            raw_runs = payload.get("runs")
            if not isinstance(raw_runs, list) or not raw_runs:
                raise ContractError("runs_missing")
            seen: set[str] = set()
            for index, raw in enumerate(raw_runs):
                run = self._run(raw, index)
                if run["run_id"] in seen:
                    raise ContractError(f"duplicate_run_id:{run['run_id']}")
                seen.add(run["run_id"])
                metered = self._meter(run)
                metered_runs.append(metered)
                failed = self._violations(metered, contract)
                if failed:
                    violations.append({"run_id": run["run_id"], "violations": failed})
                else:
                    eligible.append(metered)
            if not eligible:
                raise ContractError("no_run_satisfies_useful_gpu_contract")
            eligible.sort(
                key=lambda row: (
                    -row["useful_ratio"],
                    row["time_to_useful_minutes"],
                    row["failure_fraction"],
                    row["run_id"],
                )
            )
            selected = eligible[0]
        except ContractError as exc:
            reasons.append(str(exc))

        decision = Decision.REFUSE if reasons else Decision.ALLOW
        metrics: dict[str, Any] = {
            "selected_run_id": selected.get("run_id") if selected else None,
            "selected": selected,
            "eligible_run_count": len(eligible),
            "metered_runs": metered_runs,
            "violations": violations,
        }
        body = {
            "subject_id": req.subject_id,
            "decision": decision.value,
            "reasons": reasons,
            "metrics": metrics,
        }
        return UsefulGpuMinuteContractReceipt(
            decision=decision,
            reasons=tuple(reasons or ["useful_gpu_minute_contract_satisfied"]),
            digest=_digest(body),
            metrics=metrics,
        )


Mechanism = UsefulGpuMinuteContract
