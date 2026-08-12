from __future__ import annotations

from useful_gpu_minute_contract import Decision, UsefulGpuMinuteContract, UsefulGpuMinuteContractRequest


CONTRACT = {
    "min_useful_ratio": 0.70,
    "max_time_to_useful_minutes": 12.0,
    "max_failure_fraction": 0.05,
}


def run(run_id: str, *, allocated: float = 100.0, productive: float = 78.0, provisioning: float = 5.0, storage: float = 3.0, network: float = 2.0, failure: float = 2.0, retry: float = 2.0) -> dict:
    return {
        "run_id": run_id,
        "allocated_minutes": allocated,
        "productive_minutes": productive,
        "provisioning_minutes": provisioning,
        "storage_load_minutes": storage,
        "network_stall_minutes": network,
        "failure_minutes": failure,
        "retry_minutes": retry,
    }


def evaluate(runs: list[dict]):
    return UsefulGpuMinuteContract().evaluate(
        UsefulGpuMinuteContractRequest(
            subject_id="cluster-a",
            budget=1.0,
            payload={"contract": CONTRACT, "runs": runs},
        )
    )


def test_selects_run_with_highest_useful_ratio() -> None:
    receipt = evaluate([
        run("baseline", productive=75.0),
        run("optimized", productive=82.0, provisioning=4.0, storage=2.0, network=1.0, failure=1.0, retry=1.0),
    ])
    assert receipt.decision is Decision.ALLOW
    assert receipt.metrics["selected_run_id"] == "optimized"
    assert receipt.metrics["selected"]["useful_ratio"] == 0.82
    assert len(receipt.digest) == 64


def test_time_to_useful_includes_provisioning_storage_network_and_retries() -> None:
    receipt = evaluate([run("measured", productive=76.0, provisioning=4.0, storage=3.0, network=2.0, retry=2.0)])
    assert receipt.decision is Decision.ALLOW
    assert receipt.metrics["selected"]["time_to_useful_minutes"] == 11.0


def test_refuses_low_useful_ratio() -> None:
    receipt = evaluate([run("wasteful", productive=60.0, provisioning=10.0, storage=5.0, network=5.0, failure=5.0, retry=5.0)])
    assert receipt.decision is Decision.REFUSE
    assert "no_run_satisfies_useful_gpu_contract" in receipt.reasons
    assert "useful_ratio_below_contract" in receipt.metrics["violations"][0]["violations"]


def test_refuses_excessive_failure_fraction() -> None:
    receipt = evaluate([run("flaky", productive=75.0, failure=8.0)])
    assert receipt.decision is Decision.REFUSE
    assert "failure_fraction_exceeds_contract" in receipt.metrics["violations"][0]["violations"]


def test_refuses_slow_time_to_useful_even_with_good_productive_ratio() -> None:
    receipt = evaluate([run("slow-start", productive=75.0, provisioning=9.0, storage=4.0, network=1.0, failure=1.0, retry=1.0)])
    assert receipt.decision is Decision.REFUSE
    assert "time_to_useful_exceeds_contract" in receipt.metrics["violations"][0]["violations"]


def test_accounting_cannot_exceed_allocated_minutes() -> None:
    receipt = evaluate([run("impossible", allocated=100.0, productive=90.0, provisioning=10.0, storage=5.0)])
    assert receipt.decision is Decision.REFUSE
    assert "run_impossible_accounting_exceeds_allocation" in receipt.reasons


def test_duplicate_run_ids_fail_closed() -> None:
    receipt = evaluate([run("same"), run("same")])
    assert receipt.decision is Decision.REFUSE
    assert "duplicate_run_id:same" in receipt.reasons


def test_unclassified_idle_time_is_visible_not_silently_counted_useful() -> None:
    receipt = evaluate([run("idle", productive=75.0, provisioning=2.0, storage=2.0, network=1.0, failure=1.0, retry=1.0)])
    assert receipt.decision is Decision.ALLOW
    assert receipt.metrics["selected"]["unclassified_idle_minutes"] == 18.0
    assert receipt.metrics["selected"]["wasted_gpu_minutes"] == 25.0
