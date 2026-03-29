# PulseAI Clinical Grade Execution Plan

## Objective
Convert PulseAI from prototype state into a deployment-ready clinical platform with measurable gates.

## Phase 0: Immediate Safety Lockdown (Week 0-1)
- Rotate exposed Firebase service-account keys and remove credential files from repository history.
- Enforce authentication on all sensitive backend endpoints.
- Disable hardcoded secret paths and require environment-provided secret configuration.
- Set deployment gate: block release if any secret-scan finding is critical.

## Phase 1: Signal Integrity and Ingestion Hardening (Week 1-3)
- Replace ASCII serial stream with binary framed protocol using COBS plus CRC-16.
- Add packet-loss, checksum-failure, and acquisition-quality telemetry.
- Fail safe on dirty packets and show operator guidance instead of inferring from corrupted data.
- Add integration tests for noisy link and packet corruption scenarios.

## Phase 2: Clinical Reliability and Model Governance (Week 2-6)
- Add SQI gating policy that suppresses hard diagnosis on poor signal quality.
- Calibrate decision thresholds with constrained tuning: minimum specificity, recall, and precision floors.
- Expand evaluation to cross-dataset validation (MIT-BIH, PTB-XL subsets, noise stress scenarios).
- Introduce model card, drift monitoring, and rollback policy.

## Phase 3: Real-Time UX Determinism (Week 2-4)
- Use frontend jitter buffer and deterministic render intervals.
- Add latency and jitter metrics in telemetry dashboard.
- Gate release on frame-stability and rendering smoothness under degraded networks.

## Phase 4: Interoperability and Compliance Artifacts (Week 4-10)
- Complete HL7-FHIR R4 profile conformance tests.
- Add DICOM waveform export path for hospital integration.
- Build IEC 62304 software lifecycle evidence package.
- Build risk management matrix linked to code and test evidence.

## Phase 5: Explainability and Clinical Review (Week 6-12)
- Add segment-level explainability overlays with confidence attribution.
- Log model rationale artifacts for post-hoc audit.
- Validate explanation consistency with clinician feedback loop.

## Non-Negotiable Release Gates
- Security: zero critical secrets, authenticated sensitive APIs, encryption at rest and in transit.
- Reliability: specificity and recall above product thresholds on real-world datasets.
- Safety: no diagnosis on poor-quality signal without explicit quality warning.
- Interop: validated FHIR payloads and verified downstream compatibility.
- Traceability: each release linked to test evidence, risk controls, and model versioning.

## Current Status Delta Implemented
- Sensitive backend endpoints now support API-key enforcement via X-API-Key header when PULSEAI_API_KEY is set.
- Hardcoded Firebase key-path default removed; runtime now requires explicit FIREBASE_KEY_PATH configuration.
- Frontend 200ms ECG jitter buffer added for smoother waveform rendering under websocket/poll burstiness.

## Immediate Next Actions
1. Move Firebase credentials out of repository and rotate keys.
2. Add COBS plus CRC packet decoder in ingestion path.
3. Add SQI metric emission and hard no-diagnosis gate below SQI threshold.
4. Complete constrained tuner run and lock a deployment-safe policy profile.
