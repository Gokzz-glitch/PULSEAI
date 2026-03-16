import logging
import os
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from scipy.signal import find_peaks

try:
    from tensorflow import keras
except Exception:  # pragma: no cover
    keras = None

logger = logging.getLogger(__name__)

FS = 500


class ArrhythmiaEngine:
    """Production-safe ECG inference with ML-first and deterministic fallback."""

    def __init__(self) -> None:
        self.model_path = Path(os.getenv("MODEL_PATH", "hctg_net_model.h5"))
        self.model = None
        self.model_version = "heuristic-v2"
        self.labels = ["Normal Sinus Rhythm", "Atrial Fibrillation (AFib)", "Other Arrhythmia"]
        self._load_model_if_available()

    def _load_model_if_available(self) -> None:
        if keras is None:
            logger.warning("TensorFlow unavailable. Falling back to heuristic inference.")
            return
        if not self.model_path.exists():
            logger.info("Model file not found at %s. Using heuristic inference.", self.model_path)
            return

        try:
            self.model = keras.models.load_model(self.model_path, compile=False)
            self.model_version = f"keras:{self.model_path.name}"
            logger.info("Loaded ECG model: %s", self.model_version)
        except Exception as exc:
            logger.error("Failed to load ECG model (%s). Using heuristic fallback.", exc)
            self.model = None

    @staticmethod
    def _normalize(window: np.ndarray) -> np.ndarray:
        std = float(np.std(window))
        if std < 1e-6:
            return np.zeros_like(window)
        return (window - float(np.mean(window))) / std

    def _infer_with_keras(self, signal_window: np.ndarray) -> Optional[Dict]:
        if self.model is None:
            return None

        x = self._normalize(signal_window).astype(np.float32)[None, :, None]
        try:
            probs = np.array(self.model.predict(x, verbose=0)).reshape(-1)
            if probs.size == 1:
                af_prob = float(np.clip(probs[0], 0.0, 1.0))
                class_idx = 1 if af_prob >= 0.5 else 0
                confidence = af_prob if class_idx == 1 else 1.0 - af_prob
                probs_out = [1.0 - af_prob, af_prob, 0.0]
            else:
                probs = probs / max(np.sum(probs), 1e-6)
                class_idx = int(np.argmax(probs))
                confidence = float(np.clip(probs[class_idx], 0.0, 1.0))
                probs_out = [float(v) for v in probs[:3]]
                while len(probs_out) < 3:
                    probs_out.append(0.0)

            classification = self.labels[class_idx] if class_idx < len(self.labels) else self.labels[2]
            return {
                "is_arrhythmia": class_idx != 0,
                "classification": classification,
                "confidence": round(confidence, 3),
                "probabilities": {
                    "normal": round(probs_out[0], 3),
                    "afib": round(probs_out[1], 3),
                    "other": round(probs_out[2], 3),
                },
                "heart_rate_bpm": None,
                "rr_cv": None,
                "signal_quality": "good",
                "model_used": self.model_version,
                "explainability_map": None,
            }
        except Exception as exc:
            logger.warning("Model inference error: %s. Falling back to heuristic mode.", exc)
            return None

    def _infer_heuristic(self, signal_window: np.ndarray) -> Dict:
        if signal_window.size < 40:
            return {
                "is_arrhythmia": False,
                "classification": "Insufficient Signal",
                "confidence": 0.55,
                "probabilities": {"normal": 0.45, "afib": 0.25, "other": 0.30},
                "heart_rate_bpm": None,
                "rr_cv": None,
                "signal_quality": "poor",
                "model_used": self.model_version,
                "explainability_map": None,
            }

        z = self._normalize(signal_window)
        amp_span = float(np.percentile(z, 95) - np.percentile(z, 5))

        peak_height = max(0.8, float(np.percentile(z, 92)))
        min_distance = int(0.25 * FS)
        peaks, _ = find_peaks(z, distance=min_distance, height=peak_height)

        if len(peaks) < 2:
            quality = "poor" if amp_span < 1.2 else "fair"
            return {
                "is_arrhythmia": quality == "poor",
                "classification": "Poor Signal Quality" if quality == "poor" else "Normal Sinus Rhythm",
                "confidence": 0.72 if quality == "poor" else 0.62,
                "probabilities": {"normal": 0.62, "afib": 0.18, "other": 0.20},
                "heart_rate_bpm": None,
                "rr_cv": None,
                "signal_quality": quality,
                "model_used": self.model_version,
                "explainability_map": None,
            }

        rr = np.diff(peaks) / FS
        rr_mean = float(np.mean(rr))
        rr_std = float(np.std(rr))
        rr_cv = float(rr_std / max(rr_mean, 1e-6))
        heart_rate = float(60.0 / max(rr_mean, 1e-6))

        is_af_like = rr_cv >= 0.13 and len(rr) >= 3
        is_tachy = heart_rate > 110.0
        is_brady = heart_rate < 45.0

        if is_af_like:
            classification = "Atrial Fibrillation (AFib)"
            anomaly_score = min(1.0, 0.6 + rr_cv)
            feature_focus = "Irregular RR interval variability"
        elif is_tachy:
            classification = "Tachycardia Pattern"
            anomaly_score = min(1.0, 0.5 + (heart_rate - 110.0) / 80.0)
            feature_focus = "Sustained short RR intervals"
        elif is_brady:
            classification = "Bradycardia Pattern"
            anomaly_score = min(1.0, 0.5 + (45.0 - heart_rate) / 40.0)
            feature_focus = "Sustained long RR intervals"
        else:
            classification = "Normal Sinus Rhythm"
            anomaly_score = max(0.0, 0.25 - rr_cv)
            feature_focus = "Stable RR intervals"

        confidence = float(np.clip(0.60 + anomaly_score * 0.35, 0.50, 0.97))
        normal_prob = max(0.0, 1.0 - anomaly_score)
        afib_prob = anomaly_score if "AFib" in classification else max(0.0, anomaly_score * 0.55)
        other_prob = max(0.0, 1.0 - normal_prob - afib_prob)
        denom = normal_prob + afib_prob + other_prob
        probs = {
            "normal": round(normal_prob / denom, 3),
            "afib": round(afib_prob / denom, 3),
            "other": round(other_prob / denom, 3),
        }

        i = int(np.argmax(np.abs(np.diff(rr)))) if len(rr) > 1 else 0
        start_ms = int(peaks[i] / FS * 1000)
        end_ms = int(peaks[min(i + 1, len(peaks) - 1)] / FS * 1000)
        explainability_map = {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "intensity_score": round(float(min(0.99, 0.55 + anomaly_score * 0.4)), 3),
            "feature_focus": feature_focus,
        }

        signal_quality = "good" if amp_span >= 1.5 else "fair"
        return {
            "is_arrhythmia": classification != "Normal Sinus Rhythm",
            "classification": classification,
            "confidence": round(confidence, 3),
            "probabilities": probs,
            "heart_rate_bpm": round(heart_rate, 1),
            "rr_cv": round(rr_cv, 3),
            "signal_quality": signal_quality,
            "model_used": self.model_version,
            "explainability_map": explainability_map if classification != "Normal Sinus Rhythm" else None,
        }

    def predict(self, cleaned_ecg_window: list) -> Dict:
        signal_window = np.array(cleaned_ecg_window, dtype=np.float32)
        if signal_window.size == 0:
            return {
                "is_arrhythmia": False,
                "classification": "No Signal",
                "confidence": 0.51,
                "probabilities": {"normal": 0.34, "afib": 0.33, "other": 0.33},
                "heart_rate_bpm": None,
                "rr_cv": None,
                "signal_quality": "poor",
                "model_used": self.model_version,
                "explainability_map": None,
            }

        model_result = self._infer_with_keras(signal_window)
        if model_result is not None:
            return model_result
        return self._infer_heuristic(signal_window)

    def status(self) -> Dict:
        return {
            "model_loaded": self.model is not None,
            "model_used": self.model_version,
            "model_path": str(self.model_path),
        }


edge_ai = ArrhythmiaEngine()


def predict_arrhythmia(cleaned_ecg_window: list) -> Dict:
    return edge_ai.predict(cleaned_ecg_window)


def get_model_status() -> Dict:
    return edge_ai.status()
