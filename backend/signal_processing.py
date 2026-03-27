import numpy as np  # type: ignore
from scipy import signal as sp_signal  # type: ignore

FS = 500          # AD8232 / ESP32 sample rate (configurable)
SEGMENT_LEN = 250  # samples per inference window

def _bandpass_coeffs(lowcut=0.5, highcut=40.0, fs=FS, order=4):
    nyq = 0.5 * fs
    return sp_signal.butter(order, [lowcut / nyq, highcut / nyq], btype='band')

def _notch_coeffs(freq=50.0, fs=FS, Q=30):
    """50Hz (India) powerline noise notch."""
    return sp_signal.iirnotch(freq / (fs / 2.0), Q)

def process_ecg(raw_signal_buffer: list, fs: int = FS) -> list:
    """
    Full clinical ECG preprocessing pipeline using sos to prevent NaN/numerical collapse:
      1. High-pass (0.5 Hz) — removes baseline wander / DC drift
      2. Notch (50 Hz)      — removes Indian powerline interference
      3. Bandpass (0.5–40 Hz) — retains clinically relevant ECG band
    Returns a float list of the same length as input.
    """
    if len(raw_signal_buffer) < 10:
        return raw_signal_buffer

    data = np.array(raw_signal_buffer, dtype=np.float64)

    # 1. High-pass to remove baseline wander
    sos_hp = sp_signal.butter(4, 0.5 / (fs / 2.0), btype='high', output='sos')
    data = sp_signal.sosfiltfilt(sos_hp, data)

    # 2. 50 Hz powerline notch (iirnotch provides b,a which are usually stable for notch, but let's be careful)
    b_n, a_n = _notch_coeffs(50.0, fs)
    data = sp_signal.filtfilt(b_n, a_n, data)

    # 3. Bandpass 0.5–40 Hz
    sos_bp = sp_signal.butter(4, [0.5 / (fs / 2.0), 40.0 / (fs / 2.0)], btype='band', output='sos')
    data = sp_signal.sosfiltfilt(sos_bp, data)

    # Convert NaNs to 0 in case of an issue
    data = np.nan_to_num(data, nan=0.0)

    return data.tolist()

def extract_beat_window(cleaned_signal: list, r_peak_idx: int | None = None) -> list:
    """
    Extract a SEGMENT_LEN window centered on the strongest peak (R-peak),
    or centered in the signal if no peak given. Used for per-beat inference.
    """
    data = np.array(cleaned_signal, dtype=np.float32)
    if r_peak_idx is None:
        # Use midpoint of signal
        r_peak_idx = len(data) // 2

    half = SEGMENT_LEN // 2
    start = max(0, r_peak_idx - half)
    end = start + SEGMENT_LEN
    if end > len(data):
        end = len(data)
        start = max(0, end - SEGMENT_LEN)

    window = data[start:end]
    # Pad if shorter than SEGMENT_LEN
    if len(window) < SEGMENT_LEN:
        window = np.pad(window, (0, SEGMENT_LEN - len(window)), mode='edge')

    # Return the raw window so models can evaluate amplitude severity
    return window.tolist()
