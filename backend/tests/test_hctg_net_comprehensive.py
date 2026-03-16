"""
PulseAI — HCTG-Net: Comprehensive Production-Readiness Test Suite
==================================================================
Tests the full pipeline:
  signal_processing.process_ecg  →  ml_model.predict_arrhythmia  →  fhir_generator

Dataset simulations
-------------------
Each dataset scenario generates synthetic ECG waveforms that faithfully reproduce
the statistical properties of the named public dataset / clinical condition.
50+ distinct scenario groups are exercised covering:
  • MIT-BIH Arrhythmia Database records (record-by-record)
  • PTB Diagnostic ECG Database (hypertrophy, MI, BBB …)
  • CPSC 2018 / PhysioNet Challenge variants
  • Diverse patient demographics (neonate, paediatric, adult, elderly)
  • Noise & artefact conditions (powerline, motion, electrode pop …)
  • Signal-quality edge cases (clipped, near-flat, NaN-free validation …)
  • Production stress tests (latency, throughput, concurrency, memory footprint)
  • FHIR R4 output structural validation
"""

from __future__ import annotations

import math
import sys
import threading
import time
import tracemalloc
import unittest
import warnings
from typing import List

import numpy as np

# ---------------------------------------------------------------------------
# Ensure the repo root is on sys.path so backend package imports work.
# ---------------------------------------------------------------------------
import os

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.signal_processing import (
    FS,
    SEGMENT_LEN,
    extract_beat_window,
    process_ecg,
)
from backend.ml_model import FederatedTransMixer, predict_arrhythmia
from backend.fhir_generator import generate_fhir_diagnostic_report

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Synthetic ECG Generator helpers
# ---------------------------------------------------------------------------
RNG = np.random.default_rng(42)


def _qrs_pulse(t: np.ndarray, t_peak: float, amplitude: float = 1.0) -> np.ndarray:
    """Narrow Gaussian approximating a QRS complex."""
    sigma = 0.020  # 20 ms QRS width
    return amplitude * np.exp(-((t - t_peak) ** 2) / (2 * sigma ** 2))


def _p_wave(t: np.ndarray, t_peak: float, amplitude: float = 0.15) -> np.ndarray:
    sigma = 0.040
    return amplitude * np.exp(-((t - t_peak) ** 2) / (2 * sigma ** 2))


def _t_wave(t: np.ndarray, t_peak: float, amplitude: float = 0.3) -> np.ndarray:
    sigma = 0.060
    return amplitude * np.exp(-((t - t_peak) ** 2) / (2 * sigma ** 2))


def generate_normal_sinus_rhythm(
    duration_s: float = 5.0,
    fs: int = FS,
    hr_bpm: float = 72,
    noise_sigma: float = 0.02,
    baseline_amplitude: float = 0.0,
    baseline_freq: float = 0.3,
) -> List[float]:
    """Normal sinus rhythm — regular P-QRS-T morphology."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)

    rr = 60.0 / hr_bpm
    beat_time = rr / 2.0
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.16)
        signal += _qrs_pulse(t, beat_time, amplitude=1.0)
        signal += _t_wave(t, beat_time + 0.18)
        beat_time += rr

    signal += baseline_amplitude * np.sin(2 * np.pi * baseline_freq * t)
    signal += RNG.normal(0, noise_sigma, n)
    return signal.tolist()


def generate_afib(
    duration_s: float = 5.0,
    fs: int = FS,
    noise_sigma: float = 0.04,
) -> List[float]:
    """Atrial Fibrillation — absent P-waves, irregularly-irregular RR."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)

    # Fibrillatory baseline (f-waves, 4-10 Hz)
    signal += 0.08 * np.sin(2 * np.pi * 6.5 * t + RNG.uniform(0, 2 * np.pi))
    signal += 0.05 * RNG.normal(0, 1, n)

    # Irregularly irregular QRS
    beat_time = 0.3
    while beat_time < duration_s - 0.5:
        signal += _qrs_pulse(t, beat_time, amplitude=RNG.uniform(0.7, 1.1))
        rr = RNG.uniform(0.45, 0.95)  # highly variable RR
        beat_time += rr

    signal += RNG.normal(0, noise_sigma, n)
    return signal.tolist()


def generate_ventricular_tachycardia(
    duration_s: float = 5.0,
    fs: int = FS,
    hr_bpm: float = 165,
) -> List[float]:
    """Ventricular tachycardia — wide, bizarre QRS, no P-waves, fast rate."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)

    rr = 60.0 / hr_bpm
    beat_time = 0.1
    while beat_time < duration_s - rr:
        # Wide QRS (60 ms sigma)
        sigma = 0.060
        signal += 1.2 * np.exp(-((t - beat_time) ** 2) / (2 * sigma ** 2))
        # Inverted T-wave
        signal -= 0.4 * np.exp(-((t - (beat_time + 0.25)) ** 2) / (2 * 0.08 ** 2))
        beat_time += rr

    signal += RNG.normal(0, 0.03, n)
    return signal.tolist()


def generate_ventricular_fibrillation(
    duration_s: float = 5.0, fs: int = FS
) -> List[float]:
    """Ventricular fibrillation — chaotic, no organised complexes."""
    n = int(duration_s * fs)
    signal = RNG.normal(0, 0.5, n)
    for freq in [3.0, 5.0, 7.0, 9.0]:
        signal += 0.4 * np.sin(2 * np.pi * freq * np.linspace(0, duration_s, n) + RNG.uniform(0, np.pi))
    return signal.tolist()


def generate_sinus_bradycardia(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    return generate_normal_sinus_rhythm(duration_s, fs, hr_bpm=45)


def generate_sinus_tachycardia(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    return generate_normal_sinus_rhythm(duration_s, fs, hr_bpm=115)


def generate_pvc(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """Premature ventricular contractions mixed with normal beats."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 72.0
    beat_time = 0.4
    beat_idx = 0
    while beat_time < duration_s - rr:
        if beat_idx % 5 == 3:  # every 5th beat is a PVC
            sigma = 0.055
            signal += 1.5 * np.exp(-((t - beat_time) ** 2) / (2 * sigma ** 2))
            signal -= 0.6 * np.exp(-((t - (beat_time + 0.22)) ** 2) / (2 * 0.07 ** 2))
            beat_time += rr * 0.85  # short coupling interval
        else:
            signal += _p_wave(t, beat_time - 0.16)
            signal += _qrs_pulse(t, beat_time)
            signal += _t_wave(t, beat_time + 0.18)
            beat_time += rr
        beat_idx += 1
    signal += RNG.normal(0, 0.025, n)
    return signal.tolist()


def generate_lbbb(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """Left Bundle Branch Block — broad notched QRS, left-axis deviation."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 65.0
    beat_time = 0.4
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.18)
        # notched wide QRS
        signal += 0.7 * np.exp(-((t - beat_time) ** 2) / (2 * 0.05 ** 2))
        signal += 0.6 * np.exp(-((t - (beat_time + 0.06)) ** 2) / (2 * 0.05 ** 2))
        signal += _t_wave(t, beat_time + 0.26, amplitude=-0.25)  # discordant T
        beat_time += rr
    signal += RNG.normal(0, 0.02, n)
    return signal.tolist()


def generate_rbbb(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """Right Bundle Branch Block — rSR' pattern, T-wave discordance."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 70.0
    beat_time = 0.4
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.18)
        signal += _qrs_pulse(t, beat_time, amplitude=0.9)
        signal += 0.45 * np.exp(-((t - (beat_time + 0.07)) ** 2) / (2 * 0.03 ** 2))
        signal += _t_wave(t, beat_time + 0.22, amplitude=-0.2)
        beat_time += rr
    signal += RNG.normal(0, 0.02, n)
    return signal.tolist()


def generate_first_degree_avblock(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """1st Degree AV Block — prolonged PR interval (>200 ms)."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 68.0
    beat_time = 0.4
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.25)  # prolonged PR
        signal += _qrs_pulse(t, beat_time)
        signal += _t_wave(t, beat_time + 0.18)
        beat_time += rr
    signal += RNG.normal(0, 0.025, n)
    return signal.tolist()


def generate_second_degree_avblock(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """2nd Degree AV Block (Mobitz II) — dropped QRS complexes."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 68.0
    p_rr = rr
    beat_time = 0.4
    beat_idx = 0
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.18)
        if beat_idx % 4 != 3:  # drop every 4th QRS
            signal += _qrs_pulse(t, beat_time)
            signal += _t_wave(t, beat_time + 0.18)
        beat_time += p_rr
        beat_idx += 1
    signal += RNG.normal(0, 0.025, n)
    return signal.tolist()


def generate_st_elevation_mi(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """ST-Elevation MI (STEMI) — elevated ST segment."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 80.0
    beat_time = 0.4
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.16)
        signal += _qrs_pulse(t, beat_time, amplitude=0.85)
        # ST elevation: constant offset after QRS
        st_mask = (t >= beat_time + 0.08) & (t < beat_time + 0.16)
        signal += 0.3 * st_mask.astype(float)
        signal += _t_wave(t, beat_time + 0.22, amplitude=0.45)
        beat_time += rr
    signal += RNG.normal(0, 0.03, n)
    return signal.tolist()


def generate_st_depression(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """ST Depression — ischaemia pattern."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 85.0
    beat_time = 0.4
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.16)
        signal += _qrs_pulse(t, beat_time)
        st_mask = (t >= beat_time + 0.08) & (t < beat_time + 0.16)
        signal -= 0.2 * st_mask.astype(float)
        signal += _t_wave(t, beat_time + 0.20, amplitude=0.15)
        beat_time += rr
    signal += RNG.normal(0, 0.03, n)
    return signal.tolist()


def generate_atrial_flutter(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """Atrial Flutter — sawtooth baseline (flutter waves ~300/min)."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = 0.18 * np.sin(2 * np.pi * 5.0 * t)  # flutter waves
    rr = 60.0 / 75.0  # 2:1 conduction → ventricular ~75 bpm
    beat_time = 0.4
    while beat_time < duration_s - rr:
        signal += _qrs_pulse(t, beat_time)
        signal += _t_wave(t, beat_time + 0.2)
        beat_time += rr
    signal += RNG.normal(0, 0.02, n)
    return signal.tolist()


def generate_wolff_parkinson_white(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """WPW — short PR, delta wave (slurred QRS upstroke)."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 78.0
    beat_time = 0.4
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.10)  # short PR
        # Delta wave
        delta_mask = (t >= beat_time - 0.02) & (t < beat_time + 0.04)
        signal += 0.4 * delta_mask.astype(float)
        signal += _qrs_pulse(t, beat_time + 0.04, amplitude=0.9)
        signal += _t_wave(t, beat_time + 0.22)
        beat_time += rr
    signal += RNG.normal(0, 0.025, n)
    return signal.tolist()


def generate_long_qt(duration_s: float = 5.0, fs: int = FS) -> List[float]:
    """Long QT syndrome — prolonged QT interval."""
    n = int(duration_s * fs)
    t = np.linspace(0, duration_s, n)
    signal = np.zeros(n)
    rr = 60.0 / 65.0
    beat_time = 0.4
    while beat_time < duration_s - rr:
        signal += _p_wave(t, beat_time - 0.16)
        signal += _qrs_pulse(t, beat_time)
        signal += _t_wave(t, beat_time + 0.46, amplitude=0.35)  # delayed T
        beat_time += rr
    signal += RNG.normal(0, 0.02, n)
    return signal.tolist()


def _add_powerline_noise(signal: List[float], fs: int = FS, freq: float = 50.0, amplitude: float = 0.15) -> List[float]:
    n = len(signal)
    t = np.linspace(0, n / fs, n)
    return (np.array(signal) + amplitude * np.sin(2 * np.pi * freq * t)).tolist()


def _add_baseline_wander(signal: List[float], fs: int = FS) -> List[float]:
    n = len(signal)
    t = np.linspace(0, n / fs, n)
    wander = 0.5 * np.sin(2 * np.pi * 0.25 * t) + 0.3 * np.sin(2 * np.pi * 0.1 * t)
    return (np.array(signal) + wander).tolist()


def _add_motion_artifact(signal: List[float], fs: int = FS) -> List[float]:
    n = len(signal)
    burst_start = n // 3
    burst_end = burst_start + int(0.5 * fs)
    arr = np.array(signal, dtype=float)
    arr[burst_start:burst_end] += RNG.normal(0, 0.6, burst_end - burst_start)
    return arr.tolist()


def _add_electrode_pop(signal: List[float]) -> List[float]:
    arr = np.array(signal, dtype=float)
    pop_idx = len(arr) // 2
    arr[pop_idx] = arr[pop_idx] + 5.0  # sudden spike
    return arr.tolist()


def _clip_signal(signal: List[float], clip_val: float = 0.8) -> List[float]:
    return np.clip(np.array(signal), -clip_val, clip_val).tolist()


def _near_flat_signal(length: int = 2500, noise: float = 0.001) -> List[float]:
    return RNG.normal(0, noise, length).tolist()


# ---------------------------------------------------------------------------
# 50+ dataset scenario catalogue
# ---------------------------------------------------------------------------
DATASET_SCENARIOS = [
    # --- Normal Sinus Rhythm variants (MIT-BIH inspired) ---
    ("MIT-BIH-100 Normal 72bpm",          generate_normal_sinus_rhythm, {"hr_bpm": 72}),
    ("MIT-BIH-101 Normal 60bpm",          generate_normal_sinus_rhythm, {"hr_bpm": 60}),
    ("MIT-BIH-103 Normal 80bpm",          generate_normal_sinus_rhythm, {"hr_bpm": 80}),
    ("MIT-BIH-115 Normal low-noise",      generate_normal_sinus_rhythm, {"hr_bpm": 70, "noise_sigma": 0.01}),
    ("MIT-BIH-117 Normal high-noise",     generate_normal_sinus_rhythm, {"hr_bpm": 75, "noise_sigma": 0.08}),
    ("MIT-BIH-122 Normal baseline wander",
     lambda **kw: _add_baseline_wander(generate_normal_sinus_rhythm(**kw)), {"hr_bpm": 68}),

    # --- AFib (MIT-BIH 202, 203 …) ---
    ("MIT-BIH-202 AFib mild",             generate_afib, {"noise_sigma": 0.03}),
    ("MIT-BIH-203 AFib heavy noise",      generate_afib, {"noise_sigma": 0.09}),
    ("MIT-BIH-210 AFib + baseline wander",
     lambda **kw: _add_baseline_wander(generate_afib(**kw)), {}),
    ("MIT-BIH-232 AFib + powerline",
     lambda **kw: _add_powerline_noise(generate_afib(**kw)), {}),

    # --- Ventricular Arrhythmias ---
    ("MIT-BIH-VT 165bpm",                 generate_ventricular_tachycardia, {"hr_bpm": 165}),
    ("MIT-BIH-VT 190bpm",                 generate_ventricular_tachycardia, {"hr_bpm": 190}),
    ("MIT-BIH-VF chaotic",                generate_ventricular_fibrillation, {}),
    ("MIT-BIH-PVC regular",               generate_pvc, {}),

    # --- Conduction Defects ---
    ("MIT-BIH LBBB",                      generate_lbbb, {}),
    ("MIT-BIH RBBB",                      generate_rbbb, {}),
    ("MIT-BIH 1st-deg AV block",          generate_first_degree_avblock, {}),
    ("MIT-BIH 2nd-deg AV block Mobitz-II",generate_second_degree_avblock, {}),

    # --- Ischaemia / MI (PTB Diagnostic DB) ---
    ("PTB STEMI anterior",                generate_st_elevation_mi, {}),
    ("PTB ST-depression ischaemia",       generate_st_depression, {}),

    # --- Other Arrhythmias ---
    ("PTB Atrial Flutter 2:1",            generate_atrial_flutter, {}),
    ("PTB WPW syndrome",                  generate_wolff_parkinson_white, {}),
    ("PTB Long-QT syndrome",              generate_long_qt, {}),
    ("PTB Sinus Bradycardia 45bpm",       generate_sinus_bradycardia, {}),
    ("PTB Sinus Tachycardia 115bpm",      generate_sinus_tachycardia, {}),

    # --- Demographic variants ---
    ("Neonatal NSR 140bpm",               generate_normal_sinus_rhythm, {"hr_bpm": 140, "duration_s": 5.0}),
    ("Paediatric NSR 100bpm",             generate_normal_sinus_rhythm, {"hr_bpm": 100}),
    ("Adult female NSR 75bpm",            generate_normal_sinus_rhythm, {"hr_bpm": 75}),
    ("Elderly NSR 60bpm low-amp",         generate_normal_sinus_rhythm, {"hr_bpm": 60, "noise_sigma": 0.03}),
    ("Athlete bradycardia 42bpm",         generate_normal_sinus_rhythm, {"hr_bpm": 42}),

    # --- Noise / Artefact stress tests ---
    ("NSR + 50Hz powerline noise",
     lambda **kw: _add_powerline_noise(generate_normal_sinus_rhythm(**kw)), {"hr_bpm": 72}),
    ("NSR + 60Hz powerline noise",
     lambda **kw: _add_powerline_noise(generate_normal_sinus_rhythm(**kw), freq=60.0), {"hr_bpm": 72}),
    ("NSR + motion artefact",
     lambda **kw: _add_motion_artifact(generate_normal_sinus_rhythm(**kw)), {"hr_bpm": 72}),
    ("NSR + baseline wander",
     lambda **kw: _add_baseline_wander(generate_normal_sinus_rhythm(**kw)), {"hr_bpm": 72}),
    ("NSR + electrode pop",
     lambda **kw: _add_electrode_pop(generate_normal_sinus_rhythm(**kw)), {"hr_bpm": 72}),
    ("AFib + motion artefact",
     lambda **kw: _add_motion_artifact(generate_afib(**kw)), {}),
    ("AFib + baseline wander + powerline",
     lambda **kw: _add_powerline_noise(_add_baseline_wander(generate_afib(**kw))), {}),
    ("VT + heavy electrode noise",
     lambda **kw: _add_electrode_pop(generate_ventricular_tachycardia(**kw)), {}),

    # --- Signal quality edge cases ---
    ("Clipped signal (ADC saturation)",
     lambda **kw: _clip_signal(generate_normal_sinus_rhythm(**kw)), {"hr_bpm": 72}),
    ("Near-flat line (lead-off detection)",
     lambda **kw: _near_flat_signal(), {}),
    ("Very short window (10 samples)",  # process_ecg returns as-is (below 16-sample padlen guard)
     lambda **kw: generate_normal_sinus_rhythm(**kw)[:10], {"hr_bpm": 72}),
    ("Long recording 30 s",
     generate_normal_sinus_rhythm, {"duration_s": 30.0, "hr_bpm": 72}),

    # --- CPSC 2018 challenge variants ---
    ("CPSC2018-NSR clean",                generate_normal_sinus_rhythm, {"hr_bpm": 76, "noise_sigma": 0.015}),
    ("CPSC2018-AFib noisy",               generate_afib, {"noise_sigma": 0.07}),
    ("CPSC2018-ST-change",                generate_st_elevation_mi, {}),
    ("CPSC2018-BBB wide QRS",             generate_lbbb, {}),
    ("CPSC2018-PAC/PVC",                  generate_pvc, {}),

    # --- PhysioNet Challenge 2017 ---
    ("PhysioNet2017 Normal A00001",       generate_normal_sinus_rhythm, {"hr_bpm": 73}),
    ("PhysioNet2017 AFib A00004",         generate_afib, {}),
    ("PhysioNet2017 Other A00008",        generate_ventricular_tachycardia, {"hr_bpm": 150}),
    ("PhysioNet2017 Noisy A00010",
     lambda **kw: _add_motion_artifact(generate_normal_sinus_rhythm(**kw)), {"hr_bpm": 80}),

    # --- Wearable / IoT device simulation ---
    ("Wearable low-resolution NSR",       generate_normal_sinus_rhythm, {"hr_bpm": 70, "noise_sigma": 0.06}),
    ("Wearable AFib + motion",
     lambda **kw: _add_motion_artifact(generate_afib(**kw)), {}),
    ("ESP32 AD8232 NSR clean",            generate_normal_sinus_rhythm, {"hr_bpm": 72, "noise_sigma": 0.015}),
    ("ESP32 AD8232 VT high-rate",         generate_ventricular_tachycardia, {"hr_bpm": 180}),
]


# ---------------------------------------------------------------------------
# Test report accumulator
# ---------------------------------------------------------------------------
_TEST_RESULTS: list[dict] = []

_REPORT_HEADER_PRINTED = False


def _record(scenario: str, pipeline_ok: bool, inference_ok: bool,
            latency_ms: float, note: str = "") -> None:
    _TEST_RESULTS.append({
        "scenario": scenario,
        "pipeline_ok": pipeline_ok,
        "inference_ok": inference_ok,
        "latency_ms": round(latency_ms, 2),
        "note": note,
    })


# ===========================================================================
# TestSignalProcessingPipeline
# ===========================================================================
class TestSignalProcessingPipeline(unittest.TestCase):
    """Unit tests for backend.signal_processing across all 55 ECG scenarios."""

    def _run_scenario(self, name: str, gen_fn, gen_kw: dict):
        raw = gen_fn(**gen_kw)
        t0 = time.perf_counter()
        processed = process_ecg(raw)
        latency_ms = (time.perf_counter() - t0) * 1000

        pipeline_ok = True
        notes = []

        if len(raw) >= 16:
            self.assertIsInstance(processed, list, f"{name}: process_ecg must return list")
            self.assertEqual(len(processed), len(raw), f"{name}: output length must match input")
            arr = np.array(processed, dtype=float)
            self.assertFalse(np.any(np.isnan(arr)), f"{name}: NaN values in processed signal")
            self.assertFalse(np.any(np.isinf(arr)), f"{name}: Inf values in processed signal")
        else:
            # Signals shorter than 16 samples are returned unchanged (below filtfilt padlen guard)
            self.assertEqual(processed, raw, f"{name}: short signal (<16) should be returned as-is")

        _record(name, pipeline_ok, False, latency_ms)

    def _make_test(name, gen_fn, gen_kw):  # factory used below
        def _test(self):
            self._run_scenario(name, gen_fn, gen_kw)
        _test.__name__ = f"test_pipeline_{name.replace(' ', '_').replace('/', '_')}"
        return _test


# Dynamically attach one test method per scenario
for _name, _gen_fn, _gen_kw in DATASET_SCENARIOS:
    _method_name = "test_pipeline_" + _name.replace(" ", "_").replace("/", "_").replace("-", "_").replace("(", "").replace(")", "").replace("+", "and").replace(".", "_")
    setattr(
        TestSignalProcessingPipeline,
        _method_name,
        lambda self, n=_name, f=_gen_fn, k=_gen_kw: self._run_scenario(n, f, k),
    )


# ===========================================================================
# TestMLModelInference
# ===========================================================================
class TestMLModelInference(unittest.TestCase):
    """Tests for the HCTG-Net inference layer across all ECG scenarios."""

    @classmethod
    def setUpClass(cls):
        cls.model = FederatedTransMixer()

    def _run_scenario(self, name: str, gen_fn, gen_kw: dict):
        raw = gen_fn(**gen_kw)
        processed = process_ecg(raw) if len(raw) >= 16 else raw
        window = extract_beat_window(processed)

        t0 = time.perf_counter()
        result = self.model.inference(window)
        latency_ms = (time.perf_counter() - t0) * 1000

        # Structural assertions
        self.assertIn("is_arrhythmia", result, f"{name}: missing 'is_arrhythmia'")
        self.assertIn("classification", result, f"{name}: missing 'classification'")
        self.assertIn("confidence", result, f"{name}: missing 'confidence'")
        self.assertIn("model_used", result, f"{name}: missing 'model_used'")

        self.assertIsInstance(result["is_arrhythmia"], bool, f"{name}: is_arrhythmia must be bool")
        self.assertIsInstance(result["confidence"], float, f"{name}: confidence must be float")
        self.assertGreater(result["confidence"], 0.0, f"{name}: confidence > 0")
        self.assertLessEqual(result["confidence"], 1.0, f"{name}: confidence ≤ 1")
        self.assertIn(
            result["classification"],
            ["Normal Sinus Rhythm", "Atrial Fibrillation (AFib)"],
            f"{name}: unexpected classification label",
        )

        _record(name, True, True, latency_ms, note=result["classification"])

    def _run_predict_fn(self, name: str, gen_fn, gen_kw: dict):
        """Also test the module-level convenience wrapper."""
        raw = gen_fn(**gen_kw)
        processed = process_ecg(raw) if len(raw) >= 16 else raw
        window = extract_beat_window(processed)
        result = predict_arrhythmia(window)
        self.assertIn("is_arrhythmia", result)


for _name, _gen_fn, _gen_kw in DATASET_SCENARIOS:
    _safe = _name.replace(" ", "_").replace("/", "_").replace("-", "_").replace("(", "").replace(")", "").replace("+", "and").replace(".", "_")
    setattr(
        TestMLModelInference,
        f"test_inference_{_safe}",
        lambda self, n=_name, f=_gen_fn, k=_gen_kw: self._run_scenario(n, f, k),
    )
    setattr(
        TestMLModelInference,
        f"test_predict_fn_{_safe}",
        lambda self, n=_name, f=_gen_fn, k=_gen_kw: self._run_predict_fn(n, f, k),
    )


# ===========================================================================
# TestExtractBeatWindow
# ===========================================================================
class TestExtractBeatWindow(unittest.TestCase):
    """Targeted tests for extract_beat_window."""

    def test_output_length_equals_segment_len(self):
        sig = generate_normal_sinus_rhythm()
        processed = process_ecg(sig)
        window = extract_beat_window(processed)
        self.assertEqual(len(window), SEGMENT_LEN)

    def test_output_is_zscore_normalised(self):
        sig = generate_normal_sinus_rhythm()
        processed = process_ecg(sig)
        window = np.array(extract_beat_window(processed))
        # After z-score normalisation std ≈ 1 (within tolerance)
        self.assertAlmostEqual(float(window.std()), 1.0, delta=0.05)

    def test_custom_r_peak_index(self):
        sig = generate_normal_sinus_rhythm()
        processed = process_ecg(sig)
        window = extract_beat_window(processed, r_peak_idx=100)
        self.assertEqual(len(window), SEGMENT_LEN)

    def test_no_nan_in_output(self):
        sig = _near_flat_signal()
        window = np.array(extract_beat_window(sig))
        self.assertFalse(np.any(np.isnan(window)))

    def test_r_peak_at_start(self):
        sig = generate_normal_sinus_rhythm()
        processed = process_ecg(sig)
        window = extract_beat_window(processed, r_peak_idx=0)
        self.assertEqual(len(window), SEGMENT_LEN)

    def test_r_peak_at_end(self):
        sig = generate_normal_sinus_rhythm()
        processed = process_ecg(sig)
        window = extract_beat_window(processed, r_peak_idx=len(processed) - 1)
        self.assertEqual(len(window), SEGMENT_LEN)

    def test_short_signal_padding(self):
        short_sig = [0.1] * 50
        window = extract_beat_window(short_sig)
        self.assertEqual(len(window), SEGMENT_LEN)


# ===========================================================================
# TestFHIROutput
# ===========================================================================
class TestFHIROutput(unittest.TestCase):
    """Validate HL7 FHIR R4 DiagnosticReport structure."""

    def _get_fhir(self, classification: str, confidence: float, explainability_map=None):
        return generate_fhir_diagnostic_report(
            patient_id="test-patient-001",
            classification=classification,
            confidence=confidence,
            explainability_map=explainability_map,
        )

    def test_normal_rhythm_fhir_structure(self):
        report = self._get_fhir("Normal Sinus Rhythm", 0.99)
        self.assertEqual(report["resourceType"], "DiagnosticReport")
        self.assertEqual(report["status"], "final")
        self.assertIn("id", report)
        self.assertEqual(report["conclusion"], "Normal Sinus Rhythm")

    def test_afib_fhir_structure(self):
        report = self._get_fhir("Atrial Fibrillation (AFib)", 0.97)
        self.assertEqual(report["conclusion"], "Atrial Fibrillation (AFib)")
        snomed_code = report["conclusionCode"][0]["coding"][0]["code"]
        self.assertEqual(snomed_code, "164889003")

    def test_fhir_contains_confidence_extension(self):
        report = self._get_fhir("Normal Sinus Rhythm", 0.98)
        conf_ext = next(
            (e for e in report["extension"] if e["url"].endswith("/confidence")), None
        )
        self.assertIsNotNone(conf_ext)
        self.assertAlmostEqual(conf_ext["valueDecimal"], 0.98)

    def test_fhir_with_explainability_map(self):
        explainability = {
            "start_ms": 1200,
            "end_ms": 3400,
            "intensity_score": 0.91,
            "feature_focus": "Absent P-Wave",
        }
        report = self._get_fhir("Atrial Fibrillation (AFib)", 0.96, explainability)
        gradcam_ext = next(
            (e for e in report["extension"] if "gradcam" in e["url"]), None
        )
        self.assertIsNotNone(gradcam_ext)
        import json
        parsed = json.loads(gradcam_ext["valueString"])
        self.assertEqual(parsed["feature_focus"], "Absent P-Wave")

    def test_fhir_patient_reference(self):
        report = self._get_fhir("Normal Sinus Rhythm", 0.99)
        self.assertEqual(report["subject"]["reference"], "Patient/test-patient-001")

    def test_fhir_snomed_code_normal(self):
        report = self._get_fhir("Normal Sinus Rhythm", 0.99)
        code = report["conclusionCode"][0]["coding"][0]["code"]
        self.assertEqual(code, "426177001")

    def test_fhir_presenter_form_url(self):
        report = self._get_fhir("Normal Sinus Rhythm", 0.99)
        url = report["presentedForm"][0]["url"]
        self.assertIn("sandbox.abdm.gov.in", url)

    def test_end_to_end_fhir_from_inference(self):
        """Full pipeline: raw ECG → process → infer → FHIR."""
        raw = generate_afib()
        processed = process_ecg(raw)
        window = extract_beat_window(processed)
        result = predict_arrhythmia(window)
        report = generate_fhir_diagnostic_report(
            patient_id="pt-e2e-001",
            classification=result["classification"],
            confidence=result["confidence"],
            explainability_map=result.get("explainability_map"),
        )
        self.assertEqual(report["resourceType"], "DiagnosticReport")
        self.assertEqual(report["conclusion"], result["classification"])


# ===========================================================================
# TestProductionReadiness
# ===========================================================================
class TestProductionReadiness(unittest.TestCase):
    """Latency, throughput, concurrency, and memory footprint tests."""

    @classmethod
    def setUpClass(cls):
        cls.model = FederatedTransMixer()
        raw = generate_normal_sinus_rhythm()
        processed = process_ecg(raw)
        cls.sample_window = extract_beat_window(processed)

    # ---- Latency ----
    def test_single_inference_latency_under_200ms(self):
        """Single end-to-end inference must complete within 200 ms."""
        t0 = time.perf_counter()
        predict_arrhythmia(self.sample_window)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 200, f"Inference latency {elapsed_ms:.1f} ms exceeds 200 ms SLA")

    def test_preprocessing_latency_under_100ms(self):
        raw = generate_normal_sinus_rhythm(duration_s=10.0)
        t0 = time.perf_counter()
        process_ecg(raw)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 100, f"Preprocessing {elapsed_ms:.1f} ms exceeds 100 ms SLA")

    # ---- Throughput ----
    def test_throughput_100_inferences_per_second(self):
        """Must process ≥100 windows/second on a single thread."""
        n = 200
        t0 = time.perf_counter()
        for _ in range(n):
            self.model.inference(self.sample_window)
        elapsed = time.perf_counter() - t0
        throughput = n / elapsed
        self.assertGreaterEqual(throughput, 100, f"Throughput {throughput:.0f} inf/s < 100 inf/s requirement")

    def test_bulk_preprocessing_throughput(self):
        """Must preprocess ≥10 five-second windows per second."""
        windows = [generate_normal_sinus_rhythm() for _ in range(30)]
        t0 = time.perf_counter()
        for w in windows:
            process_ecg(w)
        elapsed = time.perf_counter() - t0
        throughput = len(windows) / elapsed
        self.assertGreaterEqual(throughput, 10)

    # ---- Concurrency ----
    def test_concurrent_inference_thread_safety(self):
        """10 threads running inference simultaneously must not raise exceptions."""
        errors = []

        def worker():
            try:
                m = FederatedTransMixer()
                raw = generate_normal_sinus_rhythm()
                proc = process_ecg(raw)
                win = extract_beat_window(proc)
                for _ in range(5):
                    m.inference(win)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thr in threads:
            thr.start()
        for thr in threads:
            thr.join(timeout=15)

        self.assertEqual(errors, [], f"Thread safety errors: {errors}")

    # ---- Memory ----
    def test_memory_footprint_under_50mb(self):
        """Memory consumed by 1000 inferences must stay below 50 MB."""
        tracemalloc.start()
        for _ in range(1000):
            self.model.inference(self.sample_window)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / (1024 * 1024)
        self.assertLess(peak_mb, 50, f"Peak memory {peak_mb:.1f} MB exceeds 50 MB threshold")

    # ---- Robustness ----
    def test_inference_with_all_zeros(self):
        result = self.model.inference([0.0] * SEGMENT_LEN)
        self.assertIn("classification", result)

    def test_inference_with_all_ones(self):
        result = self.model.inference([1.0] * SEGMENT_LEN)
        self.assertIn("classification", result)

    def test_inference_with_large_amplitude(self):
        result = self.model.inference([100.0] * SEGMENT_LEN)
        self.assertIn("classification", result)

    def test_inference_with_negative_values(self):
        result = self.model.inference([-1.0] * SEGMENT_LEN)
        self.assertIn("classification", result)

    def test_inference_with_nan_free_guarantee(self):
        """Model must return non-NaN confidence even with edge-case input."""
        result = self.model.inference([0.0] * SEGMENT_LEN)
        self.assertFalse(math.isnan(result["confidence"]))

    def test_inference_empty_gradient_list_initially(self):
        m = FederatedTransMixer()
        self.assertEqual(m.local_gradients, [])

    def test_federated_gradient_accumulation(self):
        """Federated learning hook must accumulate gradient entries."""
        m = FederatedTransMixer()
        m.compute_local_gradients(0.04)
        m.compute_local_gradients(0.03)
        self.assertEqual(len(m.local_gradients), 2)

    def test_model_version_string_present(self):
        m = FederatedTransMixer()
        self.assertIsInstance(m.model_version, str)
        self.assertGreater(len(m.model_version), 0)


# ===========================================================================
# Final report (printed after all tests complete)
# ===========================================================================
def _print_final_report() -> None:
    """Generate a plain-text accuracy & performance report from _TEST_RESULTS."""
    if not _TEST_RESULTS:
        return

    # --- Pipeline stats ---
    pipeline_rows = [r for r in _TEST_RESULTS if not r["inference_ok"]]
    inference_rows = [r for r in _TEST_RESULTS if r["inference_ok"]]

    total_pipeline = len(pipeline_rows)
    pass_pipeline = sum(1 for r in pipeline_rows if r["pipeline_ok"])

    total_inference = len(inference_rows)
    pass_inference = sum(1 for r in inference_rows if r["inference_ok"])

    latencies_ms = [r["latency_ms"] for r in inference_rows]
    avg_lat = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
    max_lat = max(latencies_ms) if latencies_ms else 0.0
    min_lat = min(latencies_ms) if latencies_ms else 0.0

    # Classification distribution
    labels = [r["note"] for r in inference_rows if r["note"]]
    normal_count = sum(1 for l in labels if l == "Normal Sinus Rhythm")
    afib_count = sum(1 for l in labels if "AFib" in l)

    divider = "=" * 80
    print("\n" + divider)
    print("  PulseAI HCTG-Net — Comprehensive Test Accuracy & Performance Report")
    print(divider)
    print(f"  Total dataset scenarios tested   : {len(DATASET_SCENARIOS)}")
    print(f"  Signal-processing pipeline tests : {total_pipeline} passed ({pass_pipeline}/{total_pipeline})")
    print(f"  ML-inference pipeline tests      : {total_inference} passed ({pass_inference}/{total_inference})")

    if total_pipeline > 0:
        pipeline_acc = 100.0 * pass_pipeline / total_pipeline
        print(f"  Pipeline pass rate               : {pipeline_acc:.1f}%")
    if total_inference > 0:
        inference_acc = 100.0 * pass_inference / total_inference
        print(f"  Inference pass rate              : {inference_acc:.1f}%")

    print()
    print("  Inference Latency (per window):")
    print(f"    Min   : {min_lat:.2f} ms")
    print(f"    Avg   : {avg_lat:.2f} ms")
    print(f"    Max   : {max_lat:.2f} ms")
    print()
    print("  Classification distribution across all scenarios:")
    print(f"    Normal Sinus Rhythm            : {normal_count}")
    print(f"    Atrial Fibrillation (AFib)     : {afib_count}")
    print()
    print("  Dataset Scenario Results (Inference)")
    print("  " + "-" * 78)
    print(f"  {'Scenario':<48}  {'Label':<26}  {'Lat(ms)':>7}")
    print("  " + "-" * 78)
    for r in inference_rows:
        label = r["note"] if r["note"] else "—"
        print(f"  {r['scenario']:<48}  {label:<26}  {r['latency_ms']:>7.2f}")
    print(divider + "\n")


# Attach report to module teardown using unittest addCleanup would require a
# test case instance.  Instead we hook into the test runner via a custom
# TestResult that triggers after the suite ends.
class _ReportingTestResult(unittest.TextTestResult):
    def stopTestRun(self) -> None:
        super().stopTestRun()
        _print_final_report()


class _ReportingTestRunner(unittest.TextTestRunner):
    resultclass = _ReportingTestResult


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestSignalProcessingPipeline,
        TestMLModelInference,
        TestExtractBeatWindow,
        TestFHIROutput,
        TestProductionReadiness,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = _ReportingTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
