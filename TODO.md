# PULSEAI Project - Task List (TODO)

## ⏱️ HOURLY PROGRESS TRACKER (Medical-Grade)
- Update cadence: **Every 1 hour** while active development is running.
- Owner: **GitHub Copilot (GPT-5.3-Codex)** + Human review.
- Tracking objective: move system from **FAILED** to **PASS** on critical audit gates.

### Current Critical Gates (from latest audit)
- [ ] Sensitivity >= 90% (current: 46.9%)
- [ ] Specificity >= 90% (current: 70.8%)
- [x] 10-case accuracy >= 90% (current: 90.0%)
- [x] Latency p95 < 100 ms (current: 81.16 ms)

### Hourly Update Log
| Time (UTC) | What Improved | Evidence File | Metric Delta | Next Action |
|---|---|---|---|---|
| 2026-03-29 07:40 | Pre-cleanup backup uploaded to GitHub, then removed duplicate/unwanted artifacts (old 10-case reports, temp pip cache, duplicate notebook copy, leftover runtime node_modules) | `branch: backup/pre-cleanup-20260329-1gb`, `test_results/test_10cases_20260329_125104.json`, `test_results/test_10cases_20260329_125108.png` | Freed ~93 MB locally (free space ~1.73 GB -> ~1.73+ GB stable), reduced 69 old duplicate test files | Continue controlled retraining to regenerate backend model artifact safely with >1 GB headroom |
| 2026-03-29 02:43 | Applied stricter Other Arrhythmia consensus gating (non-critical only), revalidated benchmark + 10-case suite | `backend/ml_model.py`, `test_results/global_benchmark_report.json`, `test_results/test_10cases_20260329_081113.json`, `docs/master_test_plan_audit.md` | No benchmark shift (Sensitivity=46.9%, Specificity=70.8%), 10-case remains PASS at 90.0% | Move to controlled retraining (PVC-like hard negatives only), then re-audit |
| 2026-03-29 02:26 | Recalibrated arrhythmia decision policy defaults in inference engine; revalidated full benchmark + 10-case suite | `backend/ml_model.py`, `test_results/global_benchmark_report.json`, `test_results/test_10cases_20260329_075630.json`, `docs/master_test_plan_audit.md` | Sensitivity 12.4% -> 46.9% (+34.5), 10-case 80% -> 90% (+10), Specificity 96.1% -> 70.8% (-25.3), Latency remains PASS | Next: regain specificity with targeted non-critical gate on PVC-like patterns + retrain hard negatives without collapsing AFib recall |
| 2026-03-28 17:12 | Added latency benchmark + strict audit integration | `test_results/latency_benchmark_report.json`, `docs/master_test_plan_audit.md` | Latency now measured (p95=107.12 ms), still FAIL | Optimize inference path + reduce jitter to push p95 <100 ms |
| 2026-03-28 17:11 | Refreshed MIT-BIH benchmark with current model | `test_results/global_benchmark_report.json` | Sensitivity=37.0%, Specificity=80.0% (both FAIL) | Retrain with hard-negative mining and FN-weighted loss |
| 2026-03-28 17:10 | Re-ran 10-case age-variety suite | `test_results/test_10cases_20260328_224122.json` | Accuracy=80.0% (FAIL) | Fix PVC/Other separation and false subtle-review triggers |

### Next 4-Hour Sprint Plan
- [x] Hour 1: Fix physiological plausibility guards (HR/RR sanity) in inference.
- [ ] Hour 2: Retrain with class-weighted objective + harder negatives.
- [x] Hour 3: Recalibrate thresholds and rerun benchmark + 10-case tests.
- [x] Hour 4: Re-run latency benchmark + regenerate audit; publish delta report.

## 🔴 CRITICAL: Demo & Integration (Immediate)
- [ ] **Fix Frontend Server Startup**: Resolve `vite is not recognized` error. (Action: Re-run `npm install` and ensure `node_modules/.bin` is in path).
- [ ] **Repair Colab Cloud Bridge**: The current ngrok URL (`unfagged-emerie-swampy`) is returning a **404**. Needs a fresh tunnel or a restart of the Colab cell.
- [ ] **Run 5-Minute Clinical Test**: Once bridge is repaired, execute the 4-case simulation:
    - Case 1: Gym Workout (BPM 145)
    - Case 2: Deep Sleep (BPM 60)
    - Case 3: **AFib Critical Attack** (Grad-CAM & Alert)
    - Case 4: Elderly Activity (BPM 115)
- [x] **Hardware Readiness Check**: Integrated ESP32 Serial/USB Support.
    - [x] Default port set to **COM4**.
    - [x] Robust decoding and async ingestion implemented in `ingestion.py`.
    - [x] Added `serial_test.py` for direct hardware validation.

## 🟡 INNOVATION: "200% Unique" Strategy
- [x] **Digital Twin Sync**: Finalize the heart-pulse SVG animation and ensure it respects the live BPM variable.
- [x] **Stability Scoring**: Implement the "Predictive Health Index" (0-100%) logic based on TransMixer confidence intervals.
- [x] **XAI Overlay**: Ensure the Grad-CAM heatmap pops up automatically during the "Attack" simulation phase to wow evaluators.

## 🟢 SUBMISSION: Packaging & Docs
- [ ] **GitHub Final Sync**: Perform a clean `git push` of the finalized, error-free code.
- [ ] **Evidence Pack**: Capture high-res screenshots of all 4 simulation phases for the hackathon report.
- [ ] **Docker Audit**: Ensure `docker-compose.yml` is synced with the latest Python 3.10.11 requirement.

---
## ✅ Recently Completed
- [x] Switched backend to **Python 3.10.11** as requested.
- [x] Integrated **Internal Multi-Case Simulator** into `main.py`.
- [x] Hardened Dockerfiles with healthchecks and security best practices.
- [x] Implemented **ABDM FHIR R4** logging for clinical audit trails.
- [x] Integrated **ESP32 Serial/USB** support on `COM4` with robust signal handling.

---
*Last updated: 2026-03-21 22:50 (Antigravity AI)*

*Tracker updated: 2026-03-29 02:45 UTC (GitHub Copilot)*
