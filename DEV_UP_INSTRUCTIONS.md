# DEV_UP_INSTRUCTIONS — implementation record

**Repository:** `GlacierEQ/lambda-useful-gpu-minute-contract`  
**Independent company lens:** Lambda  
**Innovation:** Useful-GPU-Minute Contract

## Mission

Make GPU service quality measurable in terms of productive model work rather than rented accelerator time alone.

## Implemented

The generic scaffold has been replaced by deterministic useful-compute accounting and run selection.

`src/useful_gpu_minute_contract.py` now:

- meters productive, provisioning, storage, network-stall, failure, retry, and unclassified idle minutes;
- rejects accounting totals that exceed the allocated GPU interval;
- computes useful ratio, failure fraction, wasted GPU minutes, and time-to-useful-compute;
- enforces minimum useful ratio, maximum time-to-useful, and maximum failure fraction;
- rejects duplicate run identities and malformed/non-finite measurements;
- selects the strongest contract-compliant run deterministically;
- emits structured SHA-256 receipts containing complete accounting and violations.

`src/useful_gpu_minute_cli.py` and `scripts/operate.py` execute the mechanism directly. The project is packaged as a wheel with the `useful-gpu-minute-contract` console command.

## Verification contract

Behavioral tests cover best-run selection, time-to-use accounting, low useful-ratio refusal, excessive failure refusal, slow-start refusal, impossible accounting, duplicate identities, and visibility of idle time. Existing adversarial coverage remains active.

CI must pass native tests, cold-start operation, wheel build/install, and installed CLI execution before Helix may mint source-bound promotion evidence.

## Truth boundary

No Lambda affiliation, proprietary access, production deployment, customer impact, or company partnership is claimed. Current inputs are explicit run observations; a future scheduler/telemetry adapter can derive them automatically from a permitted test environment.
