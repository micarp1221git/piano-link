# -*- coding: utf-8 -*-
"""SOME は「どこで音が変わるか」が得意（位置 359/395）、高さは半音ずれが多い。
→ 区切りは SOME、高さは声の線（f0）から測り直す。さらに4回目（notes4）と組み合わせる
使い方: python somemix.py <作業フォルダ>   → いちばん良い組み合わせを notes5.json に書く"""
import sys, json, itertools, numpy as np, mido
D = sys.argv[1]; O = 2; fps = 22050 / 256
bt = np.load(D + "/bt.npy"); idx = np.arange(len(bt))
t_of = lambda b: np.interp(b + O, idx, bt)
b_of = lambda t: np.interp(t, bt, idx) - O
R = json.load(open(D + "/ref.json")); ref = R["ref"]; off = R["off"]
f = np.load(D + "/f0_vocals.npy"); M = 69 + 12 * np.log2(f / 440.0) - off
truth = {}
for a, p, l in ref:
    seg = M[int(t_of(a + 0.12) * fps):int(t_of(a + l - 0.05) * fps)]
    if len(seg) and np.mean(~np.isnan(seg)) >= 0.5: truth[round(a * 2) / 2] = p % 12
mid = mido.MidiFile(D + "/some.mid"); tpb = mid.ticks_per_beat
raw = []; open_ = {}
for tr in mid.tracks:
    t = 0
    for m in tr:
        t += m.time
        if m.type == "note_on" and m.velocity > 0: open_[m.note] = t
        elif m.type in ("note_off", "note_on") and m.note in open_:
            s = open_.pop(m.note); raw.append((s / tpb * 0.5, t / tpb * 0.5, m.note))
raw.sort()
n4 = json.load(open(D + "/notes4.json"))["vo"]; m4 = {n[0]: n for n in n4}

def some_notes(shift, lo, hi, pct, mode):
    ns = {}
    for s, e, p in raw:
        a = round((b_of(s) + shift) * 2) / 2; l = max(0.5, round((b_of(e) - b_of(s)) * 2) / 2)
        seg = M[int((s + (e - s) * lo) * fps):int((s + (e - s) * hi) * fps) + 1]; seg = seg[~np.isnan(seg)]
        ps = int(round(p - off))
        if mode == "some" or len(seg) < 3: q = ps
        else:
            q = int(round(np.percentile(seg, pct)))
            if mode == "near" and abs(q - ps) > 2: q = ps      # 声の線が大きく外れたら SOME を信じる
        if a not in ns or l > ns[a][2]: ns[a] = [a, q, l]
    return ns
def score(m):
    return sum(1 for a, p in truth.items() if a in m and m[a][1] % 12 == p), sum(1 for a in truth if a in m), len(m)
rows = []
for shift, (lo, hi), pct, mode in itertools.product((0.05, 0.1), ((0.2, 0.95), (0.35, 0.95), (0.5, 1.0)), (50, 65, 75), ("f0", "near")):
    s = some_notes(shift, lo, hi, pct, mode)
    rows.append(("SOMEの区切り＋声の線",) + score(s) + (shift, lo, hi, pct, mode))
    # 4回目を土台に、抜けている位置だけ足す
    a = dict(m4)
    for k, v in s.items():
        if k not in a: a[k] = v
    rows.append(("4回目＋抜けを足す",) + score(a) + (shift, lo, hi, pct, mode))
    # SOME の区切りを土台に、4回目に同じ位置があればその高さ
    b = {k: [k, (m4[k][1] if k in m4 else v[1]), v[2]] for k, v in s.items()}
    rows.append(("SOMEの区切り＋4回目の高さ",) + score(b) + (shift, lo, hi, pct, mode))
rows.sort(key=lambda r: (-r[1], r[3]))
for r in rows[:14]: print("%s: 合う %d 位置 %d 読んだ %d ／ずらし %.2f 測る範囲 %.2f-%.2f %d%%点 %s" % r)
print("---読んだ数が少ない順に、各やり方の最良")
seen = set()
for r in rows:
    if r[0] not in seen: seen.add(r[0]); print("%s: 合う %d 位置 %d 読んだ %d ／ずらし %.2f 測る範囲 %.2f-%.2f %d%%点 %s" % r)
best = next(r for r in rows if r[0] != "4回目＋抜けを足す")
s = some_notes(*best[4:])
if best[0] == "SOMEの区切り＋4回目の高さ": s = {k: [k, (m4[k][1] if k in m4 else v[1]), v[2]] for k, v in s.items()}
json.dump({"vo": [s[k] for k in sorted(s)], "how": best[0]}, open(D + "/notes5.json", "w"), ensure_ascii=False)
print("notes5 ＝", best[0], best[1:4])
