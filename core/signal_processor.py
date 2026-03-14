import numpy as np
import time

from core.rpeak_detector import RPeakDetector
from core.hrv_metrics import HRVMetrics


class SignalProcessor:

    def __init__(self, config):

        self.config = config
        self.sample_rate = config.get("ecg", "sample_rate_hz")

        self.detector = RPeakDetector(self.sample_rate)
        self.metrics = HRVMetrics()

        self.signal_buffer = []

        self.last_peak_index = None
        self.last_processed_peak = None

        self.global_index = 0

        self.last_metrics = None

    def process(self, samples):

        results = []

        self.signal_buffer.extend(samples)

        if len(self.signal_buffer) < self.sample_rate * 2:
            return results

        signal = np.array(self.signal_buffer)

        peaks = self.detector.detect(signal)

        new_metrics = None

        for peak in peaks:

            peak_global = self.global_index + peak

            # evita reprocessar picos já detectados
            if self.last_processed_peak and peak_global <= self.last_processed_peak:
                continue

            if self.last_peak_index is None:
                self.last_peak_index = peak_global
                self.last_processed_peak = peak_global
                continue

            rr_samples = peak_global - self.last_peak_index
            rr = rr_samples / self.sample_rate

            self.last_peak_index = peak_global
            self.last_processed_peak = peak_global

            # rejeição fisiológica
            if rr < 0.3 or rr > 2.0:
                continue

            self.metrics.update_rr(rr)

            computed = self.metrics.compute()

            packet = {
                "rr": rr,
                "timestamp": time.time()
            }

            if computed:
                packet.update(computed)

            self.last_metrics = packet
            new_metrics = packet

        trim = self.sample_rate

        self.signal_buffer = self.signal_buffer[trim:]
        self.global_index += trim

        if new_metrics:
            results.append(new_metrics)

        elif self.last_metrics:
            packet = self.last_metrics.copy()
            packet["timestamp"] = time.time()
            results.append(packet)

        return results