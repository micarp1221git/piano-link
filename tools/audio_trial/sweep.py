# -*- coding: utf-8 -*-
"""歌の読み方の設定を変えて、v1（いまのレッスン版の右手）との合い具合を点数で比べる"""
import sys, json, re, itertools, numpy as np
D = sys.argv[1]; O = 2; METER = 4; fps = 22050 / 256
bt = np.load(D + "/bt.npy"); pos = lambda t: np.interp(t, bt, np.arange(len(bt))) - O
R = json.load(open(D + "/ref.json")); ref = [tuple(x) for x in R["ref"]]
f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0) - R["off"]; ON = np.load(D + "/on_vocals.npy"); TH = np.percentile(ON, 75)
t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
# 正解のうち、声がある音だけ
truth = {}
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if len(seg) and np.mean(~np.isnan(seg)) >= 0.5: truth[round(a * 4) / 4] = p % 12
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
def extract(thr, early, grid16, lo, hi, minfr, onset_snap):
    pk = [i for i in range(2, len(ON) - 2) if ON[i] > TH * thr and ON[i] == ON[i - 2:i + 3].max()]; pks = set(pk); pka = np.array(pk)
    segs = []; cur = None
    for i in range(len(M)):
        x = M[i]
        if np.isnan(x):
            if cur and i - cur["e"] > 3: segs.append(cur); cur = None
            continue
        if cur and abs(x - np.median(cur["v"])) < 0.7 and not (i in pks and i - cur["s"] >= minfr): cur["v"].append(x); cur["e"] = i
        else:
            fresh = cur is None
            if cur: segs.append(cur)
            cur = {"s": i, "e": i, "v": [x], "fresh": fresh}
    if cur: segs.append(cur)
    out = []
    for c in segs:
        n = len(c["v"])
        if n < minfr: continue
        body = c["v"][int(n * lo):max(int(n * lo) + 1, int(n * hi))]; p = int(round(float(np.median(body))))
        a = float(pos(c["s"] / fps)) + (early if c["fresh"] else 0.03)
        if onset_snap and len(pka):   # 近くに立ち上がりの山があれば、そこを入りにする
            j = int(np.argmin(np.abs(pka - (c["s"] + 4)))); pa = float(pos(pka[j] / fps))
            if abs(pa - a) <= 0.3: a = pa
        e8 = round(a * 2) / 2; qa = e8 if (not grid16 or abs(a - e8) <= 0.15) else round(a * 4) / 4
        b = float(pos((c["e"] + 1) / fps))
        if out and out[-1][0] == qa:
            if b - a > out[-1][3]: out[-1] = [qa, p, max(qa + 0.25, round(b * 4) / 4) - qa, b - a]
            continue
        out.append([qa, p, max(qa + 0.25, round(b * 4) / 4) - qa, b - a])
    return out
def score(ns):
    mine = {n[0]: n[1] % 12 for n in ns}
    hit = sum(1 for a, p in truth.items() if mine.get(a) == p); pos_only = sum(1 for a in truth if a in mine)
    return hit, pos_only, len(mine)
print("正解の音（声がある所）", len(truth))
rows = []
for thr, early, g16, lo, minfr, snap in itertools.product((1.2, 1.5, 2.0, 3.0), (0.14,), (True, False), (0.2, 0.35), (5, 7), (False, True)):
    ns = extract(thr, early, g16, lo, 0.95, minfr, snap); h, po, n = score(ns)
    rows.append((2 * h / (n + len(truth)), h, po, n, thr, g16, lo, minfr, snap))
rows.sort(reverse=True)
print("点数  位置も高さも合う / 位置が合う / 読んだ音  |  立ち上がりの倍率 16分あり 高さの範囲 最短 入りを山に寄せる")
for r in rows[:8] + rows[-3:]: print("%.3f  %3d / %3d / %3d  |  %s %s %s %s %s" % r)
best = rows[0]; json.dump({"thr": best[4], "g16": best[5], "lo": best[6], "minfr": best[7], "snap": best[8]}, open(D + "/best.json", "w"))
