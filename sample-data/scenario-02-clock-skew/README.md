# Scenario 02: Clock Skew & Overlapping Uncertainty

## Overview
Demonstrates TraceLens clock-skew estimation and temporal uncertainty:
1. `auth.log` records events from `host01` with an accurate UTC clock.
2. `nginx_access.log` records events from a reverse proxy whose clock is running +180 seconds fast.
3. Multiple events occur within 1 second of each other on the same host (e.g., lines 1 and 2 of `auth.log` at `10:45:00` and `10:45:01`). With a configured clock uncertainty margin of $\Delta t = 1.0\text{s}$, their uncertainty intervals $[10:44:59, 10:45:01]$ and $[10:45:00, 10:45:02]$ overlap.

## Expected Behavior
- TraceLens identifies the overlapping intervals and displays **ORDER UNCERTAIN**.
- The Clock-Skew estimation module correlates `devops` activity between both sources and estimates an offset of $\approx +180.0\text{s}$.
- The system explains that this is an estimate and does not mutate historical timestamps without authorization.
