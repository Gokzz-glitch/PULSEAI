# PulseAI 1200-Combination Search: Winner and Failure Analysis

## What was executed
- Design-space search executed over 1200 sampled combinations from a 1,166,400 full combination space.
- Output artifact: test_results/combination_search_1200_20260329_191728.json
- Passing threshold applied: all 10 categories must be >= 8.0.

## Winning combination

- Hardware: ADS1292R_ESP32
- Leads: pseudo12
- IMU: mpu6050
- Connectivity: ble_wifi_hybrid
- Dataset strategy: mitbih_ptbxl_incart_challenge2020
- Backbone: cnn_transformer_hybrid
- Pretrained: challenge2020_pretrain
- Filter profile: artifact_aware_imu_gated
- Policy profile: recall_guard
- Deployment: hybrid_failover

## Winner scores
- UI: 8.20
- Ease of Use: 8.54
- Accuracy: 8.87
- Novelty: 8.84
- Innovation: 8.73
- Invention: 8.54
- Latency: 8.85
- Real-World: 8.70
- Safety: 8.49
- Reliability: 8.64
- Composite: 8.68

## Why this combination won
1. Better analog front-end (ADS1292R) lifted signal quality and safety margins.
2. Motion context (MPU6050) reduced artifact-driven false positives.
3. Multi-dataset transfer + Challenge pretraining improved generalization robustness.
4. Hybrid deployment/failover improved latency and reliability simultaneously.
5. Recall-guard policy protected critical-event sensitivity while still maintaining acceptable specificity.

## Why many combinations failed
- Accuracy below 8: 691 combinations
- Safety below 8: 825 combinations
- Real-world below 8: 674 combinations
- Latency below 8: 767 combinations
- Other dimensions below 8: 1126 combinations

Primary failure patterns:
1. Single-lead + weaker dataset strategy combinations underfit edge cases.
2. Plain MQTT transport lowered safety/reliability due to security and resilience penalties.
3. No-IMU artifact handling increased motion-related misclassification risk.
4. Cloud-only deployment reduced latency/reliability under unstable connectivity.
5. No pretraining or weak pretraining reduced cross-domain generalization.

## Important note
This 1200-combination search is a systems-level optimization run for architecture selection and planning. It is not a substitute for prospective clinical validation, IEC/FDA-grade bench evidence, or board-certified cardiologist adjudication.
