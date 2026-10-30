# Scenario 03: Changed File Integrity Mutation

## Overview
Demonstrates SHA-256 integrity baseline verification and downstream Mutation Radar impact propagation:
1. Both `auth.log` and `nginx_access.log` are collected into the Evidence Vault and have baseline SHA-256 digests computed and stored.
2. An investigation is created with a dependent finding linked to `auth.log` events.
3. A controlled modification is simulated on the stored evidence file (e.g., appending an unauthorized line).
4. Running **Verify Integrity** computes a new hash that differs from the recorded baseline, flagging the file as `MISMATCH`.
5. **Mutation Radar** immediately maps the impact:
   - Affected raw lines.
   - Affected timeline events.
   - Automatically flags dependent findings as `REQUIRES REVIEW` with a clear explanation without overwriting the investigator's conclusions.
