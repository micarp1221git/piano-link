# -*- coding: utf-8 -*-
"""声・ベース・その他の音 → 16分のマス目の音（2回目）。使い方: build2.py <D> <コード譜> <頭の拍> <出力js> <譜面の番号>
1回目との違い（2026-11-26 みかさん「歌が半音ずれ・半拍や16分ずれ」「イントロはコードだけだと分からない」）:
  - 歌の入り: 声の出はじめは、高さの読み取りの窓のぶん早く出る（実測 -0.14拍）。無音のあとの入りはそのぶん戻してからマス目へ
  - 歌の高さ: 音の後ろ（35〜95%）で決める。キーにもその小節のコードにも無い音は、実際の高さに近い方のとなりへ寄せる
  - 歌の無い区切り: その他の音の立ち上がりの位置で、右手がコードを打つ。歌が戻る前の小節にスティックのカウント
"""
import sys, json, re, numpy as np
D = sys.argv[1]; O = int(sys.argv[3]); METER = 4; sr = 22050; hop = 256; fps = sr / hop
bt = np.load(D + "/bt.npy"); pos = lambda t: np.interp(t, bt, np.arange(len(bt))) - O
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
def pc(s): return (PC[s[0]] + (1 if s[1:2] == "#" else -1 if s[1:2] == "b" else 0)) % 12
def tones(sym):
    body = sym.split("/")[0]; r = pc(body); q = body[2:] if body[1:2] in ("#", "b") else body[1:]
    third = 5 if "sus4" in q else 3 if (q.startswith("m") and not q.startswith("maj")) else 4
    t = [r, (r + third) % 12, (r + 7) % 12]
    if "maj7" in q or "M7" in q: t.append((r + 11) % 12)
    elif "7" in q: t.append((r + 10) % 12)
    return t
# コード譜 → 拍ごとのコード、区切り
chord_at = []; sections = []; text = open(sys.argv[2], encoding="utf-8").read().replace("\\n", "\n")
parts = re.split(r"\[([^\]]+)\]", text); prev = None
for i in range(1, len(parts), 2):
    start = len(chord_at) // METER
    for cell in [c.strip() for c in parts[i + 1].split("|")]:
        if not cell: continue
        toks = cell.split(); n = len(toks)
        for b in range(METER):
            t = toks[b * n // METER]
            if t not in ("%", "-"): prev = t
            chord_at.append(prev)
    sections.append([parts[i].strip(), start, len(chord_at) // METER - 1])
NB = len(chord_at) // METER; TOTAL = NB * METER
# キー: コードの音を全部足して、いちばん合う長音階
hist = np.zeros(12)
for c in chord_at:
    for t in tones(c): hist[t] += 1
MAJ = [0, 2, 4, 5, 7, 9, 11]; key = max(range(12), key=lambda k: sum(hist[(k + d) % 12] for d in MAJ)); SCALE = {(key + d) % 12 for d in MAJ}
def midi(name):
    f = np.load(D + "/f0_" + name + ".npy"); m = 69 + 12 * np.log2(f / 440.0); v = m[~np.isnan(m)]
    off = max(np.arange(-0.5, 0.5, 0.02), key=lambda o: np.mean(np.abs(((v - o) + 0.5) % 1 - 0.5) < 0.2)); return m - off
def peaks(on, thr, gap):
    th = np.percentile(on, 75) * thr; out = []
    for i in range(2, len(on) - 2):
        if on[i] > th and on[i] == on[i - 2:i + 3].max() and (not out or i - out[-1] >= gap): out.append(i)
    return out
def grid(a):   # 8分に近ければ8分、はっきり離れていれば16分
    e8 = round(a * 2) / 2; return e8 if abs(a - e8) <= 0.15 else round(a * 4) / 4
def mono(ns):  # [始まり, 終わり, 高さ] → 重なりの無い [位置, 高さ, 長さ]
    out = []
    for a, b, p in ns:
        qa = grid(a); qb = max(qa + 0.25, round(b * 4) / 4)
        if qa < 0 or qa >= TOTAL: continue
        if out and out[-1][0] == qa:
            if qb - qa > out[-1][2]: out[-1] = [qa, p, qb - qa]
            continue
        if out and out[-1][0] + out[-1][2] > qa: out[-1][2] = qa - out[-1][0]
        out.append([qa, p, min(qb, TOTAL) - qa])
    return [n for n in out if n[2] > 0]

# ---- 歌 ----
mv = midi("vocals"); onv = set(peaks(np.load(D + "/on_vocals.npy"), 3.0, 7))
EARLY = 0.14   # 無音のあとの入りは、このぶん早く読めている（probe.py の実測）
segs = []; cur = None
for i in range(len(mv)):
    x = mv[i]
    if np.isnan(x):
        if cur and i - cur["e"] > 3: segs.append(cur); cur = None
        continue
    if cur and abs(x - np.median(cur["v"])) < 0.7 and not (i in onv and i - cur["s"] >= 7): cur["v"].append(x); cur["e"] = i
    else:
        fresh = cur is None
        if cur: segs.append(cur)
        cur = {"s": i, "e": i, "v": [x], "fresh": fresh}
if cur: segs.append(cur)
snapped = 0; raw = []
for c in segs:
    n = len(c["v"])
    if n < 7: continue
    body = np.array(c["v"][int(n * 0.35):max(int(n * 0.35) + 1, int(n * 0.95))]); f = float(np.median(body)); p = int(round(f))
    a = float(pos(c["s"] / fps)) + (EARLY if c["fresh"] else 0.03); b = float(pos((c["e"] + 1) / fps)) - 0.05
    beat = int(min(TOTAL - 1, max(0, round(a)))); ok = SCALE | set(tones(chord_at[beat]))
    if p % 12 not in ok:
        cand = [q for q in (p - 1, p + 1) if q % 12 in ok]
        if cand: p = min(cand, key=lambda q: abs(q - f)); snapped += 1
    raw.append([a, max(a + 0.2, b), p])
vo = mono(raw)
# 16分の短い音が、となりと半音〜全音でつながる所は、しゃくり・揺れとして長い方へ
i = 0
while i < len(vo):
    a, p, l = vo[i]
    if l <= 0.25:
        nx = vo[i + 1] if i + 1 < len(vo) else None; pv = vo[i - 1] if i > 0 else None
        if nx and abs(nx[0] - (a + l)) < 1e-6 and 0 < abs(nx[1] - p) <= 2 and nx[2] >= l: nx[0] = a; nx[2] += l; vo.pop(i); continue
        if pv and abs(pv[0] + pv[2] - a) < 1e-6 and abs(pv[1] - p) <= 1: pv[2] += l; vo.pop(i); continue
    i += 1
# 同じ高さが切れ目なく続くだけの所（立ち上がりも無い）はつなぐ
out = []
for n in vo:
    if out and out[-1][1] == n[1] and abs(out[-1][0] + out[-1][2] - n[0]) < 1e-6 and out[-1][2] <= 0.25: out[-1][2] += n[2]
    else: out.append(n)
vo = out

# ---- ベース（1回目と同じ読み方）----
mb = midi("bass"); cuts = [0] + peaks(np.load(D + "/on_bass.npy"), 2.0, 6); extra = []
for a, b in zip(cuts, cuts[1:] + [len(mb)]):
    j = a + 4
    while j < b - 4:
        l = mb[max(a, j - 6):j]; l = l[~np.isnan(l)][-4:]; r = mb[j:j + 6]; r = r[~np.isnan(r)][:4]
        if len(l) >= 3 and len(r) >= 3 and np.ptp(l) < 1.0 and np.ptp(r) < 1.0 and abs(np.median(l) - np.median(r)) >= 1.5 and not np.isnan(mb[j]): extra.append(j); j += 5
        else: j += 1
cuts = sorted(set(cuts + extra)); raw = []
for a, b in zip(cuts, cuts[1:] + [len(mb)]):
    seg = mb[a:b]; ok = ~np.isnan(seg)
    if b - a < 6 or ok.mean() < 0.4: continue
    last = a + int(np.where(ok)[0].max()) + 1; tail = seg[int(len(seg) * 0.5):]; tail = tail[~np.isnan(tail)]
    raw.append([float(pos(a / fps)), float(pos(last / fps)), int(round(np.median(tail if len(tail) >= 3 else seg[ok]))) + 12])
ba = [[a, p, min(l, 2.0)] for a, p, l in mono(raw)]
for x, y in zip(ba, ba[1:]):   # 拍の頭のずり上げ
    if x[0] % 1 == 0 and x[2] <= 0.5 and y[1] - x[1] == 1 and abs(x[0] + x[2] - y[0]) < 1e-6: x[1] = y[1]

# ---- 歌の無い区切り: その他の音の立ち上がりで、右手がコードを打つ ----
voiced_bar = np.zeros(NB)
for a, p, l in vo: voiced_bar[int(a // METER)] += l
nosing = [s for s in sections if voiced_bar[s[1]:s[2] + 1].sum() < 0.08 * (s[2] - s[1] + 1) * METER]
ono = np.load(D + "/on_other.npy"); stabs = []
pk = [float(pos(i / fps)) for i in peaks(ono, 2.2, 6)]
for name, s, e in nosing:
    hits = sorted({grid(p) for p in pk if s * METER <= grid(p) < (e + 1) * METER})
    for k, a in enumerate(hits):
        nxt = hits[k + 1] if k + 1 < len(hits) else (e + 1) * METER; ln = min(1.0, nxt - a) * 0.9
        ts = tones(chord_at[int(a)])[:3]; top = 62 + (ts[0] - 62) % 12   # いちばん上がコードの根音（D4〜Db5）
        for t in ts: stabs.append([a, top - (top - t) % 12, ln])
# カウント: 歌が4小節以上あいたあとに戻る所の、前の小節にスティック4つ（頭の入りも）
clicks = []; sung = [b for b in range(NB) if voiced_bar[b] >= 0.5]; prevb = -99
for b in sung:
    if b - prevb > 4 and b >= 1: clicks += [[(b - 1) * METER + k, 127, 0.12] for k in range(METER)]
    prevb = b
def stat(ns, name):
    fr = [n[0] % 1 for n in ns]; print(name, len(ns), "音 / 表拍", sum(f == 0 for f in fr), "8分ウラ", sum(f == .5 for f in fr), "16分", sum(f in (.25, .75) for f in fr))
stat(vo, "歌"); stat(ba, "ベース"); print("キー", key, "／キーにもコードにも無くて寄せた音", snapped, "／歌の無い区切り", [(n, s + 1, e + 1) for n, s, e in nosing], "／コードを打つ位置", len(stabs) // 3, "／カウントを置いた小節", sorted({int(c[0] // METER) + 1 for c in clicks}))
allv = sorted([[round(a, 2), p, round(l, 2), 0] for a, p, l in clicks] + [[round(a, 2), p, round(l, 2), 1] for a, p, l in vo + stabs] + [[round(a, 2), p, round(l, 2), 2] for a, p, l in ba])
sid = sys.argv[5]
open(sys.argv[4], "w").write("window.PIANO_SCORES=window.PIANO_SCORES||{};\nwindow.PIANO_SCORES[\"%s\"]=" % sid + json.dumps({"id": sid, "bars": NB, "meter": METER, "notes": allv}, separators=(",", ":")) + ";\n")
json.dump({"nosing": [n for n, s, e in nosing], "vo": vo}, open(D + "/notes2.json", "w"), ensure_ascii=False)
NN = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
for k in (11, 12, 13, 14, 15, 45):
    print("%3d 歌| %s" % (k + 1, " ".join("%s@%g(%g)" % (NN[p % 12], a - k * 4, l) for a, p, l in vo if k * 4 <= a < k * 4 + 4)))
for k in (3, 4, 5, 6):
    print("%3d 打| %s" % (k + 1, " ".join("%g" % (a - k * 4) for a in sorted({s[0] for s in stabs}) if k * 4 <= a < k * 4 + 4)))
