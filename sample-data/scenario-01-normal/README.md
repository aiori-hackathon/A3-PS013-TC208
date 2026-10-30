# Scenario 01: Normal Operations & Baseline Authentication

## Overview
This synthetic scenario simulates legitimate operational telemetry alongside non-complex external probing:
1. `192.0.2.10` executes web reconnaissance against `/robots.txt` and `/login`, followed by 3 invalid SSH password attempts.
2. `192.0.2.20` represents an authorized internal workstation used by user `analyst`, who logs in via SSH public key at `10:30:08 UTC` and accesses the management web dashboard at the same time.

## Evidence Files
- `auth.log`: Linux authentication events recorded on `host01`.
- `nginx_access.log`: Combined Nginx access log from the reverse proxy.

## Expected Evaluation Results
- **Parsing ledger reconciliation**: 100% (all records accounted for).
- **Source traceability**: 100% of timeline events trace back to source line and evidence ID.
- **Timestamp normalization**: Normalized to UTC with configured 1.0s uncertainty margin.
