from __future__ import annotations

import argparse
import json
from pathlib import Path

from useful_gpu_minute_contract import Decision, UsefulGpuMinuteContract, UsefulGpuMinuteContractRequest


def default_payload() -> dict:
    return {
        "contract": {"min_useful_ratio": 0.70, "max_time_to_useful_minutes": 12.0, "max_failure_fraction": 0.05},
        "runs": [
            {
                "run_id": "optimized",
                "allocated_minutes": 100.0,
                "productive_minutes": 82.0,
                "provisioning_minutes": 4.0,
                "storage_load_minutes": 2.0,
                "network_stall_minutes": 1.0,
                "failure_minutes": 1.0,
                "retry_minutes": 1.0,
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Meter and select useful GPU minute runs")
    parser.add_argument("--input", type=Path, help="JSON payload; defaults to built-in demo")
    parser.add_argument("--subject", default="cluster-demo")
    parser.add_argument("--budget", type=float, default=1.0)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text()) if args.input else default_payload()
    receipt = UsefulGpuMinuteContract().evaluate(UsefulGpuMinuteContractRequest(args.subject, payload, args.budget))
    print(json.dumps(receipt.as_dict(), sort_keys=True, indent=2))
    return 0 if receipt.decision is Decision.ALLOW else 2


if __name__ == "__main__":
    raise SystemExit(main())
