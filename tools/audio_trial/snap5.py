# -*- coding: utf-8 -*-
"""5回目（notes5）の残りのずれを調べ、キー（ト長調）の音に寄せて直るかを試す
使い方: python snap5.py <作業フォルダ>"""
import sys, json, collections, numpy as np
D = sys.argv[1]; O = 2; fps = 22050 / 256
bt = np.load(D + "/bt.npy"); t_of = lambda b: np.interp(b + O, np.arange(len(bt)), bt)
R = json.load(open(D + "/ref.json")); ref = R["ref"]; off = R["off"]
f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0) - off
truth = {}
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if len(seg) and np.mean(~np.isnan(seg)) >= 0.5: truth[round(a * 2) / 2] = p % 12
vo = json.load(open(D + "/notes5.json"))["vo"]; m = {n[0]: n for n in vo}
SCALE = {(7 + d) % 12 for d in (0, 2, 4, 5, 7, 9, 11)}
print("正解のうちキーの外の音", sum(1 for p in truth.values() if p not in SCALE), "/", len(truth))
c = collections.Counter()
for a, p in truth.items():
    if a not in m: continue
    q = m[a][1] % 12
    if q == p: c["合う・" + ("キーの中" if q in SCALE else "キーの外")] += 1
    else: c["違う・自分は" + ("中" if q in SCALE else "外") + "・ずれ%+d" % ((q - p + 6) % 12 - 6)] += 1
for k, v in sorted(c.items(), key=lambda x: -x[1]): print("  ", k, v)
def score(mm): return sum(1 for a, p in truth.items() if a in mm and mm[a] % 12 == p), len(mm)
base = {a: n[1] for a, n in m.items()}
print("5回目", score(base))
# 寄せ方: キーの外の音を、声の線の中央値に近い方のとなりへ
for name, pick in (("下へ", lambda q, fm: q - 1), ("上へ", lambda q, fm: q + 1), ("声の線に近い方へ", lambda q, fm: q + (1 if fm >= q else -1))):
    mm = {}
    for a, n in m.items():
        q = n[1]
        if q % 12 not in SCALE:
            seg = M[int(t_of(a + n[2] * 0.3) * fps):int(t_of(a + n[2] * 0.95) * fps) + 1]; seg = seg[~np.isnan(seg)]
            fm = np.median(seg) if len(seg) else q
            q = pick(q, fm)
        mm[a] = q
    print("キーの外を" + name, score(mm))
# となり合う音の流れ: 前後が同じ高さで自分だけ半音ちがう → そろえる
mm = dict(base); ks = sorted(mm); n = 0
for i in range(1, len(ks) - 1):
    a0, a1, a2 = ks[i - 1], ks[i], ks[i + 1]
    if base[a0] == base[a2] and abs(base[a1] - base[a0]) == 1 and a2 - a0 <= 2: mm[a1] = base[a0]; n += 1
print("前後と半音だけ違う音をそろえる", score(mm), "直した", n)
