"""Kodla üretilen ses efektleri ve yedek fon müziği (yapay zekâ ve hazır ses kütüphanesi yok; numpy ile sentez).
Tüm sesler 48 kHz mono float32 dizi döndürür."""
import numpy as np

SR = 48000


def _t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.004, r=0.08, curve=4.0):
    """Hızlı atak, üstel sönüm zarfı."""
    x = np.ones(n)
    na = max(1, int(SR * a))
    x[:na] = np.linspace(0, 1, na)
    tail = np.arange(n - na) / SR
    x[na:] = np.exp(-tail / max(r, 1e-4) * (curve / 4))
    return x


def pop(pitch=880.0, d=0.12, gain=0.55):
    """Yuvarlak 'pop': hızla düşen perdeli sinüs + biraz gürültü tıkı."""
    t = _t(d)
    f = pitch * (1.0 + 1.6 * np.exp(-t * 60))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env(len(t), 0.002, 0.035)
    click = np.random.default_rng(1).normal(0, 1, len(t)) * env(len(t), 0.0005, 0.004) * 0.25
    return (s + click) * gain


def tick(d=0.05, gain=0.35):
    t = _t(d)
    s = np.sin(2 * np.pi * 2200 * t) * env(len(t), 0.0005, 0.012)
    return s * gain


def ding(base=1318.5, d=0.9, gain=0.42):
    """Doğru cevap çanı: iki armonik, uzun sönüm."""
    t = _t(d)
    s = (np.sin(2 * np.pi * base * t) + 0.45 * np.sin(2 * np.pi * base * 2.01 * t) + 0.2 * np.sin(2 * np.pi * base * 3.02 * t))
    s2 = np.sin(2 * np.pi * base * 1.5 * t) * 0.6
    out = s * env(len(t), 0.002, 0.35) + np.concatenate([np.zeros(int(SR * 0.07)), s2[: len(t) - int(SR * 0.07)]]) * env(len(t), 0.002, 0.3)
    return out / 2.2 * gain


def buzz(d=0.32, gain=0.32):
    """Yanlış cevap: kısa, kaba testere dişi 'bzzt'."""
    t = _t(d)
    f = 155
    saw = 2 * ((t * f) % 1) - 1
    saw2 = 2 * ((t * f * 1.5) % 1) - 1
    s = (saw + 0.5 * saw2) * env(len(t), 0.003, 0.12)
    # basit alçak geçiren
    k = np.ones(18) / 18
    s = np.convolve(s, k, mode='same')
    return s * gain


def whoosh(d=0.38, gain=0.28, up=True):
    """Geçiş sesi: bant geçiren beyaz gürültü süpürmesi."""
    t = _t(d)
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 1, len(t))
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(len(noise), 1 / SR)
    center = 900 if up else 2400
    spec *= np.exp(-((freqs - center) / 1400) ** 2)
    s = np.fft.irfft(spec, len(noise))
    shape = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 1.6
    s = s / (np.abs(s).max() + 1e-9) * shape
    return s * gain


def type_clicks(n=6, gap=0.07, gain=0.18):
    out = np.zeros(int(SR * (n * gap + 0.05)))
    for i in range(n):
        c = tick(0.02, 1.0) * (0.7 + 0.3 * ((i * 37) % 5) / 5)
        st = int(SR * i * gap)
        out[st:st + len(c)] += c
    return out * gain


def mix(cues, duration):
    """cues: [(saniye, dizi), ...] → tek kanal karışım."""
    out = np.zeros(int(SR * duration) + SR)
    for t, s in cues:
        st = int(SR * t)
        end = min(len(out), st + len(s))
        out[st:end] += s[: end - st]
    return out[: int(SR * duration)]


def backing_track(duration, bpm=96, seed=3, gain=0.22):
    """Yedek fon müziği (Instagram müziği eklenemezse): yumuşak akorlar, kick, snare, hi-hat. Döngüye uygun."""
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    n = int(SR * duration)
    out = np.zeros(n + SR)
    # akorlar (Fmaj7 - Em7 - Dm7 - Cmaj7), elektrik piyano benzeri
    chords = [[174.6, 220.0, 261.6, 329.6], [164.8, 196.0, 246.9, 293.7], [146.8, 174.6, 220.0, 261.6], [130.8, 164.8, 196.0, 246.9]]
    bar = beat * 4
    t_chord = _t(bar)
    for i in range(int(duration / bar) + 1):
        ch = chords[i % 4]
        s = sum(np.sin(2 * np.pi * f * t_chord) * (1 + 0.3 * np.sin(2 * np.pi * f * 2 * t_chord)) for f in ch)
        s *= env(len(t_chord), 0.01, 1.6) * 0.12
        st = int(SR * i * bar)
        out[st:st + len(s)] += s[: max(0, min(len(s), len(out) - st))]
    kick_t = _t(0.25)
    kick = np.sin(2 * np.pi * (55 + 90 * np.exp(-kick_t * 30)) * kick_t) * env(len(kick_t), 0.002, 0.09) * 0.9
    snare_t = _t(0.2)
    snare = rng.normal(0, 1, len(snare_t)) * env(len(snare_t), 0.001, 0.05) * 0.35
    hat_t = _t(0.05)
    hat = rng.normal(0, 1, len(hat_t))
    hat = np.diff(hat, prepend=0) * env(len(hat_t), 0.0005, 0.01) * 0.18
    for b in range(int(duration / beat) + 1):
        st = int(SR * b * beat)
        for snd, cond in ((kick, b % 4 in (0, 2)), (snare, b % 4 in (1, 3))):
            if cond:
                out[st:st + len(snd)] += snd[: max(0, min(len(snd), len(out) - st))]
        for half in (0, 0.5):
            hs = int(SR * (b + half) * beat)
            out[hs:hs + len(hat)] += hat[: max(0, min(len(hat), len(out) - hs))]
    k = np.ones(9) / 9
    out = np.convolve(out, k, mode='same')
    return out[:n] / (np.abs(out[:n]).max() + 1e-9) * gain


# ---------- v4: üretim kılavuzu §5.9 tarifleri ----------

def _lp(x, cutoff):
    """Tek kutuplu alçak geçiren."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def pop2(pitch=1.0, gain=0.5):
    """Kart ve hap pop'u: 900→250 Hz üstel kayan sinüs + 1 ms gürültü tıkı, 25 ms sönüm (90 ms)."""
    t = _t(0.09)
    f = 250 + (900 * pitch - 250) * np.exp(-t / 0.012)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.025)
    click = np.random.default_rng(5).normal(0, 1, len(t)) * (t < 0.001) * 0.6
    return (s + click) * gain


def chime(gain=0.42):
    """Doğru cevap: çan kısmileri ×[1, 2, 2.76, 5.4, 8.93], E6 sonra 80 ms arayla B6; τ = 0.6/√oran."""
    d = 1.0
    t = _t(d)
    out = np.zeros(len(t) + int(SR * 0.08))
    for k, base in enumerate((1318.5, 1975.5)):
        s = np.zeros(len(t))
        for r, a in zip((1, 2.0, 2.76, 5.40, 8.93), (1, .5, .35, .18, .08)):
            s += a * np.sin(2 * np.pi * base * r * t) * np.exp(-t / (0.6 / np.sqrt(r)))
        st = int(SR * 0.08 * k)
        out[st:st + len(s)] += s * (1 if k == 0 else 0.8)
    return out / np.abs(out).max() * gain


def buzz2(gain=0.36):
    """Hata: iki bant sınırlı kare ton 220→165 Hz, 130 ms'lik, 30 Hz tremolo, 3 kHz alçak geçiren (300 ms)."""
    parts = []
    for f0 in (220, 165):
        t = _t(0.13)
        sq = np.zeros(len(t))
        for h in (1, 3, 5, 7, 9, 11):
            sq += np.sin(2 * np.pi * f0 * h * t) / h
        sq *= 1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * 30 * t))
        sq *= np.minimum(1, t / 0.004) * np.minimum(1, (0.13 - t) / 0.01)
        parts.append(sq)
    s = np.concatenate([parts[0], np.zeros(int(SR * 0.02)), parts[1]])
    s = _lp(s, 3000)
    return s / np.abs(s).max() * gain


def tick2(gain=0.25, seed=0):
    """Saniye ve liste tıkı: 1,5 ms gürültü (yüksek geçiren) + 3,2 kHz rezonatör, τ 8 ms (30 ms)."""
    rng = np.random.default_rng(seed)
    t = _t(0.03)
    n = rng.normal(0, 1, len(t)) * (t < 0.0015)
    n = np.diff(n, prepend=0)
    f = 3200 * (1 + rng.uniform(-0.1, 0.1))
    res = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.008)
    s = n * 0.5 + res
    return s / np.abs(s).max() * gain


def whoosh2(d=0.38, gain=0.26, up=True):
    """Geçiş: beyaz gürültü, 300→3500 Hz süpüren bant geçiren; şişme %65'te tepe yapar."""
    t = _t(d)
    rng = np.random.default_rng(11)
    noise = rng.normal(0, 1, len(t))
    f = 300 * (3500 / 300) ** (t / d) if up else 3500 * (300 / 3500) ** (t / d)
    # durum değişkenli bant geçiren
    low = band = 0.0
    out = np.zeros(len(t))
    q = 1.8
    for i in range(len(t)):
        fc = 2 * np.sin(np.pi * min(f[i], SR / 6) / SR)
        high = noise[i] - low - band / q
        band += fc * high
        low += fc * band
        out[i] = band
    shape = np.where(t < 0.65 * d, (t / (0.65 * d)) ** 2, ((d - t) / (0.35 * d)) ** 1.5)
    out *= shape
    return out / (np.abs(out).max() + 1e-9) * gain


def boing(gain=0.3):
    """Goof sıçraması: 180→420 Hz, 8 Hz vibrato (120 ms)."""
    t = _t(0.12)
    f = 180 + 240 * (t / 0.12) + 12 * np.sin(2 * np.pi * 8 * t)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.06)
    return s * gain


def stamp(gain=0.45):
    """Damga: 90 Hz gümleme (τ 60 ms) + gürültü tıkı (150 ms)."""
    t = _t(0.15)
    s = np.sin(2 * np.pi * 90 * t) * np.exp(-t / 0.06)
    click = np.random.default_rng(3).normal(0, 1, len(t)) * np.exp(-t / 0.003) * 0.5
    return (s + click) / 1.3 * gain


def backing_120(duration, seed=0, gain=0.3):
    """Yedek fon müziği, 120 BPM (bir vuruş = 15 kare): akor pedi, bas, kick, clap, hi-hat. Tohuma göre iki ilerleme."""
    rng = np.random.default_rng(seed)
    bpm = 120
    beat = 60 / bpm
    n = int(SR * duration)
    out = np.zeros(n + SR)
    progs = [
        [[174.6, 220.0, 261.6, 329.6], [164.8, 196.0, 246.9, 293.7], [146.8, 174.6, 220.0, 261.6], [130.8, 164.8, 196.0, 246.9]],
        [[130.8, 164.8, 196.0, 246.9], [110.0, 130.8, 164.8, 196.0], [174.6, 220.0, 261.6, 329.6], [196.0, 246.9, 293.7, 349.2]],
    ]
    chords = progs[seed % 2]
    bar = beat * 4
    tb = _t(bar)
    for i in range(int(duration / bar) + 2):
        ch = chords[i % 4]
        pad = sum(np.sin(2 * np.pi * f * tb + 0.3 * np.sin(2 * np.pi * 0.5 * tb)) for f in ch) * 0.10
        pad *= np.minimum(1, tb / 0.03) * np.exp(-tb / 2.5)
        # bas: kök nota, sekizlik
        bass = np.zeros(len(tb))
        for k in range(8):
            st = int(SR * k * beat / 2)
            tt = _t(beat / 2 * 0.9)
            b = np.sin(2 * np.pi * ch[0] / 2 * tt) * np.exp(-tt / 0.12) * 0.35
            bass[st:st + len(b)] += b[: max(0, min(len(b), len(bass) - st))]
        s = pad + bass
        st = int(SR * i * bar)
        seg = s[: max(0, min(len(s), len(out) - st))]
        out[st:st + len(seg)] += seg
    kt = _t(0.25)
    kick = np.sin(2 * np.pi * (50 + 110 * np.exp(-kt * 35)) * kt) * np.exp(-kt / 0.09) * 0.9
    ct = _t(0.18)
    clap = rng.normal(0, 1, len(ct)) * np.exp(-ct / 0.045) * 0.32
    ht = _t(0.04)
    hat = np.diff(rng.normal(0, 1, len(ht)), prepend=0) * np.exp(-ht / 0.01) * 0.12
    for b in range(int(duration / beat) + 2):
        st = int(SR * b * beat)
        for snd, cond in ((kick, True), (clap, b % 2 == 1)):
            if cond:
                seg = snd[: max(0, min(len(snd), len(out) - st))]
                out[st:st + len(seg)] += seg
        for half in (0.5,):
            hs = int(SR * (b + half) * beat)
            seg = hat[: max(0, min(len(hat), len(out) - hs))]
            out[hs:hs + len(seg)] += seg
    out = out[:n]
    return out / (np.abs(out).max() + 1e-9) * gain
