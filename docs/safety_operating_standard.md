# PulseAI Safety Operating Standard

## Purpose
Define non-negotiable runtime safety controls for medical ECG decision support.

## Core Principles
- Human safety over automation speed.
- Decision support, not autonomous diagnosis by default.
- Fail safe on low-quality signal.
- Production startup must fail on insecure configuration.

## Mandatory Runtime Controls
- PULSEAI_DEPLOYMENT_ENV=production
- PULSEAI_STRICT_SAFETY=1
- PULSEAI_API_KEY must be set
- CORS_ALLOW_ORIGINS must not include wildcard
- COLAB_INFERENCE_URL must use HTTPS if configured
- PULSEAI_ALLOW_AUTONOMOUS_DIAGNOSIS=0 by default
- PULSEAI_MIN_SQI_FOR_DIAGNOSIS must be >= 0.40 in strict mode

## Prediction Safety Behavior
- Every prediction includes advisory and clinician-review flags.
- If SQI is below threshold, output is forced to:
  - classification: Poor Signal Quality - Hold Still
  - hold_still_required: true
  - is_arrhythmia: false
- High-risk findings remain visible but are treated as clinician-reviewed outputs.

## Logging and Privacy
- PHI logging is disabled by default.
- Enable PHI logs only for controlled debugging with explicit approval.

## Deployment Gate Checklist
- Secrets are not present in repository.
- API key protection enabled.
- Endpoint authentication verified.
- SQI gating enabled and tested.
- Benchmark thresholds validated on real-world datasets.
- Clinical review workflow enabled in frontend and backend.
