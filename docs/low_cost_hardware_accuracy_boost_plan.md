# Low-Cost Hardware Additions to Boost PulseAI Accuracy

## Objective
Increase ECG classification accuracy and safety by reducing motion artifacts, improving signal integrity, and enabling richer context with low-cost components.

## Recommended Additions (Low Cost)

1. MPU6050 (6-axis IMU)
- Approx cost: USD 1.5 to 3
- Why it helps: Detects body motion and electrode displacement. The backend can down-weight or gate uncertain predictions during high motion.
- Expected score impact:
  - Accuracy: +0.4 to +0.8
  - Safety: +0.5 to +0.9
  - Reliability: +0.3 to +0.6

2. BMI160 (alternative IMU, better noise behavior)
- Approx cost: USD 2.5 to 5
- Why it helps: Lower-noise motion signal than MPU6050 in some wearables.
- Expected score impact similar to MPU6050, slightly better on motion-heavy use.

3. ADS1292R analog front-end (2-channel ECG AFE)
- Approx cost: USD 8 to 18 (module dependent)
- Why it helps: Better ECG dynamic range, integrated right-leg drive support, clinical-grade oriented AFE path.
- Expected score impact:
  - Accuracy: +0.8 to +1.4
  - Safety: +0.6 to +1.2
  - Real-world implementation: +0.5 to +1.0

4. MAX30003 ECG biopotential IC
- Approx cost: USD 12 to 22
- Why it helps: High-quality ECG front-end with heart-rate related features and low-power wearable suitability.

5. Better electrode set + lead wire quality
- Approx cost: USD 0.2 to 1 per test session (consumables)
- Why it helps: Large effect on contact impedance, lead-off events, and false alarms.

6. Medical isolation module and battery-only default mode
- Approx cost: USD 8 to 25
- Why it helps: Required direction for IEC 60601-1 leakage safety compliance.

## Best Cost/Benefit Sequence

1. Add MPU6050 immediately and motion-gate predictions in backend.
2. Upgrade electrodes and contact quality SOP.
3. Move from AD8232 to ADS1292R for next hardware revision.
4. Add isolation and leakage-current test path before any clinical pilot.

## Firmware/Data Changes Needed

1. Include IMU packet fields in telemetry payload:
- accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, motion_index

2. Add sequence number and timestamp in every ECG packet:
- seq_id, ts_ms, lead_status

3. Add battery level and power-mode state:
- batt_mv, charging, source

4. Add reconnect counters:
- reconnect_count, packet_drop_estimate

## Why this improves model performance

- Motion context reduces false positives from artifact-heavy windows.
- Better analog front-end improves SNR and morphology retention.
- Better contact quality reduces low-amplitude and lead-off confusion.
- Sequence IDs and packet diagnostics enable robust missing-data handling and safer uncertainty outputs.

## Minimum hardware target for >=8/10 category plan

- ESP32-S3
- ADS1292R or MAX30003 AFE
- MPU6050/BMI160 IMU
- Battery-only clinical mode + isolation path
- TLS transport + local failover inference

This combination is the most practical low-cost route toward broad score lift while remaining buildable by small teams.
