# Useful-GPU-Minute Contract

Independent GlacierEQ portfolio implementation aligned to **Lambda** operating themes.

> **Not affiliated.** This repository is not affiliated with, endorsed by, employed by, or deployed at Lambda. No proprietary access, production deployment, customer impact, or company partnership is claimed.

## Purpose

Measure accelerator service by **useful model work**, not by how long a GPU happened to be allocated.

The contract makes provisioning delay, storage load, network stalls, failures, retries, and unclassified idle time explicit so raw capacity cannot masquerade as reliable compute delivery.

## Implemented mechanism

`UsefulGpuMinuteContract` meters candidate runs into:

- allocated GPU minutes;
- productive/useful GPU minutes;
- provisioning minutes;
- storage-load minutes;
- network-stall minutes;
- failure minutes;
- retry minutes;
- unclassified idle minutes.

Each run is checked against a declared service contract for minimum useful ratio, maximum time-to-useful-compute, and maximum failure fraction. Accounting that exceeds the allocation is rejected. Eligible runs are ranked deterministically by useful ratio, time to useful compute, failure fraction, and stable run id.

The receipt exposes the full accounting, contract violations, selected run, and a SHA-256 decision digest.

## Run

```bash
python -m pytest -q
python scripts/operate.py
```

Build and install:

```bash
python -m pip install build
python -m build
python -m pip install dist/*.whl
useful-gpu-minute-contract
```

Evaluate your own run measurements:

```bash
useful-gpu-minute-contract --input gpu-runs.json
```

## Proof surface

- `src/useful_gpu_minute_contract.py` — accounting and contract selection engine
- `src/useful_gpu_minute_cli.py` — installable execution surface
- `tests/test_useful_gpu_minute_contract.py` — useful ratio, time-to-use, failures, accounting integrity, duplicate and idle-time behavior
- `tests/test_adversarial.py` — fail-closed adversarial coverage
- `.github/workflows/tests.yml` — tests + cold-start + wheel build/install + installed CLI
- `machine/` — existing Helix target, proof, authority, and promotion surfaces remain preserved

## Current boundary

The mechanism operates on supplied run measurements and does not claim Lambda infrastructure access or production service levels. The next depth step is a telemetry adapter for a permitted GPU scheduler/test cluster that derives these phase measurements automatically.
