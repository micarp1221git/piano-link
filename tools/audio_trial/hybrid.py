# -*- coding: utf-8 -*-
"""わたしの読み（notes3）で音が無い8分の位置を、basic-pitch の音の頭で埋める。埋める音の高さは (a) basic-pitch のまま (b) 声の高さの線から、の2通り"""
import sys, json, re, numpy as np
D = sys.argv[1]; O = 2; fps = 22050 / 256; METER = 4
bt = np.load(D + "/bt.npy"); pos = lambda t: np.interp(t, bt, np.arange(len(bt))) - O; t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
R = json.load(open(D + "/ref.json")); ref = R["ref"]; f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0) - R["off"]
truth = {}
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if len(seg) and np.mean(~np.isnan(seg)) >= 0.5: truth[round(a * 2) / 2] = p % 12
vo = json.load(open(D + "/notes3.json"))["vo"]; base = {n[0]: n[1] for n in vo}
bp = json.load(open(D + "/notes_bp.json"))
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
def pc(s): return (PC[s[0]] + (1 if s[1:2] == "#" else -1 if s[1:2] == "b" else 0)) % 12
def tones(sym):
    body = sym.split("/")[0]; r = pc(body); q = body[2:] if body[1:2] in ("#", "b") else body[1:]
    third = 5 if "sus4" in q else 3 if (q.startswith("m") and not q.startswith("maj")) else 4
    t = [r, (r + third) % 12, (r + 7) % 12]
    if "7" in q and "maj7" not in q: t.append((r + 10) % 12)
    return t
chord_at = []; prev = None
for part in re.split(r"\[[^\]]+\]", open(D + "/chart.txt", encoding="utf-8").read().replace("\\n", "\n")):
    for cell in [c.strip() for c in part.split("|")]:
        if not cell: continue
        toks = cell.split()
        for b in range(METER):
            t = toks[b * len(toks) // METER]
            if t not in ("%", "-"): prev = t
            chord_at.append(prev)
SCALE = {7, 9, 11, 0, 2, 4, 6}
def line_pitch(q):   # その8分の間の声の高さ
    seg = M[int(t_of(q + 0.1) * fps):int(t_of(q + 0.45) * fps)]; seg = seg[~np.isnan(seg)]
    if len(seg) < 4: return None
    fm = float(np.percentile(seg, 65)); ct = set(tones(chord_at[int(min(len(chord_at) - 1, q))]))
    cost = lambda x: abs(fm - x) - (0.1 if x % 12 in ct else 0) + (1.0 if x % 12 not in SCALE and x % 12 not in ct else 0)
    return min((int(np.floor(fm)) - 1, int(np.floor(fm)), int(np.floor(fm)) + 1, int(np.floor(fm)) + 2), key=cost)
def score(m): return sum(1 for a, p in truth.items() if a in m and m[a] % 12 == p), sum(1 for a in truth if a in m), len(m)
print("正解", len(truth), "／わたしの読みだけ", score(base))
best = None
for key, ev in bp.items():
    for shift in (-0.1, -0.05, 0):
        for mode in ("bp", "line"):
            m = dict(base); added = 0
            for s, e, p, a in ev:
                q = round((float(pos(s)) + shift) * 2) / 2
                if q in m or q < 0 or q >= len(chord_at): continue
                pp = p if mode == "bp" else line_pitch(q)
                if pp is None: continue
                m[q] = pp; added += 1
            h, po, n = score(m); r = (2 * h / (n + len(truth)), h, po, n, added, key, shift, mode)
            if best is None or r > best: best = r
            if mode == "line" and shift == -0.1: print("%.3f 合う %d 位置 %d 読んだ %d 足した %d  %s %+.2f %s" % r)
print("いちばん良い:", "%.3f 合う %d 位置 %d 読んだ %d 足した %d  %s %+.2f %s" % best)
json.dump({"key": best[5], "shift": best[6], "mode": best[7]}, open(D + "/hybrid_best.json", "w"))
