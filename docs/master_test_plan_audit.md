# Master Test Plan Audit

Generated UTC: 2026-03-29T13:38:59.604990+00:00

## Pass/Fail Matrix

| ID | Criterion | Target | Measured | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| C1 | Arrhythmia Sensitivity | >= 90% | 39.2% | FAIL | test_results\global_benchmark_report.json |
| C2 | Arrhythmia Specificity | >= 90% | 70.9% | FAIL | test_results\global_benchmark_report.json |
| C3 | 10-Case Real-Time Accuracy | >= 90% | 100.0% | PASS | test_results\test_10cases_20260329_172721.json |
| C4 | Sampling Frequency | >= 500 Hz | 500 Hz | PASS | backend/signal_processing.py |
| C5 | Classification Latency | < 100 ms | p95=81.16 ms | PASS | test_results\latency_benchmark_report.json |

## Remediation

- C1 Arrhythmia Sensitivity: Retrain on harder positives and tune operating threshold with false-negative penalty.
- C2 Arrhythmia Specificity: Add stronger non-arrhythmia hard negatives and post-filter to suppress noise-induced positives.

## Notes

- Thresholds are sourced from the Master Test Plan PDF.
- Missing metrics are marked N/A until instrumentation is added.