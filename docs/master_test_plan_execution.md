# Master Test Plan Execution (ESP32 ECG AI)

This execution guide operationalizes the requirements from the provided Master Test Plan PDF.

## Prioritized Checklist

1. Safety-critical rhythm handling
- Ensure severe instability patterns are never silently downgraded.
- Required checks: lead-off, low battery, sensor fault, unknown rhythm fallback.

2. Accuracy and robustness
- Evaluate sensitivity/specificity against MIT-BIH benchmark windows.
- Run noise and artifact robustness tests and track degradation.

3. Real-time performance
- Confirm sampling >= 500 Hz under full streaming load.
- Instrument and enforce inference latency target < 100 ms.

4. Regulatory-readiness evidence
- Maintain auditable logs for events, outputs, and errors.
- Keep traceable pass/fail report artifacts for each test run.

## Equipment and Profiles

Recommended test setup from the plan:
- ECG simulator or PhysioNet-driven digital feed.
- Electrode impedance/short simulation network.
- DAQ or scope for ground-truth signal capture.

Patient profiles to cover:
- Healthy adult
- Elderly with AF/PVC tendencies
- Athlete bradycardia
- Pediatric high-rate profile
- Pacemaker-style signals
- Artifact-heavy profile

## Current Project Mapping

Implemented artifacts:
- Benchmark report: test_results/global_benchmark_report.json
- Age-variety test suite: test_10cases_age_variety.py
- Automated plan audit: scripts/master_test_plan_audit.py

## Pass/Fail Criteria Enforced

Current automated gate evaluates:
- Sensitivity >= 90%
- Specificity >= 90%
- 10-case accuracy >= 90%
- Sampling rate >= 500 Hz
- Latency < 100 ms (placeholder until instrumentation is added)

Run audit:

```powershell
python scripts/master_test_plan_audit.py
```

Run latency benchmark (for <100 ms criterion):

```powershell
python scripts/latency_benchmark.py
```

Outputs:
- test_results/master_test_plan_audit.json
- docs/master_test_plan_audit.md
- test_results/latency_benchmark_report.json

## Required Next Additions

1. Latency instrumentation
- Log per-inference latency (p50, p95, max) in backend runtime.
- Add fail gate when p95 >= 100 ms.

2. Hardware-fault test harness
- Add repeatable lead-off and battery-low simulation checks.

3. Motion/noise protocol
- Add synthetic EMG and baseline-wander augmentation tests with target retention thresholds.

4. Regulatory evidence folder
- Store versioned logs and test evidence for IEC 62304 / ISO 14971 traceability.
