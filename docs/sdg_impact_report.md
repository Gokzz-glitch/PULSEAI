# PulseAI SDG Impact Report

Generated at: 2026-03-28T13:32:14.121842+00:00

Overall SDG Alignment Score: 66.2/100

## SDG Coverage

### SDG-3 - Good Health and Well-Being
- Status: in-progress
- Score: 65/100
- Rationale: Core objective is safer arrhythmia triage and early risk detection.
- Evidence: test_results\global_benchmark_report.json, docs\safety_operating_standard.md
- Gap: Specificity remains below clinical-grade threshold.
- Gap: Need prospective validation on diverse real-world cohorts.

### SDG-9 - Industry, Innovation and Infrastructure
- Status: strong
- Score: 72/100
- Rationale: Digital health infrastructure using streaming, edge inference, and interoperable outputs.
- Evidence: docs\clinical_grade_execution_plan.md, test_results\research_intel_report.json
- Gap: Need full DICOM waveform export implementation for hospital systems.

### SDG-10 - Reduced Inequalities
- Status: in-progress
- Score: 55/100
- Rationale: Potentially expands screening access via low-cost sensing pathways.
- Evidence: docs\clinical_grade_execution_plan.md
- Gap: Need explicit bias/fairness audits across age/sex/comorbidity cohorts.

### SDG-12 - Responsible Consumption and Production
- Status: in-progress
- Score: 68/100
- Rationale: Safety gates and strict deployment checks reduce unsafe releases.
- Evidence: docs\safety_operating_standard.md, test_results\policy_tuning_report.json
- Gap: Need mandatory CI release blocking on safety and benchmark thresholds.

### SDG-16 - Peace, Justice and Strong Institutions
- Status: in-progress
- Score: 62/100
- Rationale: Medical trust requires privacy, security, and accountable decision support.
- Evidence: docs\safety_operating_standard.md, docs\clinical_grade_execution_plan.md
- Gap: Need formal audit logging and immutable access trails.
- Gap: Need external compliance assessment process.

### SDG-17 - Partnerships for the Goals
- Status: strong
- Score: 75/100
- Rationale: Open datasets and research integration accelerate responsible clinical innovation.
- Evidence: test_results\research_intel_report.json
- Gap: Need active clinical/hospital partner validation programs.

## Priority Actions

- Raise specificity to clinically acceptable threshold before deployment claims.
- Add fairness and subgroup performance reporting into benchmark pipeline.
- Add CI gate to block release when safety benchmark floors are unmet.
- Establish pilot clinical partnerships for prospective validation.
