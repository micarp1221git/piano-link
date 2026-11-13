# -*- coding: utf-8 -*-
"""耳コピ譜（MusicXML・ピアノ2段）から、レッスン版の曲データを作る。

使い方: python3 musicxml_to_lesson.py <譜面.xml> <score_id> <出力.js> <曲名>
  出力.js   … window.PIANO_SCORES[score_id] = {id,bars,meter,notes}
  標準出力  … 入れておく曲（PRESET_TEXTS）の1行（コード譜テキスト）と区切り
notes は [拍(4分音符=1), MIDI, 長さ(拍), 手(1=上の段/2=下の段)]。タイはつなげる。
2026-11-13 「いつかのメリークリスマス」を足すときに作った（みかさんの依頼）。
"""
import sys, json
import xml.etree.ElementTree as ET

src, sid, out_js, title = sys.argv[1:5]
root = ET.parse(src).getroot()
part = root.find('part')
STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
KIND = {'major': '', 'minor': 'm', 'dominant': '7', 'major-seventh': 'maj7', 'minor-seventh': 'm7',
        'diminished': 'dim', 'augmented': 'aug', 'suspended-fourth': 'sus4', 'major-sixth': '6',
        'minor-sixth': 'm6', 'half-diminished': 'm7-5', 'diminished-seventh': 'dim7'}

div = 1; beats = 4; beat_type = 4
notes, chords, marks = [], [], []
open_ties = {}  # (midi, hand) -> note
bar_start = 0.0
measures = part.findall('measure')
for mi, m in enumerate(measures):
    cur = 0.0; mlen = 0.0
    for el in m:
        tag = el.tag
        if tag == 'attributes':
            d = el.find('divisions')
            if d is not None: div = int(d.text)
            t = el.find('time')
            if t is not None:
                beats = int(t.find('beats').text); beat_type = int(t.find('beat-type').text)
        elif tag == 'backup':
            cur -= int(el.find('duration').text) / div
        elif tag == 'forward':
            cur += int(el.find('duration').text) / div; mlen = max(mlen, cur)
        elif tag == 'direction':
            r = el.find('direction-type/rehearsal')
            if r is not None and r.text: marks.append((mi, r.text.strip()))
        elif tag == 'harmony':
            st = el.find('root/root-step').text
            alt = el.find('root/root-alter'); alt = int(float(alt.text)) if alt is not None else 0
            k = el.find('kind'); kind = KIND.get(k.text.strip(), '') if k is not None and k.text else ''
            acc = lambda a: '#' if a > 0 else 'b' if a < 0 else ''  # 譜面どおりの書き方（F#m7 など）
            sym = st + acc(alt) + kind
            b = el.find('bass/bass-step')
            if b is not None:
                ba = el.find('bass/bass-alter'); ba = int(float(ba.text)) if ba is not None else 0
                sym += '/' + b.text + acc(ba)
            chords.append((mi, cur, sym))
        elif tag == 'note':
            dur_el = el.find('duration')
            if dur_el is None: continue  # 装飾音
            dur = int(dur_el.text) / div
            is_chord = el.find('chord') is not None
            if is_chord: cur -= last_dur
            staff = el.find('staff'); hand = int(staff.text) if staff is not None else 1
            p = el.find('pitch')
            if p is not None:
                alt = el.find('pitch/alter'); alt = int(float(alt.text)) if alt is not None else 0
                midi = 12 * (int(p.find('octave').text) + 1) + STEP[p.find('step').text] + alt
                start = bar_start + cur
                bar_len_now = beats * 4 / beat_type
                if cur >= bar_len_now - 1e-6:  # 拍子より長い小節（変換の誤り）ははみ出た音を捨てる
                    cur += dur; last_dur = dur; mlen = max(mlen, cur); continue
                dur_in = min(dur, bar_len_now - cur)
                ties = [t.get('type') for t in el.findall('tie')]
                key = (midi, hand)
                if 'stop' in ties and key in open_ties:
                    n = open_ties[key]; n[2] = round(start + dur_in - n[0], 4)
                    if 'start' not in ties: del open_ties[key]
                else:
                    n = [round(start, 4), midi, round(dur_in, 4), hand]
                    notes.append(n)
                    if 'start' in ties: open_ties[key] = n
            cur += dur; last_dur = dur; mlen = max(mlen, cur)
    bar_len = beats * 4 / beat_type
    bar_start += bar_len  # 小節は拍子どおりの長さで並べる（弱起は無い前提・下で確かめる）
    if abs(mlen - bar_len) > 1e-6 and mlen > 0:
        print(f'⚠ 小節{mi}: 中身 {mlen} 拍・拍子 {bar_len} 拍', file=sys.stderr)

bars = len(measures); meter = beats
notes.sort(key=lambda n: (n[0], n[1]))
reg = {'id': sid, 'bars': bars, 'meter': meter, 'notes': notes}
with open(out_js, 'w', encoding='utf-8') as f:
    f.write('window.PIANO_SCORES=window.PIANO_SCORES||{};\n')
    f.write(f'window.PIANO_SCORES[{json.dumps(sid)}]=' + json.dumps(reg, ensure_ascii=False, separators=(',', ':')) + ';\n')

# コード譜テキスト（1拍 = '-' で埋める書き方は使わず、小節内に複数あれば並べる）
by_bar = {}
for mi, pos, sym in chords: by_bar.setdefault(mi, []).append((pos, sym))
mark_at = dict(marks)
lines, cur_line = [], ''
prev = None
for mi in range(bars):
    if mi in mark_at:
        if cur_line: lines.append(cur_line + ' |')
        cur_line = f'[{mark_at[mi]}]'
    cs = by_bar.get(mi, [])
    if not cs:
        cell = '%' if prev else 'N.C.'
    elif len(cs) == 1 and cs[0][0] < 1e-6:
        cell = cs[0][1]
    else:
        # 拍ごとに置く（'-' は前のコードを伸ばす）
        slots = ['-'] * meter
        if cs[0][0] > 1e-6: slots[0] = prev or 'N.C.'
        for pos, sym in cs: slots[min(meter - 1, int(round(pos)))] = sym
        cell = ' '.join(slots)
    if cs: prev = cs[-1][1]
    cur_line += ' | ' + cell
lines.append(cur_line + ' |')
print(json.dumps({'bars': bars, 'meter': meter, 'notes': len(notes), 'chords': len(chords),
                  'marks': marks, 'first_note': notes[0][0] if notes else None,
                  'tempo': root.find('.//sound[@tempo]').get('tempo') if root.find('.//sound[@tempo]') is not None else None},
                 ensure_ascii=False))
print('\\n'.join(lines))
