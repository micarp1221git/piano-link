# -*- coding: utf-8 -*-
"""歌声専用モデル SOME の読み（some.mid・テンポ120＝1拍0.5秒）を、いままでと同じ採点（8分の位置＋音名）にかける
使い方: python somescore.py <作業フォルダ>   → いちばん良い設定の音を notes_some.json に書く"""
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
print("SOMEが読んだ音", len(raw), "／正解", len(truth), "／高さの補正 off", off)

def build(shift, minlen, merge):
    ns = []
    for s, e, p in raw:
        if e - s < minlen: continue
        a = round((b_of(s) + shift) * 2) / 2; l = max(0.5, round((b_of(e) - b_of(s)) * 2) / 2)
        q = int(round(p - off))
        if ns and ns[-1][0] == a:            # 同じマスに2つ → 長い方
            if l > ns[-1][2]: ns[-1] = [a, q, l]
            continue
        if merge and ns and ns[-1][1] == q and abs(ns[-1][0] + ns[-1][2] - a) < 0.01 and e - s < merge:
            ns[-1][2] += l; continue
        ns.append([a, q, l])
    return ns
def score(ns):
    m = {n[0]: n[1] for n in ns}
    return sum(1 for a, p in truth.items() if a in m and m[a] % 12 == p), sum(1 for a in truth if a in m), len(m)
rows = []
for shift, minlen, merge in itertools.product(np.arange(-0.4, 0.41, 0.05), (0, 0.05, 0.08, 0.12), (0,)):
    rows.append(score(build(shift, minlen, merge)) + (round(float(shift), 2), minlen, merge))
rows.sort(reverse=True)
for r in rows[:10]: print("合う %d 位置 %d 読んだ %d ／ずらし %.2f拍 短い音を捨てる<%.2f秒" % r[:5])
b = rows[0]; best = build(*b[3:]); json.dump({"vo": best}, open(D + "/notes_some.json", "w"))
# 内訳
m = {n[0]: n[1] for n in best}; diff = {}
for a, p in truth.items():
    if a not in m: diff["位置なし"] = diff.get("位置なし", 0) + 1
    else:
        d = (m[a] - p + 6) % 12 - 6; diff[d] = diff.get(d, 0) + 1
print("内訳", diff)
# いまの4回目と合わせる: 4回目で位置が無い所だけ SOME の音で埋める／高さが食い違う所の数
n4 = json.load(open(D + "/notes4.json"))["vo"]; m4 = {n[0]: n[1] for n in n4}
fill = dict(m4); add = 0
for a, q in m.items():
    if a not in fill: fill[a] = q; add += 1
print("4回目", sum(1 for a, p in truth.items() if a in m4 and m4[a] % 12 == p), "／4回目の抜けをSOMEで埋める",
      sum(1 for a, p in truth.items() if a in fill and fill[a] % 12 == p), "読んだ", len(fill), "足した", add)
both = sum(1 for a, p in truth.items() if a in m4 and a in m and m4[a] % 12 == p and m[a] % 12 == p)
either = sum(1 for a, p in truth.items() if (a in m4 and m4[a] % 12 == p) or (a in m and m[a] % 12 == p))
print("両方合う", both, "／どちらかが合う", either)
