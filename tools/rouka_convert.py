# -*- coding: utf-8 -*-
"""musicxml_to_lesson.py を「廊下を走るな」用に直した写し（リポジトリ側は触っていない）。
直した点:
 1) backup で小節の頭より前に戻る壊れた値 → 0 で止める（左手が負の拍に置かれていた）
 2) 小節の長さは拍子記号でなく中身で数える（段ごとの長さの小さいほう）。譜面は 2/4 と 4/4 が入り混じり、拍子記号と中身が合わない
 3) DROP_BARS の小節（休符だけの変換のごみ）を捨てる
 4) PADS の位置に拍を足して（TRIMS は逆に拍を抜く・LEN_FIX は小節の長さを手で決める）、4/4 の小節線にそろえる（足した所は左手の和音を続ける）
 5) タイは「前の音の終わり＝次の音の頭」のときだけつなげる
 6) 全体を 4/4 で小節を切り直し、コードも絶対拍から小節に入れ直す。CHORD_FIX で譜面のコード記号を上書きできる
使い方: python3 rouka_convert.py <譜面.xml> <score_id> <出力.js> <中間.json>
"""
import sys, json
import xml.etree.ElementTree as ET
src, sid, out_js, out_json = sys.argv[1:5]
METER = 4
DROP_BARS = {3}            # 譜面の小節（0始まり）: 休符だけ
PADS = [(22, 4.0, 2.0, [(44, 2), (51, 2), (56, 2), (51, 2)])]   # (譜面の小節, 小節内の拍, 足す拍, 足す間に8分で順に弾く左手の音)
LEN_FIX = {72: 5.0}      # 譜面の小節: 中身の長さを手で決める（右手5拍・左手4拍の小節。右手が正）
TRIMS = {71: (0.0, 1.0)}   # 譜面の小節: (ここから, ここまで) の拍を抜く
root = ET.parse(src).getroot(); part = root.find('part')
STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
KIND = {'major': '', 'minor': 'm', 'dominant': '7', 'major-seventh': 'maj7', 'minor-seventh': 'm7',
        'diminished': 'dim', 'augmented': 'aug', 'suspended-fourth': 'sus4', 'major-sixth': '6',
        'minor-sixth': 'm6', 'half-diminished': 'm7-5', 'diminished-seventh': 'dim7'}
acc = lambda a: '#' if a > 0 else 'b' if a < 0 else ''
div = 1
sheet = []  # 小節ごと {len, notes:[pos,midi,dur,hand,ties], chords:[pos,sym], mark}
kinds_unknown = set()
for mi, m in enumerate(part.findall('measure')):
    cur = 0.0; last = 0.0; vl = {}; B = {'notes': [], 'chords': [], 'mark': None, 'i': mi}
    for el in m:
        tag = el.tag
        if tag == 'attributes':
            d = el.find('divisions')
            if d is not None: div = int(d.text)
        elif tag == 'backup': cur = max(0.0, cur - int(el.find('duration').text) / div)
        elif tag == 'forward': cur += int(el.find('duration').text) / div
        elif tag == 'direction':
            r = el.find('direction-type/rehearsal')
            if r is not None and r.text: B['mark'] = r.text.strip()
        elif tag == 'harmony':
            st = el.find('root/root-step').text
            alt = el.find('root/root-alter'); alt = int(float(alt.text)) if alt is not None else 0
            k = el.find('kind'); kt = k.text.strip() if k is not None and k.text else ''
            if kt not in KIND: kinds_unknown.add(kt)
            sym = st + acc(alt) + KIND.get(kt, '')
            b = el.find('bass/bass-step')
            if b is not None:
                ba = el.find('bass/bass-alter'); ba = int(float(ba.text)) if ba is not None else 0
                sym += '/' + b.text + acc(ba)
            off = el.find('offset'); off = int(float(off.text)) / div if off is not None else 0.0
            B['chords'].append([max(0.0, cur + off), sym])
        elif tag == 'note':
            de = el.find('duration')
            if de is None: continue
            dur = int(de.text) / div
            is_ch = el.find('chord') is not None
            if is_ch: cur -= last
            hand = int(el.findtext('staff') or 1); key = (hand, el.findtext('voice'))
            p = el.find('pitch')
            if p is not None:
                a = el.find('pitch/alter'); a = int(float(a.text)) if a is not None else 0
                midi = 12 * (int(p.find('octave').text) + 1) + STEP[p.find('step').text] + a
                B['notes'].append([cur, midi, dur, hand, [t.get('type') for t in el.findall('tie')]])
            cur += dur; last = dur
            vl[key] = max(vl.get(key, 0), cur)
    st_len = {}
    for (h, v), L in vl.items(): st_len[h] = max(st_len.get(h, 0), L)
    B['len'] = LEN_FIX.get(mi, min(st_len.values()) if st_len else 0.0)
    if mi in TRIMS:
        a_, b_ = TRIMS[mi]; w = b_ - a_; nn = []
        for n in B['notes']:
            if a_ - 1e-9 <= n[0] < b_ - 1e-9:
                if n[0] + n[2] > b_ + 1e-9: n[2] = n[0] + n[2] - b_; n[0] = a_; nn.append(n)
            else:
                if n[0] >= b_ - 1e-9: n[0] -= w
                nn.append(n)
        B['notes'] = nn
        B['chords'] = [[c[0] - w if c[0] >= b_ - 1e-9 else c[0], c[1]] for c in B['chords'] if not (a_ - 1e-9 <= c[0] < b_ - 1e-9)]
        B['len'] -= w
    sheet.append(B)

pad_at = {(b, p): (n, fill) for b, p, n, fill in PADS}
notes, chords, marks, bar_map = [], [], [], []
open_ties = {}
t0 = 0.0
for B in sheet:
    if B['i'] in DROP_BARS: continue
    L = B['len']; pads_here = sorted((p, n, fill) for (b, p), (n, fill) in pad_at.items() if b == B['i'])
    def shift(pos):
        return sum(n for p, n, _ in pads_here if pos >= p - 1e-9)
    if B['mark']: marks.append((t0 + shift(0.0), B['mark']))
    bar_map.append((B['i'], t0, L + sum(n for _, n, _ in pads_here)))
    for p, n, fill in pads_here:
        k = 0
        while k * 0.5 < n - 1e-9:
            midi, hand = fill[k % len(fill)]; notes.append([round(t0 + p + k * 0.5, 4), midi, 0.5, hand]); k += 1
    for pos, midi, dur, hand, ties in B['notes']:
        if pos >= L - 1e-6: continue           # 小節からはみ出た音は捨てる
        d = min(dur, L - pos); start = t0 + pos + shift(pos); key = (midi, hand)
        if 'stop' in ties and key in open_ties and abs(open_ties[key][0] + open_ties[key][2] - start) < 0.02:
            n_ = open_ties[key]; n_[2] = round(start + d - n_[0], 4)
            if 'start' not in ties: del open_ties[key]
        else:
            n_ = [round(start, 4), midi, round(d, 4), hand]; notes.append(n_)
            if 'start' in ties: open_ties[key] = n_
            else: open_ties.pop(key, None)
    for pos, sym in B['chords']:
        if pos < L + 1e-6: chords.append((t0 + min(pos, L - 0.001) + shift(pos), sym, B['i']))
    t0 += L + sum(n for _, n, _ in pads_here)
# 7) 頭の直し（2026-11-19 みかさん「イントロ〜Aメロで違和感。イントロは4拍目の右手の16分のタラランから始まって、次の小節の1拍目から左のコード」）
#    音源と照らすと、耳コピ譜はイントロ〜Aメロ1（HEAD_END まで）が半拍早く、頭のタラランが抜けていた（間奏1・Aメロ2は合っている）
#    a) HEAD_END より前の音を半拍うしろへ。HEAD_END を越えた左手と、同じ音が重なった右手は捨てる
#    b) リフ1回目の頭2拍は耳コピが崩れているので、リフ2回目の頭2拍を写す
#    c) 頭に1小節足して、4拍目にリフ2回目の前のタララン（右手だけ）を置く
HEAD_END, HEAD_SHIFT, RIFF = 44.0, 0.5, 8.0
have = {(n[0], n[1], n[3]) for n in notes if n[0] >= HEAD_END - 1e-9}
fixed = []
for n in notes:
    if n[0] >= HEAD_END - 1e-9: fixed.append(n); continue
    p = round(n[0] + HEAD_SHIFT, 4)
    if p >= HEAD_END - 1e-9 and (n[3] == 2 or (p, n[1], n[3]) in have): continue
    d = n[2] if n[3] == 1 else min(n[2], HEAD_END - p)
    fixed.append([p, n[1], round(d, 4), n[3]])
riff2 = [[round(n[0] - RIFF, 4), n[1], n[2], n[3]] for n in fixed if RIFF - 1e-9 <= n[0] < RIFF + 2 - 1e-9]
pickup = [[round(n[0] - RIFF + METER, 4), n[1], n[2], 1] for n in fixed if RIFF - 1 - 1e-9 <= n[0] < RIFF - 1e-9 and n[3] == 1]
notes = pickup + [[round(n[0] + METER, 4), n[1], n[2], n[3]] for n in riff2 + [n for n in fixed if n[0] >= 2 - 1e-9]]
chords = [(t + METER, sym, b) for t, sym, b in chords]; marks = [(t + METER, m) for t, m in marks]
bar_map = [(b, t + METER, L) for b, t, L in bar_map]
t0 += METER
total = t0; bars = int(round(total / METER))
assert abs(total - bars * METER) < 1e-6, total
notes.sort(key=lambda n: (n[0], n[1]))
json.dump({'bars': bars, 'meter': METER, 'notes': notes, 'chords': chords, 'marks': marks, 'bar_map': bar_map,
           'kinds_unknown': sorted(kinds_unknown), 'tempo': root.find('.//sound[@tempo]').get('tempo')},
          open(out_json, 'w', encoding='utf-8'), ensure_ascii=False)
reg = {'id': sid, 'bars': bars, 'meter': METER, 'notes': notes}
with open(out_js, 'w', encoding='utf-8') as f:
    f.write('window.PIANO_SCORES=window.PIANO_SCORES||{};\n')
    f.write(f'window.PIANO_SCORES[{json.dumps(sid)}]=' + json.dumps(reg, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(json.dumps({'bars': bars, 'notes': len(notes), 'chords': len(chords), 'marks': [(t / METER + 1, m) for t, m in marks],
                  'first_note': notes[0][0], 'last_note_end': max(n[0] + n[2] for n in notes), 'total_beats': total,
                  'kinds_unknown': sorted(kinds_unknown)}, ensure_ascii=False))
