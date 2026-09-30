# AGENTS.md — lambda-useful-gpu-minute-contract

**Company:** GlacierEQ
**Domain:** Autonomous Systems Engineering

## Quick Rules
- **Test command:** `PYTHONPATH=src pytest tests/ -v`
- **Lint:** `ruff check src/ tests/`
- **No drive-by edits** — load the skill first.

## Architecture
- `src/lambda_useful_gpu_minute_contract/core.py` — Domain logic (Autonomous Systems Engineering)
- `tests/` — Verified test suite
- `.github/workflows/ci.yml` — Enforced CI pipeline
