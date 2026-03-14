import numpy as np
from scipy.signal import welch
from scipy.integrate import trapezoid


class HRVMetrics:

    def __init__(self):

        self.rr_buffer = []
        self.max_buffer = 256

    def update_rr(self, rr):

        if rr < 0.3 or rr > 2.0:
            return

        self.rr_buffer.append(rr)

        if len(self.rr_buffer) > self.max_buffer:
            self.rr_buffer.pop(0)

    def compute(self):

        if len(self.rr_buffer) < 3:
            return None

        rr = np.array(self.rr_buffer)

        # HR com média móvel curta (mais estável)
        window = min(5, len(rr))
        hr = 60.0 / np.mean(rr[-window:])

        # SDNN
        sdnn = np.std(rr, ddof=1) if len(rr) > 1 else None

        diff_rr = np.diff(rr)

        if len(diff_rr) > 0:

            rmssd = np.sqrt(np.mean(diff_rr ** 2))

            nn50 = np.sum(np.abs(diff_rr) > 0.05)
            pnn50 = nn50 / len(diff_rr)

        else:

            rmssd = None
            pnn50 = None

        lf_hf = None

        # cálculo espectral requer mais histórico
        if len(rr) > 20:

            time_axis = np.cumsum(rr)

            fs = 4.0  # Hz (interpolação recomendada para HRV)

            t_interp = np.arange(time_axis[0], time_axis[-1], 1 / fs)

            if len(t_interp) > 4:

                rr_interp = np.interp(t_interp, time_axis, rr)

                rr_interp = rr_interp - np.mean(rr_interp)

                freqs, psd = welch(
                    rr_interp,
                    fs=fs,
                    nperseg=min(256, len(rr_interp))
                )

                lf_band = (freqs >= 0.04) & (freqs < 0.15)
                hf_band = (freqs >= 0.15) & (freqs < 0.40)

                lf = trapezoid(psd[lf_band], freqs[lf_band]) if np.any(lf_band) else 0
                hf = trapezoid(psd[hf_band], freqs[hf_band]) if np.any(hf_band) else 0

                if hf > 0:
                    lf_hf = lf / hf

        return {
            "hr": float(hr) if hr is not None else None,
            "rmssd": float(rmssd) if rmssd is not None else None,
            "sdnn": float(sdnn) if sdnn is not None else None,
            "pnn50": float(pnn50) if pnn50 is not None else None,
            "lf_hf": float(lf_hf) if lf_hf is not None else None
        }