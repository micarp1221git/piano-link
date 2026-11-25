# -*- coding: utf-8 -*-
"""いまのレッスン版（overdrive-v1）の右手と、音源から読んだ歌を突き合わせる"""
import sys, json, re, numpy as np
from collections import Counter
D, R = sys.argv[1], sys.argv[2]
def load(path):
    s = open(path).read(); return json.loads(s[s.index("]=") + 2:s.rindex(";")])
v1 = load(R + "/lesson-data-overdrive.js"); mine = json.load(open(D + "/notes2.json"))["vo"]
rh = [n for n in v1["notes"] if n[3] == 1]
# v1 の右手: 同じ位置のいちばん上の音をメロディーとみなす
top = {}
for a, p, l, h in rh: top[a] = max(top.get(a, (0, 0)), (p, l))
ref = sorted((a, p, l) for a, (p, l) in top.items())
print("v1 右手", len(rh), "音 / 位置", len(ref), "/ 高さ", min(p for a, p, l in ref), "〜", max(p for a, p, l in ref), "/ 位置の端数", Counter(round(a % 1, 2) for a, p, l in ref).most_common(6))
print("読んだ歌", len(mine), "音 / 高さ", min(n[1] for n in mine), "〜", max(n[1] for n in mine))
NN = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
# 小節ごとに、v1 の右手に音が何個あるか（歌の小節だけ見る）
for k in (11, 12, 13, 14, 15, 16, 17, 18, 44, 45, 46):
    f = lambda ns: " ".join("%s%d@%g(%g)" % (NN[p % 12], p // 12 - 1, a - k * 4, l) for a, p, l in ns if k * 4 <= a < k * 4 + 4)
    print("%3d v1 | %s\n    読 | %s" % (k + 1, f(ref), f(mine)))
# 全体のずれ: 読んだ音ごとに、±1拍以内でいちばん近い v1 の音（音名が同じもの優先）
dt = []; dp = []; un = 0
refa = np.array([a for a, p, l in ref])
for a, p, l in mine:
    idx = np.where(np.abs(refa - a) <= 1.0)[0]
    if not len(idx): un += 1; continue
    same = [i for i in idx if (ref[i][1] - p) % 12 == 0]
    if same: i = min(same, key=lambda i: abs(refa[i] - a)); dt.append(round(a - refa[i], 2))
    j = min(idx, key=lambda i: abs(refa[i] - a))
    if abs(refa[j] - a) < 0.13: dp.append((p - ref[j][1] + 6) % 12 - 6)
print("近くに v1 の音が無い", un, "／同じ音名が±1拍にある", len(dt), "／位置の差（読んだ−v1）", sorted(Counter(dt).items()))
print("同じ位置にある音", len(dp), "の高さの差（半音）", sorted(Counter(dp).items()))
