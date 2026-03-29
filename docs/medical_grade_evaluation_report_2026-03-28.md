# Medical AI Evaluation Report (Strict Medical Grade)

Date (UTC): 2026-03-28
Agent: Medical AI Evaluation Agent (strict evidence-based mode)
System under test: PulseAI ESP32 ECG AI stack

## Evidence Sources

- [test_results/global_benchmark_report.json](test_results/global_benchmark_report.json)
- [test_results/test_10cases_20260328_224122.json](test_results/test_10cases_20260328_224122.json)
- [test_results/latency_benchmark_report.json](test_results/latency_benchmark_report.json)
- [docs/master_test_plan_audit.md](docs/master_test_plan_audit.md)
- [backend/signal_processing.py](backend/signal_processing.py)
- [backend/ml_model.py](backend/ml_model.py)
- [backend/main.py](backend/main.py)

## Section 1: Hardware Layer Evaluation (ESP32 ECG)

Status: PARTIAL EVIDENCE ONLY (bench-level, not certified hardware verification)

Measured or inferable:
- Sampling rate target met in software config: 500 Hz ([backend/signal_processing.py](backend/signal_processing.py)).
- Notch/high-pass/low-pass filtering implemented in software pipeline ([backend/signal_processing.py](backend/signal_processing.py)).

Not evidenced in repository artifacts (cannot claim pass):
- IEC 60601-1 electrical safety test evidence (leakage current, isolation, input impedance).
- CMRR certified measurement >= 80 dB under controlled hardware setup.
- Galvanic isolation proof and short-circuit protection verification.
- Packet-loss quantified evidence <0.1% under interference.
- AES-256 transport evidence on device path.

Conclusion: Hardware medical-grade compliance cannot be approved with current evidence.

## Section 2: AI Model Accuracy & Clinical Performance

Observed from current benchmark artifacts:
- MIT-BIH binary metrics:
  - Accuracy: 69.79%
  - Precision: 36.46%
  - Recall (sensitivity): 37.0%
  - Specificity: 79.98%
  - Source: [test_results/global_benchmark_report.json](test_results/global_benchmark_report.json)
- 10-case suite accuracy: 80.0% (8/10)
  - Source: [test_results/test_10cases_20260328_224122.json](test_results/test_10cases_20260328_224122.json)

Critical interpretation:
- Life-threatening detection standards in your requirement (near-zero miss tolerance) are not met.
- False-negative risk remains too high for clinical deployment.
- PVC/Other class handling remains unstable in practical scenarios.

## Section 3: Real-Time Performance Benchmarking

Latency evidence:
- p50: 71.284 ms
- p95: 107.117 ms
- p99: 131.978 ms
- max: 422.57 ms
- Source: [test_results/latency_benchmark_report.json](test_results/latency_benchmark_report.json)

Interpretation:
- Local inference+preprocessing is close but misses strict <100 ms p95 target.
- Long-tail latency (max 422.57 ms) requires optimization and jitter control.

## Section 4: Real-World Feasibility Assessment

Current state: prototype-to-preclinical, not deployment-ready.

Gaps blocking real-world approval:
- No verified ICU integration pathway or interoperability evidence at clinical level.
- No quantified elderly/non-expert usability validation under field constraints.
- No demonstrated certified fallback chain for all failure modes (power/network/hardware faults).
- Cloud/offline behavior for critical events not fully validated with pass/fail traceability.

## Section 5: Safety, Accountability, and Ethics

Positive controls present:
- Advisory-only framing and clinician-review flags exist in backend logic.
- API key and safety gating exist in software.
- Audit artifacts generated for benchmark/audit scripts.

Critical deficits:
- False-negative burden too high for life-threatening class claims.
- Full immutable medico-legal evidence chain not demonstrated.
- Formal regulatory evidence package (IEC/FDA/MDR) not present.
- OOD and uncertainty handling not demonstrated to required safety threshold.

## Strict Verdict Inputs

Threshold compliance from audit:
- Sensitivity >= 90%: FAIL (37.0%)
- Specificity >= 90%: FAIL (80.0%)
- 10-case accuracy >= 90%: FAIL (80.0%)
- Sampling >= 500 Hz: PASS (500 Hz)
- Latency p95 < 100 ms: FAIL (107.12 ms)

Reference: [docs/master_test_plan_audit.md](docs/master_test_plan_audit.md)

SYSTEM: PulseAI / v2.1.0
HARDWARE: ESP32 + AD8232-class single-lead frontend (repository-claimed)
TEST DATE: 2026-03-28
TESTER: Medical AI Evaluation Agent (Strict)

SCORES:
  UI:               4/10
  Ease of Use:      4/10
  Accuracy:         3/10  ← CRITICAL
  Novelty:          4/10
  Innovation:       4/10
  Invention:        3/10
  Latency:          5/10
  Real-World:       3/10
  Safety:           2/10  ← CRITICAL
  Reliability:      4/10

COMPOSITE SCORE:    3.2/10

VERDICT: FAILED

CRITICAL FAILURES FOUND: 
- Arrhythmia sensitivity 37.0% vs required >=90%.
- Specificity 80.0% vs required >=90%.
- 10-case scenario accuracy 80.0% vs required >=90%.
- Latency p95 107.12 ms vs required <100 ms.
- No certified evidence for IEC 60601 electrical safety items (leakage current/isolation/CMRR formal test).
- No evidence for 100% detection of life-threatening rhythms (VF/VT/asystole/STEMI conditions in strict protocol).

CONDITIONS FOR APPROVAL (if conditional): N/A (hard fail)

RECOMMENDED NEXT STEPS:
1. Rebalance and retrain model with life-threatening false-negative penalty and external validation cohort.
2. Add class-specific calibration for PVC/Other and enforce uncertainty output for low-confidence regions.
3. Reduce p95 latency below 100 ms with model/runtime optimization and queue jitter control.
4. Execute formal hardware safety bench tests (IEC 60601-1 relevant checks) and attach traceable reports.
5. Run full 25-case stress matrix with reproducible evidence artifacts and clinician review sign-off.
6. Build regulatory traceability pack for IEC 62304, ISO 14971, ISO 13485, HIPAA/GDPR readiness.

EXPERT REVIEW REQUIRED: YES — Reason: Critical safety and accuracy thresholds are below medical deployment minimums.

⚠️ THIS REPORT IS NOT A REGULATORY CLEARANCE.
   Clinical validation by a board-certified cardiologist
   and formal regulatory submission required before use.
