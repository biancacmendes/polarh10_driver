import numpy as np
from scipy.signal import find_peaks


class RPeakDetector:

    def __init__(self, fs):

        self.fs = fs
        self.min_distance = int(fs * 0.35)  # ~350ms refractory

    def detect(self, signal):

        if len(signal) < self.fs:
            return []

        signal = np.asarray(signal)

        # threshold adaptativo baseado no percentil
        threshold = np.percentile(signal, 97)

        peaks, _ = find_peaks(
            signal,
            height=threshold,
            distance=self.min_distance
        )

        return peaks