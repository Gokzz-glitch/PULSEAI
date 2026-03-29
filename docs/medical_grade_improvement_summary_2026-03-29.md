# PulseAI Medical-Grade Improvement Summary

Generated UTC: 2026-03-29T02:30:00Z

## Executive Outcome

This remediation cycle improved sensitivity and restored 10-case pass status, but the system still fails medical-grade gate criteria due to low specificity and sub-threshold sensitivity.

- Overall status: FAIL (medical-grade gate not met)
- Net gain: clinical scenario robustness improved (10-case 90%)
- Remaining blocker: sensitivity/specificity are not simultaneously acceptable

## What Was Changed

1. Inference policy recalibration in backend/ml_model.py
- Reduced default non-critical arrhythmia confidence gate from 0.90 to 0.62
- Relaxed max normal-probability veto from 0.30 to 0.75
- Disabled strict good-quality requirement for non-critical classes by default
- Enabled practical ML override threshold by setting strong ML confidence default to 0.78

2. Full validation rerun
- Global benchmark rerun on 48 MIT-BIH records
- 10-case age-variety clinical suite rerun
- Master test plan audit regenerated

## Before vs After (Latest Cycle)

Baseline before policy recalibration:
- Sensitivity: 12.4%
- Specificity: 96.1%
- 10-case accuracy: 80.0%
- Latency p95: 81.16 ms

Latest after policy recalibration:
- Sensitivity: 46.9% (+34.5)
- Specificity: 70.8% (-25.3)
- 10-case accuracy: 90.0% (+10.0)
- Latency p95: 81.16 ms (maintained PASS)

## Clinical Interpretation

- Positive: The system now catches substantially more arrhythmia-positive windows and passes scenario-level 10-case validation.
- Negative: False-positive burden is too high for safe clinical deployment, and sensitivity remains far below 90%.
- Implication: Current model/policy pair is in a trade-off regime where threshold-only tuning is insufficient for medical-grade pass.

## Immediate Next Sequence (Recommended)

1. Specificity recovery without collapsing AFib recall
- Add targeted non-critical gating for low-risk "Other Arrhythmia" only
- Preserve AFib and critical rhythm detection path

2. Controlled retraining update (single variable change)
- Introduce hard negatives only for PVC-like normals
- Avoid class weighting and global threshold collapse strategies

3. Revalidate and decide go/no-go
- Rerun global benchmark + 10-case + latency + audit
- If sensitivity < 70% or specificity < 85%, freeze as research prototype and plan architecture/data upgrade

## Additional Iteration (02:43 UTC)

A second pass was executed with stronger non-critical consensus gating focused on "Other Arrhythmia" calls to recover specificity while preserving AFib behavior.

Outcome:
- Global benchmark remained unchanged at Sensitivity 46.9% and Specificity 70.8%
- 10-case suite stayed at 90.0% pass
- Interpretation: post-processing policy alone is no longer the dominant bottleneck; model-level discrimination needs retraining improvements

## Current Verdict

The system is improved and more clinically useful than baseline, but it is still not medical-grade compliant under the current gate definitions.
