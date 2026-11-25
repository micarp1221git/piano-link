# -*- coding: utf-8 -*-
"""3回目の読み（notes3）が正解と違う所の内訳: 何半音ずれか・声の線は正解からどれだけ離れているか"""
import sys, json, collections, numpy as np
D = sys.argv[1]; O = 2; fps = 22050 / 256
bt = np.load(D + "/bt.npy"); t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
R = json.load(open(D + "/ref.json")); ref = R["ref"]; f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0) - R["off"]
print("off", R["off"])
vo = json.load(open(D + "/notes3.json"))["vo"]; base = {n[0]: n[1] for n in vo}
h = collections.Counter(); dev = []; miss = 0; n = 0; rows = []
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if not len(seg) or np.mean(~np.isnan(seg)) < 0.5: continue
    q = round(a * 2) / 2; n += 1; s = seg[~np.isnan(seg)]
    med = float(np.median(s)); d = ((med - p + 6) % 12) - 6; dev.append(d)
    if q not in base: miss += 1; continue
    e = ((base[q] - p + 6) % 12) - 6; h[e] += 1
    if e: rows.append((a, p, base[q], round(med, 2), round(float(np.percentile(s, 25)), 2), round(float(np.percentile(s, 85)), 2), l))
print("正解", n, "位置なし", miss, "ずれの内訳（半音: 件数）", sorted(h.items()))
dev = np.array(dev); print("声の線の中央値 − 正解: 平均 %.2f 中央 %.2f ／|ずれ|<0.5 が %d ／ 0.5〜1.5 が %d ／ それ以上 %d" % (dev.mean(), np.median(dev), (abs(dev) < 0.5).sum(), ((abs(dev) >= 0.5) & (abs(dev) < 1.5)).sum(), (abs(dev) >= 1.5).sum()))
for r in rows[:40]: print(r)
