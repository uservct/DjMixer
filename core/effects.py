"""
core/effects.py
───────────────
Thành viên 3 – Audio Effects (EQ, Reverb, Echo, Filter)

v2: Stateful filtering – mỗi bộ lọc lưu trạng thái giữa các chunk
để tránh artifact khi xử lý real-time.

Effects:
  - EQ 3 dải: Bass (< 300Hz) / Mid (300-4000Hz) / Treble (> 4000Hz)
  - Low-pass filter (cắt tần số cao)
  - High-pass filter (cắt tần số thấp)
  - Echo (delay + feedback)
  - Reverb (Schroeder comb + all-pass)

EffectsChain: class tổng hợp, gắn vào AudioEngine để xử lý từng chunk.
"""

import numpy as np
from scipy import signal


# ── Helper: Stateful biquad filter ──────────────────────────────────────────

class StatefulFilter:
    """
    Biquad filter có trạng thái (IIR filter state).
    Giữ state giữa các lần gọi process() để tránh artifact tại biên chunk.
    """

    def __init__(self, b: np.ndarray, a: np.ndarray, channels: int = 2):
        self.b = b
        self.a = a
        self.channels = channels
        # Filter state: shape [max(len(a), len(b)) - 1, channels]
        n_state = max(len(a), len(b)) - 1
        self._zi = np.zeros((n_state, channels), dtype=np.float32)
        self._initialized = False

    def process(self, data: np.ndarray) -> np.ndarray:
        """Áp dụng filter với trạng thái liên tục giữa các chunk."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
            squeeze = True
        else:
            squeeze = False

        n_ch = min(data.shape[1], self.channels)
        out = np.zeros_like(data)

        # Đảm bảo zi đúng shape
        if self._zi.shape[1] != n_ch:
            n_state = max(len(self.a), len(self.b)) - 1
            self._zi = np.zeros((n_state, n_ch), dtype=np.float32)

        for ch in range(n_ch):
            if not self._initialized:
                # Khởi tạo zi từ mẫu đầu tiên (tránh transient hiện đầu)
                zi_init = signal.lfilter_zi(self.b, self.a) * data[0, ch]
                self._zi[:, ch] = zi_init
            out_ch, new_zi = signal.lfilter(
                self.b, self.a, data[:, ch].astype(np.float64),
                zi=self._zi[:, ch].astype(np.float64)
            )
            self._zi[:, ch] = new_zi.astype(np.float32)
            out[:, ch] = out_ch.astype(np.float32)

        self._initialized = True
        return out.squeeze() if squeeze else out

    def reset(self):
        """Reset trạng thái (gọi khi load file mới hoặc seek)."""
        self._zi[:] = 0
        self._initialized = False


def _make_lowpass(cutoff_hz: float, sr: int, order: int = 4) -> StatefulFilter:
    nyq = sr / 2.0
    norm = min(max(cutoff_hz / nyq, 0.001), 0.999)
    b, a = signal.butter(order, norm, btype="low")
    return StatefulFilter(b, a)


def _make_highpass(cutoff_hz: float, sr: int, order: int = 4) -> StatefulFilter:
    nyq = sr / 2.0
    norm = min(max(cutoff_hz / nyq, 0.001), 0.999)
    b, a = signal.butter(order, norm, btype="high")
    return StatefulFilter(b, a)


def _make_bandpass(lo_hz: float, hi_hz: float, sr: int) -> StatefulFilter:
    nyq = sr / 2.0
    lo = min(max(lo_hz / nyq, 0.001), 0.999)
    hi = min(max(hi_hz / nyq, 0.001), 0.999)
    if lo >= hi:
        hi = min(lo + 0.001, 0.999)
    b, a = signal.butter(2, [lo, hi], btype="band")
    return StatefulFilter(b, a)


# ── EQ 3-Band ────────────────────────────────────────────────────────────────

class EQ3Band:
    """
    EQ 3 dải stateful:
      Bass  : tần số < 300 Hz
      Mid   : 300 Hz → 4000 Hz
      Treble: > 4000 Hz
    Gain: -12 dB → +12 dB (0 dB = không đổi)
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.bass_gain_db: float = 0.0
        self.mid_gain_db: float = 0.0
        self.treble_gain_db: float = 0.0

        # Stateful filters để tách 3 dải
        self._lp_bass = _make_lowpass(300.0, sample_rate, order=2)
        self._hp_treble = _make_highpass(4000.0, sample_rate, order=2)
        self._rebuilt = False

    @staticmethod
    def _db_to_linear(db: float) -> float:
        return 10 ** (db / 20.0)

    def process(self, data: np.ndarray) -> np.ndarray:
        """Tách 3 dải, áp gain rồi cộng lại."""
        bass   = self._lp_bass.process(data.copy())
        treble = self._hp_treble.process(data.copy())
        mid    = data - bass - treble  # phần giữa

        bass   = bass   * self._db_to_linear(self.bass_gain_db)
        mid    = mid    * self._db_to_linear(self.mid_gain_db)
        treble = treble * self._db_to_linear(self.treble_gain_db)

        result = (bass + mid + treble).astype(np.float32)
        return np.clip(result, -1.0, 1.0)

    def reset(self):
        self._lp_bass.reset()
        self._hp_treble.reset()


# ── Low-pass / High-pass (stateful) ──────────────────────────────────────────

class LowpassEffect:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.cutoff_hz: float = 1000.0
        self._filter: StatefulFilter | None = None
        self._last_cutoff: float = -1.0

    def process(self, data: np.ndarray) -> np.ndarray:
        if self.cutoff_hz != self._last_cutoff:
            self._filter = _make_lowpass(self.cutoff_hz, self.sample_rate)
            self._last_cutoff = self.cutoff_hz
        return self._filter.process(data)

    def reset(self):
        if self._filter:
            self._filter.reset()


class HighpassEffect:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.cutoff_hz: float = 1000.0
        self._filter: StatefulFilter | None = None
        self._last_cutoff: float = -1.0

    def process(self, data: np.ndarray) -> np.ndarray:
        if self.cutoff_hz != self._last_cutoff:
            self._filter = _make_highpass(self.cutoff_hz, self.sample_rate)
            self._last_cutoff = self.cutoff_hz
        return self._filter.process(data)

    def reset(self):
        if self._filter:
            self._filter.reset()


# ── Echo (delay line stateful) ───────────────────────────────────────────────

class EchoEffect:
    """
    Echo: trộn tín hiệu gốc với bản trễ delay_sec giây.
    Duy trì delay buffer giữa các chunk.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.delay_sec: float = 0.3
        self.feedback: float = 0.4
        self._buffer: np.ndarray | None = None
        self._buf_pos: int = 0

    def _ensure_buffer(self, n_channels: int = 2):
        delay_samples = int(self.delay_sec * self.sample_rate)
        delay_samples = max(1, delay_samples)
        if (self._buffer is None or
                self._buffer.shape[0] != delay_samples or
                self._buffer.shape[1] != n_channels):
            self._buffer = np.zeros((delay_samples, n_channels), dtype=np.float32)
            self._buf_pos = 0

    def process(self, data: np.ndarray) -> np.ndarray:
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        n_ch = data.shape[1]
        self._ensure_buffer(n_ch)

        output = data.copy()
        buf_len = self._buffer.shape[0]

        for i in range(len(data)):
            delayed = self._buffer[self._buf_pos].copy()
            output[i] = data[i] + self.feedback * delayed
            self._buffer[self._buf_pos] = output[i]
            self._buf_pos = (self._buf_pos + 1) % buf_len

        return np.clip(output, -1.0, 1.0).astype(np.float32)

    def reset(self):
        self._buffer = None
        self._buf_pos = 0


# ── Reverb ────────────────────────────────────────────────────────────────────

class ReverbEffect:
    """
    Reverb đơn giản: nhiều comb filter song song + all-pass nối tiếp.
    Duy trì buffer giữa các chunk.
    """

    COMB_DELAYS_MS = [29.7, 37.1, 41.1, 43.7]
    ALLPASS_DELAYS_MS = [5.0, 1.7]

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.room_size: float = 0.5
        self.damping: float = 0.5
        self._comb_bufs: list = []
        self._comb_poses: list = []
        self._ap_bufs: list = []
        self._ap_poses: list = []
        self._initialized = False

    def _init_buffers(self, n_ch: int = 2):
        sr = self.sample_rate
        self._comb_bufs = []
        self._comb_poses = []
        for d_ms in self.COMB_DELAYS_MS:
            delay = max(1, int((d_ms + self.room_size * 50) * sr / 1000))
            self._comb_bufs.append(np.zeros((delay, n_ch), dtype=np.float32))
            self._comb_poses.append(0)

        self._ap_bufs = []
        self._ap_poses = []
        for d_ms in self.ALLPASS_DELAYS_MS:
            delay = max(1, int(d_ms * sr / 1000))
            self._ap_bufs.append(np.zeros((delay, n_ch), dtype=np.float32))
            self._ap_poses.append(0)

        self._initialized = True
        self._n_ch = n_ch

    def process(self, data: np.ndarray) -> np.ndarray:
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        n_ch = data.shape[1]

        if not self._initialized or self._n_ch != n_ch:
            self._init_buffers(n_ch)

        feedback = 0.84 - self.damping * 0.1
        wet = np.zeros_like(data)

        # Comb filters (song song)
        for idx in range(len(self._comb_bufs)):
            buf = self._comb_bufs[idx]
            pos = self._comb_poses[idx]
            buf_len = len(buf)
            comb_out = np.zeros_like(data)
            for i in range(len(data)):
                delayed = buf[pos].copy()
                comb_out[i] = data[i] + feedback * delayed
                buf[pos] = comb_out[i]
                pos = (pos + 1) % buf_len
            self._comb_poses[idx] = pos
            wet += comb_out

        wet /= len(self._comb_bufs)

        # All-pass filters (nối tiếp)
        gain = 0.5
        for idx in range(len(self._ap_bufs)):
            buf = self._ap_bufs[idx]
            pos = self._ap_poses[idx]
            buf_len = len(buf)
            ap_out = np.zeros_like(wet)
            for i in range(len(wet)):
                delayed = buf[pos].copy()
                v = wet[i] + gain * delayed
                ap_out[i] = -gain * v + delayed
                buf[pos] = v
                pos = (pos + 1) % buf_len
            self._ap_poses[idx] = pos
            wet = ap_out

        mixed = (data * 0.6 + wet * 0.4).astype(np.float32)
        return np.clip(mixed, -1.0, 1.0)

    def reset(self):
        self._initialized = False


# ── EffectsChain ──────────────────────────────────────────────────────────────

class EffectsChain:
    """
    Chuỗi effects cho một Deck. Được gắn vào AudioEngine.
    AudioEngine.process(chunk) sẽ gọi EffectsChain.process(chunk) mỗi ~46ms.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        self.eq = EQ3Band(sample_rate)

        self._lowpass = LowpassEffect(sample_rate)
        self._highpass = HighpassEffect(sample_rate)
        self._echo = EchoEffect(sample_rate)
        self._reverb = ReverbEffect(sample_rate)

        # Trạng thái bật/tắt
        self.lowpass_enabled: bool = False
        self.highpass_enabled: bool = False
        self.echo_enabled: bool = False
        self.reverb_enabled: bool = False

        # Properties được GUI set
        @property
        def lowpass_cutoff(self): return self._lowpass.cutoff_hz
        @lowpass_cutoff.setter
        def lowpass_cutoff(self, v): self._lowpass.cutoff_hz = float(v)

        @property
        def highpass_cutoff(self): return self._highpass.cutoff_hz
        @highpass_cutoff.setter
        def highpass_cutoff(self, v): self._highpass.cutoff_hz = float(v)

        @property
        def echo_delay(self): return self._echo.delay_sec
        @echo_delay.setter
        def echo_delay(self, v): self._echo.delay_sec = float(v)

        @property
        def echo_feedback(self): return self._echo.feedback
        @echo_feedback.setter
        def echo_feedback(self, v): self._echo.feedback = float(v)

        @property
        def reverb_room_size(self): return self._reverb.room_size
        @reverb_room_size.setter
        def reverb_room_size(self, v): self._reverb.room_size = float(v)

        @property
        def reverb_damping(self): return self._reverb.damping
        @reverb_damping.setter
        def reverb_damping(self, v): self._reverb.damping = float(v)

    # Expose cutoff/delay as simple attributes (giao diện đơn giản cho GUI)
    @property
    def lowpass_cutoff(self):
        return self._lowpass.cutoff_hz

    @lowpass_cutoff.setter
    def lowpass_cutoff(self, v):
        self._lowpass.cutoff_hz = float(v)

    @property
    def highpass_cutoff(self):
        return self._highpass.cutoff_hz

    @highpass_cutoff.setter
    def highpass_cutoff(self, v):
        self._highpass.cutoff_hz = float(v)

    @property
    def echo_delay(self):
        return self._echo.delay_sec

    @echo_delay.setter
    def echo_delay(self, v):
        self._echo.delay_sec = float(v)

    @property
    def echo_feedback(self):
        return self._echo.feedback

    @echo_feedback.setter
    def echo_feedback(self, v):
        self._echo.feedback = float(v)

    @property
    def reverb_room_size(self):
        return self._reverb.room_size

    @reverb_room_size.setter
    def reverb_room_size(self, v):
        self._reverb.room_size = float(v)

    @property
    def reverb_damping(self):
        return self._reverb.damping

    @reverb_damping.setter
    def reverb_damping(self, v):
        self._reverb.damping = float(v)

    # ── Main process ──────────────────────────────────────────────────────────

    def process(self, data: np.ndarray) -> np.ndarray:
        """
        Áp dụng toàn bộ effects đang bật theo thứ tự.
        data: float32 stereo array [N, 2]
        """
        out = self.eq.process(data)

        if self.lowpass_enabled:
            out = self._lowpass.process(out)
        if self.highpass_enabled:
            out = self._highpass.process(out)
        if self.echo_enabled:
            out = self._echo.process(out)
        if self.reverb_enabled:
            out = self._reverb.process(out)

        return out.astype(np.float32)

    def reset_state(self):
        """Reset toàn bộ filter state – gọi khi load file mới hoặc seek."""
        self.eq.reset()
        self._lowpass.reset()
        self._highpass.reset()
        self._echo.reset()
        self._reverb.reset()
