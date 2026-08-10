# Issue contract — Useful-GPU-Minute Contract

## Problem
differentiating GPU access when raw capacity increasingly commoditizes and customers care about reliable cluster performance and time-to-useful-compute

## Desired outcome
A bounded, open, testable implementation of **Useful-GPU-Minute Contract** that demonstrates Meter and optimize time from allocation to productive model work, including provisioning, failures, network stalls, storage load, and job retries—not just rented accelerator time.

## Non-goals
- Lambda affiliation or proprietary integration
- Portfolio-wide scale/performance claims
- UI marketing site

## Acceptance
1. Mechanism module implements allow + refuse with structured receipts
2. pytest behavioral suite green
3. operate.py cold-start produces JSON receipt
4. Non-affiliation disclaimer preserved
