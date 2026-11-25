# -*- coding: utf-8 -*-
"""v1（いまのレッスン版の右手）を正解として、声の高さの生の読みがどれだけ合うか・入りがどれだけずれるかを測る"""
import sys, json, numpy as np
from collections import Counter
D, R = sys.argv[1], sys.argv[2]; O = 2; fps = 22050 / 256
s = open(R + "/lesson-data-overdrive.js").read(); v1 = json.loads(s[s.index("]=") + 2:s.rindex(";")])
top = {}
for a, p, l, h in v1["notes"]:
    if h == 1: top[a] = max(top.get(a, (0, 0)), (p, l))
ref = sorted((a, p, l) for a, (p, l) in top.items())
bt = np.load(D + "/bt.npy"); t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
f = np.load(D + "/f0_vocals.npy"); m = 69 + 12 * np.log2(f / 440.0); on = np.load(D + "/on_vocals.npy"); rms = np.load(D + "/rms_vocals.npy")
dev = []; cover = []; rows = []
for a, p, l in ref:
    i0, i1 = int(t_of(a + 0.12) * fps), int(t_of(a + l - 0.05) * fps); seg = m[i0:i1]; ok = seg[~np.isnan(seg)]
    cover.append(len(ok) / max(1, len(seg)))
    if len(ok) >= 3:
        d = (np.median(ok) - p + 6) % 12 - 6; dev.append(d); rows.append((a, p, l, d))
dev = np.array(dev); cover = np.array(cover)
print("v1 の音", len(ref), "／声が半分以上ある音", int((cover >= 0.5).sum()), "／声がほぼ無い音", int((cover < 0.1).sum()))
print("生の高さ − v1（半音）の分布:", np.histogram(dev, bins=np.arange(-3.25, 3.3, 0.5))[0].tolist(), "区切り -3.25〜+3.25 を 0.5 刻み")
core = dev[np.abs(dev) < 0.5]; print("±0.5以内", len(core), "/", len(dev), "中央値 %+.2f" % np.median(core))
off = float(np.median(core))
r = np.round(dev - off); print("調律を引いたあとの丸め:", sorted(Counter(r.astype(int)).items()))
# 入り: v1 の音の頭の前後で、声の立ち上がりの山・声の出はじめがどこにあるか
th = np.percentile(on, 75)
lag_on = []; strength = []
for a, p, l in ref:
    c = int(t_of(a) * fps); w = int(0.25 * (t_of(a + 1) - t_of(a)) * fps) + 1; seg = on[c - w:c + w + 1]
    if len(seg) < 3: continue
    k = int(np.argmax(seg)); strength.append(seg[k] / th); lag_on.append((k - w) / fps / (t_of(a + 1) - t_of(a)))
strength = np.array(strength); lag_on = np.array(lag_on)
print("v1 の音の頭±16分にある立ち上がりの強さ（75パーセント点の何倍か）: 中央値 %.1f / 1.5倍未満 %d / 2倍未満 %d / 3倍未満 %d / 全 %d" % (np.median(strength), (strength < 1.5).sum(), (strength < 2).sum(), (strength < 3).sum(), len(strength)))
print("立ち上がりの山の位置 − v1 の頭（拍）: 中央値 %+.3f  四分位 %+.3f 〜 %+.3f" % (np.median(lag_on[strength > 2]), np.percentile(lag_on[strength > 2], 25), np.percentile(lag_on[strength > 2], 75)))
# 同じ高さの連打: v1 で前の音と同じ高さ・切れ目なし のとき、立ち上がりはあるか
rep = [strength[i] for i in range(1, len(ref)) if i < len(strength) and ref[i][1] == ref[i - 1][1] and abs(ref[i - 1][0] + ref[i - 1][2] - ref[i][0]) < 1e-6]
print("同じ高さの連打", len(rep), "か所の立ち上がりの強さ: 中央値 %.1f / 1.5倍以上 %d / 2倍以上 %d" % (np.median(rep), sum(x >= 1.5 for x in rep), sum(x >= 2 for x in rep)))
json.dump({"ref": ref, "off": off}, open(D + "/ref.json", "w"))
