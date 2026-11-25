# -*- coding: utf-8 -*-
"""歌の入りの偏りと、その他の音（リード）の読みやすさを測る"""
import sys, warnings, numpy as np, librosa
warnings.filterwarnings("ignore")
D = sys.argv[1]; sr = 22050; hop = 256; fps = sr / hop; O = 2
bt = np.load(D + "/bt.npy")
pos = lambda t: np.interp(t, bt, np.arange(len(bt))) - O
for name in ("vocals", "bass"):
    f = np.load(D + "/f0_" + name + ".npy"); on = np.load(D + "/on_" + name + ".npy")
    v = ~np.isnan(f); starts = [i for i in range(1, len(v)) if v[i] and not v[i - 3:i].any()] if name == "vocals" else []
    # 立ち上がりの山
    th = np.percentile(on, 75) * 3; pk = [i for i in range(2, len(on) - 2) if on[i] > th and on[i] == on[i - 2:i + 3].max()]
    for label, idx in (("声の出はじめ", starts), ("立ち上がりの山", pk)):
        if not idx: continue
        p = pos(np.array(idx) / fps); d = (p * 2 + 0.5) % 1 - 0.5   # 8分のマス目からのずれ（8分=1）
        h = np.histogram(d, bins=10, range=(-0.5, 0.5))[0]
        ang = np.angle(np.mean(np.exp(2j * np.pi * d))) / (2 * np.pi)
        print(name, label, len(idx), "8分からのずれの分布", h.tolist(), "平均のずれ(8分=1) %+.3f = %+.3f拍" % (ang, ang / 2))
# その他の音: 高い所の旋律が読めるか
if not __import__("os").path.exists(D + "/f0_other.npy"):
    y, _ = librosa.load(D + "/other.wav", sr=sr)
    f0, vf, vp = librosa.pyin(y, fmin=180, fmax=1400, sr=sr, frame_length=2048, hop_length=hop, resolution=0.05)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0][:len(f0)]
    np.save(D + "/f0_other.npy", np.where(vf, f0, np.nan)); np.save(D + "/vp_other.npy", vp); np.save(D + "/rms_other.npy", rms)
    np.save(D + "/on_other.npy", librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop))
f = np.load(D + "/f0_other.npy"); m = 69 + 12 * np.log2(f / 440); fv = np.load(D + "/f0_vocals.npy")
NN = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
print("その他: 読めた割合", round(float(np.mean(~np.isnan(m))), 2))
for bar in range(1, 13):
    a, b = int(np.interp(O + (bar - 1) * 4, np.arange(len(bt)), bt) * fps), int(np.interp(O + bar * 4, np.arange(len(bt)), bt) * fps)
    seg = m[a:b]; out = []; cur = None
    for i, x in enumerate(seg):
        if np.isnan(x):
            if cur and i - cur[1] > 2: out.append(cur); cur = None
            continue
        if cur and abs(x - np.median(cur[2])) < 0.7: cur[2].append(x); cur[1] = i
        else:
            if cur: out.append(cur)
            cur = [i, i, [x]]
    if cur: out.append(cur)
    print("%2d 声%3d%% |" % (bar, 100 * np.mean(~np.isnan(fv[a:b]))), " ".join("%s%d@%.2f(%.2f)" % (NN[int(round(np.median(c[2]))) % 12], int(round(np.median(c[2]))) // 12 - 1, c[0] / (b - a) * 4, (c[1] - c[0] + 1) / (b - a) * 4) for c in out if c[1] - c[0] >= 5))
