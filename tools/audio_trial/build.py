# -*- coding: utf-8 -*-
"""声とベースの高さ → 16分のマス目の音。使い方: build.py <D> <コード譜のテキスト> [頭の拍の番号]"""
import sys, json, re, numpy as np
D = sys.argv[1]; METER = 4; sr = 22050; hop = 256; fps = sr / hop
bt = np.load(D + "/bt.npy")
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
def pc(s): return (PC[s[0]] + (1 if s[1:2] == "#" else -1 if s[1:2] == "b" else 0)) % 12
def bass_of(sym): return pc(sym.split("/")[1]) if "/" in sym else pc(sym)
bars = []
for line in open(sys.argv[2], encoding="utf-8").read().replace("\\n", "\n").split("\n"):
    for cell in [c.strip() for c in re.sub(r"\[[^\]]*\]", "", line).split("|")]:
        if not cell: continue
        toks = cell.split(); first = toks[0]
        bars.append(bars[-1] if first == "%" else bass_of(first))
NB = len(bars)
def midi(name):
    f = np.load(D + "/f0_" + name + ".npy"); m = 69 + 12 * np.log2(f / 440.0); v = m[~np.isnan(m)]
    off = max(np.arange(-0.5, 0.5, 0.02), key=lambda o: np.mean(np.abs(((v - o) + 0.5) % 1 - 0.5) < 0.2)); return m - off, off
mb, ob = midi("bass"); mv, ov = midi("vocals")
def pos(t): return np.interp(t, bt, np.arange(len(bt)))   # 秒 → 拍の番号（小数）
# 頭の拍を決める: 小節の最初の1拍半のベースの音名が、コード譜の低い音と合う割合
def score(o):
    hit = n = 0
    for k in range(NB):
        i0 = o + k * METER
        if i0 + 2 >= len(bt): break
        a, b = int(bt[i0] * fps), int((bt[i0] + (bt[i0 + 2] - bt[i0]) * 0.75) * fps); seg = mb[a:b]; seg = seg[~np.isnan(seg)]
        if len(seg) < 4: continue
        n += 1; hit += int(np.bincount(np.round(seg).astype(int) % 12, minlength=12).argmax() == bars[k])
    return hit / max(1, n), n
if len(sys.argv) > 3: O = int(sys.argv[3])
else:
    cand = sorted(((score(o)[0], o) for o in range(0, 16)), reverse=True); print("頭の拍の候補", [(round(s, 2), o) for s, o in cand[:5]]); O = cand[0][1]
print("頭の拍", O, "合う割合", score(O), "小節", NB, "調律 ベース%+.2f 声%+.2f" % (ob, ov))
def notes(m, on, min_fr, split_thr, shift):
    # 高さが続く所を1音に。同じ高さでも立ち上がりが強い所では切る（同じ音の連打）
    peaks = set(); th = np.percentile(on, 75) * split_thr
    for i in range(2, len(on) - 2):
        if on[i] > th and on[i] == on[i - 2:i + 3].max(): peaks.add(i)
    out = []; cur = None
    for i in range(len(m)):
        x = m[i]
        if np.isnan(x):
            if cur and i - cur["e"] > 3: out.append(cur); cur = None
            continue
        if cur and abs(x - np.median(cur["v"])) < 0.7 and not (i in peaks and i - cur["s"] >= min_fr): cur["v"].append(x); cur["e"] = i
        else:
            if cur: out.append(cur)
            cur = {"s": i, "e": i, "v": [x]}
    if cur: out.append(cur)
    res = []
    for c in out:
        if c["e"] - c["s"] + 1 < min_fr: continue
        res.append([float(pos(c["s"] / fps)) - O, float(pos((c["e"] + 1) / fps)) - O, int(round(np.median(c["v"]))) + shift])
    return res

def onset_notes(m, on, min_fr, split_thr, shift):
    th = np.percentile(on, 75) * split_thr; cuts = [0]
    for i in range(2, len(on) - 2):
        if on[i] > th and on[i] == on[i - 2:i + 3].max() and i - cuts[-1] >= min_fr: cuts.append(i)
    # 立ち上がりが無くても、高さが2半音近く変わって両側が安定している所は切る
    extra = []
    for a, b in zip(cuts, cuts[1:] + [len(m)]):
        j = a + 4
        while j < b - 4:
            l = m[max(a, j - 6):j]; l = l[~np.isnan(l)][-4:]; r = m[j:j + 6]; r = r[~np.isnan(r)][:4]
            if len(l) >= 3 and len(r) >= 3 and np.ptp(l) < 1.0 and np.ptp(r) < 1.0 and abs(np.median(l) - np.median(r)) >= 1.5 and not np.isnan(m[j]): extra.append(j); j += 5
            else: j += 1
    cuts = sorted(set(cuts + extra)); res = []
    for a, b in zip(cuts, cuts[1:] + [len(m)]):
        seg = m[a:b]; ok = ~np.isnan(seg)
        if b - a < min_fr or ok.mean() < 0.4: continue
        last = a + int(np.where(ok)[0].max()) + 1; tail = seg[int(len(seg) * 0.5):]; tail = tail[~np.isnan(tail)]
        v = tail if len(tail) >= 3 else seg[ok]
        res.append([float(pos(a / fps)) - O, float(pos(last / fps)) - O, int(round(np.median(v))) + shift])
    return res
def tidy(ns):
    # 歌: 16分の短い音が、となりの音と半音〜全音でつながっている所は、しゃくり・揺れとして長い方にまとめる
    out = [list(n) for n in ns]; i = 0
    while i < len(out):
        a, p, l = out[i]
        if l <= 0.25:
            nx = out[i + 1] if i + 1 < len(out) else None; pv = out[i - 1] if i > 0 else None
            if nx and abs(nx[0] - (a + l)) < 1e-6 and 0 < abs(nx[1] - p) <= 2 and nx[2] >= l: nx[0] = a; nx[2] += l; out.pop(i); continue
            if pv and abs(pv[0] + pv[2] - a) < 1e-6 and abs(pv[1] - p) <= 1: pv[2] += l; out.pop(i); continue
        i += 1
    return out
def quant(ns):
    out = []
    for a, b, p in ns:
        e8 = round(a * 2) / 2; qa = e8 if abs(a - e8) <= 0.15 else round(a * 4) / 4
        qb = max(qa + 0.25, round(b * 4) / 4)
        if qa < 0 or qa >= NB * METER: continue
        if out and out[-1][0] == qa:
            if qb - qa > out[-1][2]: out[-1] = [qa, p, qb - qa]
            continue
        if out and out[-1][0] + out[-1][2] > qa: out[-1][2] = qa - out[-1][0]
        out.append([qa, p, min(qb, NB * METER) - qa])
    return [n for n in out if n[2] > 0]
vo = tidy(quant(notes(mv, np.load(D + "/on_vocals.npy"), 7, 3.0, 0)))
ba = quant(onset_notes(mb, np.load(D + "/on_bass.npy"), 6, float(sys.argv[4]) if len(sys.argv) > 4 else 2.0, 12))
# ベースは伸ばしすぎない: 次の音まで、長くても2拍
ba = [[a, p, min(l, 2.0)] for a, p, l in ba]
def stat(ns, name):
    fr = [n[0] % 1 for n in ns]; print(name, len(ns), "音 / 表拍", sum(f == 0 for f in fr), "8分ウラ", sum(f == .5 for f in fr), "16分", sum(f in (.25, .75) for f in fr), "/ 高さ", min(n[1] for n in ns), "〜", max(n[1] for n in ns))
stat(vo, "声"); stat(ba, "ベース")
allv = sorted([[a, p, l, 1] for a, p, l in vo] + [[a, p, l, 2] for a, p, l in ba])
json.dump({"bars": NB, "meter": METER, "notes": allv, "O": O}, open(D + "/notes.json", "w"))
NN = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
for k in (8, 9, 10, 11, 12, 13, 14, 15, 44, 45, 76, 77):
    f = lambda ns: " ".join("%s@%g(%g)" % (NN[p % 12], a - k * 4, l) for a, p, l in ns if k * 4 <= a < k * 4 + 4)
    print("%3d 声| %s\n    低| %s" % (k + 1, f(vo), f(ba)))
