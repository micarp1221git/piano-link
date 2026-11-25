# -*- coding: utf-8 -*-
import sys, json, warnings, numpy as np, librosa
warnings.filterwarnings("ignore")
D = sys.argv[1]; METER = 4; BPM = 148.0
sr = 22050; hop = 256; fps = sr / hop
dr, _ = librosa.load(D + "/drums.wav", sr=sr); ba, _ = librosa.load(D + "/bass.wav", sr=sr); mo, _ = librosa.load(D + "/mono.wav", sr=sr)
oenv = librosa.onset.onset_strength(y=dr + 0.5 * mo, sr=sr, hop_length=hop)
tempo, bf = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, start_bpm=BPM, tightness=200)
bt = list(librosa.frames_to_time(bf, sr=sr, hop_length=hop)); ibi = float(np.median(np.diff(bt)))
d = np.diff(bt); print("tempo", float(np.atleast_1d(tempo)[0]), "ibi", ibi, "bpm_med", 60 / ibi, "n", len(bt), "first", bt[0], "last", bt[-1], "dur", len(mo) / sr)
print("ibi out of 15%:", int(np.sum(np.abs(d - ibi) > 0.15 * ibi)), [round(bt[i], 1) for i in np.where(np.abs(d - ibi) > 0.15 * ibi)[0]][:30])
while bt[0] - ibi > 0: bt.insert(0, bt[0] - ibi)
while bt[-1] + ibi < len(mo) / sr: bt.append(bt[-1] + ibi)
bt = np.array(bt); N = len(bt)
# 小節の頭: キック(ドラムの低い所)とベースの立ち上がり
def lowon(y, lo, hi):
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)); fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
    e = S[(fr > lo) & (fr < hi)].sum(0); return np.maximum(0, np.diff(np.log1p(e), prepend=0))
k = lowon(dr, 30, 120); b = lowon(ba, 30, 250)
def pk(a, t, w=0.05):
    i0 = max(0, int((t - w) * fps)); i1 = min(len(a), int((t + w) * fps) + 1); return float(a[i0:i1].max()) if i1 > i0 else 0.0
r = np.array([pk(k, t) / (k.max() + 1e-9) + pk(b, t) / (b.max() + 1e-9) for t in bt])
for ph in range(4): print("phase", ph, round(float(r[ph::4].mean()), 4), "kick", round(float(np.mean([pk(k, t) for t in bt[ph::4]])), 3), "bass", round(float(np.mean([pk(b, t) for t in bt[ph::4]])), 3))
# スネア(中高域)の位置も: 2・4拍目に来るはず
s = lowon(dr, 1500, 6000)
for ph in range(4): print("snare phase", ph, round(float(np.mean([pk(s, t) for t in bt[ph::4]])), 3))
np.save(D + "/bt.npy", bt)
