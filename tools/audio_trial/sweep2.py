# -*- coding: utf-8 -*-
"""8分のマス目・立ち上がり2倍を土台に、高さの決め方（コードの音・キーの音への寄せ方）を比べる"""
import sys, json, re, itertools, numpy as np
D = sys.argv[1]; O = 2; METER = 4; fps = 22050 / 256
bt = np.load(D + "/bt.npy"); pos = lambda t: np.interp(t, bt, np.arange(len(bt))) - O; t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
R = json.load(open(D + "/ref.json")); ref = [tuple(x) for x in R["ref"]]
f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0) - R["off"]; ON = np.load(D + "/on_vocals.npy"); TH = np.percentile(ON, 75)
truth = {}
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if len(seg) and np.mean(~np.isnan(seg)) >= 0.5: truth[round(a * 2) / 2] = p % 12
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
pk = set(i for i in range(2, len(ON) - 2) if ON[i] > TH * 2.0 and ON[i] == ON[i - 2:i + 3].max())
segs = []; cur = None
for i in range(len(M)):
    x = M[i]
    if np.isnan(x):
        if cur and i - cur["e"] > 3: segs.append(cur); cur = None
        continue
    if cur and abs(x - np.median(cur["v"])) < 0.7 and not (i in pk and i - cur["s"] >= 7): cur["v"].append(x); cur["e"] = i
    else:
        fresh = cur is None
        if cur: segs.append(cur)
        cur = {"s": i, "e": i, "v": [x], "fresh": fresh}
if cur: segs.append(cur)
def run(cb, sp, stat):
    mine = {}; dur = {}
    for c in segs:
        n = len(c["v"])
        if n < 7: continue
        body = np.array(c["v"][int(n * 0.35):max(int(n * 0.35) + 1, int(n * 0.95))])
        fm = float(np.median(body)) if stat == "med" else float(np.percentile(body, 65))
        a = float(pos(c["s"] / fps)) + (0.14 if c["fresh"] else 0.03); qa = round(a * 2) / 2
        if qa < 0 or qa >= len(chord_at): continue
        ct = set(tones(chord_at[int(qa)]))
        cost = lambda q: abs(fm - q) - (cb if q % 12 in ct else 0) + (sp if q % 12 not in SCALE and q % 12 not in ct else 0)
        p = min((int(np.floor(fm)) - 1, int(np.floor(fm)), int(np.floor(fm)) + 1, int(np.floor(fm)) + 2), key=cost)
        if qa not in mine or n > dur[qa]: mine[qa] = p % 12; dur[qa] = n
    hit = sum(1 for a, p in truth.items() if mine.get(a) == p); po = sum(1 for a in truth if a in mine)
    return hit, po, len(mine)
print("正解", len(truth))
for stat in ("med", "p65"):
    for cb, sp in itertools.product((0, 0.1, 0.2, 0.3), (0, 0.3, 1.0)):
        h, po, n = run(cb, sp, stat); print("%s コードの音びいき %.1f キー外の罰 %.1f → 位置も高さも合う %d / 位置が合う %d / 読んだ %d  (高さ %.0f%%)" % (stat, cb, sp, h, po, n, 100 * h / po))
