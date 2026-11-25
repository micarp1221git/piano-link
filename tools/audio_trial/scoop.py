# -*- coding: utf-8 -*-
"""notes3 に「しゃくり」のまとめだけを足す: 短い音のすぐ後ろに1〜2半音上の音が続き、その境目に声の立ち上がりが無い（＝同じ言葉のまま高さだけ上がった）なら、前の音を後ろの高さにまとめる"""
import sys, json, itertools, numpy as np
D = sys.argv[1]; O = 2; fps = 22050 / 256
bt = np.load(D + "/bt.npy"); t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
R = json.load(open(D + "/ref.json")); ref = R["ref"]; f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0) - R["off"]
on = np.load(D + "/on_vocals.npy"); base = np.percentile(on, 75)
truth = {}
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if len(seg) and np.mean(~np.isnan(seg)) >= 0.5: truth[round(a * 2) / 2] = p % 12
vo = json.load(open(D + "/notes3.json"))["vo"]
def score(ns):
    m = {n[0]: n[1] for n in ns}
    return sum(1 for a, p in truth.items() if a in m and m[a] % 12 == p), sum(1 for a in truth if a in m), len(m)
def run(maxlen, thr, minnext, updown):
    out = []; i = 0; n = 0
    while i < len(vo):
        a, p, l = vo[i]
        if i + 1 < len(vo):
            a2, p2, l2 = vo[i + 1]; d = p2 - p
            ok = (1 <= d <= 2) or (updown and -2 <= d <= -1)
            if l <= maxlen and abs(a + l - a2) < 0.3 and ok and l2 >= minnext:
                k = int(t_of(a2) * fps); pk = on[max(0, k - 5):k + 6].max() / base
                if pk < thr: out.append([a, p2, round(a2 + l2 - a, 2)]); i += 2; n += 1; continue
        out.append(vo[i]); i += 1
    return out, n
print("正解", len(truth), "／3回目", score(vo), "／立ち上がりの基準", round(float(base), 3))
rows = []
for maxlen, thr, minnext, updown in itertools.product((0.5, 0.75, 1.0), (1.0, 1.5, 2.0, 3.0, 99), (0.5, 1.0, 1.5), (0, 1)):
    ns, n = run(maxlen, thr, minnext, updown); rows.append(score(ns) + (n, maxlen, thr, minnext, updown))
rows.sort(reverse=True)
for r in rows[:12]: print("合う %d 位置 %d 読んだ %d まとめた %d ／前の長さ≤%.2f 立ち上がり<%.1f 後ろの長さ≥%.1f 下がりも %d" % r)
b = rows[0]; json.dump({"vo": run(*b[4:])[0]}, open(D + "/notes4.json", "w"))
