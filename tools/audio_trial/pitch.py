# -*- coding: utf-8 -*-
import sys, warnings, numpy as np, librosa
warnings.filterwarnings("ignore")
D = sys.argv[1]; sr = 22050; hop = 256
for name, lo, hi, thr in (("bass", 38, 260, 0.01), ("vocals", 150, 900, 0.008)):
    y, _ = librosa.load(D + "/" + name + ".wav", sr=sr)
    f0, vf, vp = librosa.pyin(y, fmin=lo, fmax=hi, sr=sr, frame_length=2048 if name == "vocals" else 4096, hop_length=hop, resolution=0.05)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0][:len(f0)]
    f0 = np.where(vf & (rms > thr), f0, np.nan)
    on = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    np.save(D + "/f0_" + name + ".npy", f0); np.save(D + "/rms_" + name + ".npy", rms); np.save(D + "/on_" + name + ".npy", on)
    m = 69 + 12 * np.log2(f0 / 440); v = m[~np.isnan(m)]
    print(name, "voiced", len(v), "of", len(f0), "median", round(float(np.median(v)), 1), "tuning hist", np.histogram((v + 0.5) % 1 - 0.5, bins=10, range=(-0.5, 0.5))[0].tolist())
