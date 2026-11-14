import numpy as np, wave
SR = 48000; DUR = 154.5; N = int(SR * DUR); B = 0.75           # 80 BPM
mus = np.zeros(N); sfx = np.zeros(N)
nota = lambda m: 440 * 2 ** ((m - 69) / 12)
def env(n, a, d): x = np.arange(n) / SR; return np.minimum(1, x / a) * np.exp(-x / d)
def poner(buf, ini, sig, g=1.0):
    i = int(ini * SR); j = min(N, i + len(sig))
    if i < N: buf[i:j] += g * sig[:j - i]
AC = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]; BJ = [33, 29, 36, 31]
comp = 4 * B
for c in range(int(DUR / comp) + 1):
    ini = c * comp; ac = AC[c % 4]; n = int((comp + .4) * SR); x = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * nota(m) * x) + .25 * np.sin(2 * np.pi * nota(m + 12) * x * 1.002) for m in ac)
    poner(mus, ini, s * np.minimum(1, x / .6) * np.minimum(1, (comp + .4 - x) / .5), .035)
    n = int(comp * SR); x = np.arange(n) / SR                       # bajo largo
    poner(mus, ini, np.sin(2 * np.pi * nota(BJ[c % 4]) * x) * np.minimum(1, x / .05) * np.exp(-x / 1.6), .13)
    for k in range(8):                                              # arpegio suave en corcheas
        t0 = ini + k * B / 2
        if t0 < 4 or t0 > 148: continue
        m = ac[[0, 1, 2, 1, 0, 2, 1, 2][k]] + 12; n = int(.5 * SR); x = np.arange(n) / SR
        poner(mus, t0, np.sin(2 * np.pi * nota(m) * x) * env(n, .004, .16), .035)
    for k in range(4):                                              # pulso grave muy suave
        t0 = ini + k * B
        if t0 < 4 or t0 > 148: continue
        n = int(.3 * SR); x = np.arange(n) / SR; f = 45 + 60 * np.exp(-x / .03)
        poner(mus, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / .1), .22 if k == 0 else .10)
def tic(t, m=69, g=.06):
    n = int(.25 * SR); x = np.arange(n) / SR; poner(sfx, t, np.sin(2 * np.pi * nota(m) * x) * env(n, .002, .07), g)
for t in [4, 10, 16, 22]: tic(t, 64)
for k in range(7):
    t = 29 + k * 8.5; tic(t, 64); tic(t + 1.2, 76 if k < 4 else 72, .05)
for t in [88.5, 97.5, 106.5, 117.5, 130.5]: tic(t, 64)
for i in range(3): tic(117.5 + .6 + i * 3.2, 72, .05)
for i in range(4): tic(130.5 + .8 + i * 3.6, 72, .05)
for i in range(5): tic(106.5 + .8 + i * 1.5, 69 + [0, 3, 7, 3, 0][i], .05)
for t, m in [(29 + 4 * 8.5 + 1.2, 33), (29 + 4 * 8.5 + 1.55, 28)]:   # muerde el cebo
    n = int(.8 * SR); x = np.arange(n) / SR; poner(sfx, t, np.tanh(2 * np.sin(2 * np.pi * nota(m) * x)) * env(n, .003, .22), .26)
n = int(5 * SR); x = np.arange(n) / SR
poner(mus, 148.5, sum(np.sin(2 * np.pi * nota(m) * x) for m in [45, 57, 60, 64, 69]) * env(n, .02, 1.6), .06)
mix = mus + sfx; fade = np.ones(N); k = int(2.5 * SR); fade[-k:] = np.linspace(1, 0, k) ** 1.5; fade[:int(.3 * SR)] = np.linspace(0, 1, int(.3 * SR))
mix = np.tanh(1.1 * mix) * fade; mix /= np.abs(mix).max() / .85
with wave.open("musica.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.stack([mix, mix], 1) * 32767).astype(np.int16).tobytes())
