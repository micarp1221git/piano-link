# -*- coding: utf-8 -*-
"""basic-pitch の読みを8分のマス目に当てて、レッスン版（v1）の395音と突き合わせる"""
import sys, json, numpy as np
D = sys.argv[1]; O = 2; fps = 22050 / 256
bt = np.load(D + "/bt.npy"); pos = lambda t: np.interp(t, bt, np.arange(len(bt))) - O; t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
ref = json.load(open(D + "/ref.json"))["ref"]; f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0)
truth = {}
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if len(seg) and np.mean(~np.isnan(seg)) >= 0.5: truth[round(a * 2) / 2] = p % 12
bp = json.load(open(D + "/notes_bp.json")); rows = []
for key, ev in bp.items():
    for shift in (-0.1, -0.05, 0, 0.05, 0.1):
        mine = {}; w = {}
        for s, e, p, a in ev:
            q = round((float(pos(s)) + shift) * 2) / 2; score = (e - s) * a
            if q not in mine or score > w[q]: mine[q] = p % 12; w[q] = score
        hit = sum(1 for a, p in truth.items() if mine.get(a) == p); po = sum(1 for a in truth if a in mine)
        rows.append((2 * hit / (len(mine) + len(truth)), hit, po, len(mine), key, shift))
rows.sort(reverse=True)
print("正解", len(truth), "／点数・位置も高さも合う・位置が合う・読んだ位置の数・設定・ずらし")
for r in rows[:8]: print("%.3f  %d  %d  %d  %s  %+.2f" % r)
json.dump({"key": rows[0][4], "shift": rows[0][5]}, open(D + "/bp_best.json", "w"))
