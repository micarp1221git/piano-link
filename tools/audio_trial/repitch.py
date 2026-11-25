# -*- coding: utf-8 -*-
"""notes3 の音の位置はそのまま、高さだけ決め直す。試すのは: 何パーセント点か・上向きの補正・コードの音のひいき・しゃくり（短い音が上がりながら次の長い音に続く）を次の音にまとめる"""
import sys, json, re, itertools, numpy as np
D = sys.argv[1]; O = 2; fps = 22050 / 256; METER = 4
bt = np.load(D + "/bt.npy"); t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
R = json.load(open(D + "/ref.json")); ref = R["ref"]; f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0) - R["off"]
truth = {}
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if len(seg) and np.mean(~np.isnan(seg)) >= 0.5: truth[round(a * 2) / 2] = p % 12
vo = json.load(open(D + "/notes3.json"))["vo"]
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
def seg_of(a, l, lo, hi):
    s = M[int(t_of(a + l * lo) * fps):max(int(t_of(a + l * lo) * fps) + 1, int(t_of(a + l * hi) * fps))]; return s[~np.isnan(s)]
def decide(a, l, P, B, C, lo):
    s = seg_of(a, l, lo, 0.95)
    if len(s) < 3: return None
    fm = float(np.percentile(s, P)) + B; ct = set(tones(chord_at[int(min(len(chord_at) - 1, a))]))
    cost = lambda x: abs(fm - x) - (C if x % 12 in ct else 0) + (1.0 if x % 12 not in SCALE and x % 12 not in ct else 0)
    k = int(np.floor(fm)); return min((k - 1, k, k + 1, k + 2), key=cost)
def run(P, B, C, lo, scoop):
    ns = []
    for a, p, l in vo:
        q = decide(a, l, P, B, C, lo); ns.append([a, p if q is None else q, l])
    if scoop:
        out = []; i = 0
        while i < len(ns):
            a, p, l = ns[i]
            if i + 1 < len(ns):
                a2, p2, l2 = ns[i + 1]
                if l <= 0.5 and abs(a + l - a2) < 0.01 and 1 <= p2 - p <= 2 and l2 >= scoop:
                    s = seg_of(a, l, 0.0, 1.0)
                    if len(s) >= 6 and np.median(s[-len(s) // 3:]) - np.median(s[:len(s) // 3]) > 0.5:
                        out.append([a, p2, l + l2]); i += 2; continue
            out.append(ns[i]); i += 1
        ns = out
    return ns
def score(ns):
    m = {n[0]: n[1] for n in ns}
    return sum(1 for a, p in truth.items() if a in m and m[a] % 12 == p), sum(1 for a in truth if a in m), len(m)
print("正解", len(truth), "／いまの3回目", score(vo))
rows = []
for P, B, C, lo, scoop in itertools.product((50, 65, 75), (0, 0.1, 0.2, 0.3), (0, 0.1, 0.2), (0.35, 0.5), (0, 0.75, 1.5)):
    h, po, n = score(run(P, B, C, lo, scoop)); rows.append((h, po, n, P, B, C, lo, scoop))
rows.sort(reverse=True)
for r in rows[:10]: print("合う %d 位置 %d 読んだ %d ／点 %d 補正 %.1f コード %.1f 始め %.2f しゃくり %s" % r)
print("しゃくり無しの最高:", max(r for r in rows if r[7] == 0))
best = rows[0]; json.dump({"vo": run(*best[3:])}, open(D + "/notes4.json", "w"))
