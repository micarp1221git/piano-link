# -*- coding: utf-8 -*-
"""「いつも何度でも（木村弓キー）」の譜面データ（lesson-data-itsumo.js）を作る。
使い方: /opt/homebrew/bin/python3 itsumo_score.py ../lesson-data-itsumo.js
メロディーは音源（いつも何度でも・木村弓.m4a）の歌の高さを読み、同じ節のくり返しでそろう音を採った（2026-11-25）。
  1小節＝8分6つ。音は (8分の位置, MIDI, 8分いくつ分)。ヘ長調・歌の高さ（ド4=60）
  あやしい所: 最後のAメロの「Bb | F/A」を3回くり返す所（同じ2小節を3回置いた）・ラララの間奏と後奏（Bメロと同じ節を置いた）・アウトロ（メロディーなし）
手の番号 0 はカウント（1小節目に3つ・2小節目に2つ。歌は2小節目の3拍目から）。
"""
import sys, json
C, D, E, F, G, A, Bb, C2 = 60, 62, 64, 65, 67, 69, 70, 72
PA = [[(0, A, 1), (1, F, 1), (2, C2, 2), (4, C2, 1), (5, A, 1)], [(0, G, 2), (2, C2, 2), (4, G, 2)],
      [(0, F, 1), (1, D, 1), (2, A, 1), (3, Bb, 1), (4, A, 1), (5, F, 1)], [(0, E, 4), (4, E, 2)],
      [(1, D, 1), (2, E, 1), (3, F, 2), (5, G, 1)], [(0, A, 3), (3, F, 1), (4, G, 1), (5, A, 1)], [(0, Bb, 2), (2, A, 4)], [(0, G, 4)]]
PA2 = [PA[0], [(0, G, 2), (2, G, 2), (4, G, 2)], [(0, F, 1), (1, D, 3), (4, F, 2)], [(0, C, 4), (5, C, 1)],
       [(0, D, 2), (2, E, 1), (3, F, 2), (5, G, 1)], PA[5], [(0, Bb, 3), (3, A, 1), (4, G, 1), (5, F, 1)], [(0, F, 4)]]
PB = [[(0, C2, 6)], [(0, C2, 2), (2, G, 2), (4, C2, 1), (5, Bb, 1)], [(0, A, 3), (3, Bb, 1), (4, A, 2)],
      [(0, A, 2), (2, A, 1), (3, Bb, 1), (4, A, 1), (5, G, 1)], [(0, F, 2), (2, G, 1), (3, F, 2), (5, E, 1)],
      [(0, D, 3), (3, E, 1), (4, F, 1), (5, G, 1)], [(0, G, 3), (3, A, 3)], [(0, G, 4)]]
PB2 = [PB[0], PB[1], PB[2], [(0, A, 1), (1, Bb, 1), (2, A, 1), (3, G, 1), (4, F, 1), (5, E, 1)], PA[4], PA[5], [(0, G, 5), (5, F, 1)], [(0, F, 4)]]
PAX = PA2[:4] + [PA2[4], PA2[5]] * 3 + PA2[6:]
UP_A, UP_B = [(4, F, 1), (5, G, 1)], [(4, A, 1), (5, Bb, 1)]   # 次の節へ入る2音（3拍目）
bars = {}
def put(start, phrase):
    for i, b in enumerate(phrase): bars.setdefault(start + i, []).extend(b)
def pick(bar, up): bars.setdefault(bar, []).extend(up)
pick(2, UP_A)
put(3, PA); pick(10, UP_A); put(11, PA2); pick(19, UP_B)
put(20, PB); pick(27, UP_B); put(28, PB2); pick(37, UP_A)
put(38, PA); pick(45, UP_A); put(46, PA2); pick(55, UP_B)
put(56, PB); pick(63, UP_B); put(64, PB2); pick(74, UP_A)
put(75, PA); pick(82, UP_A); put(83, PA2); pick(91, UP_B)
put(92, PB); pick(99, UP_B); put(100, PB2); pick(109, UP_A)
put(110, PA); pick(117, UP_A); put(118, PAX); pick(132, UP_B)
put(133, PB); pick(140, UP_B); put(141, PB2)
BARS, METER = 154, 3
notes = [[0, 84, 0.12, 0], [1, 79, 0.12, 0], [2, 79, 0.12, 0], [3, 84, 0.12, 0], [4, 79, 0.12, 0]]
for bar, ns in sorted(bars.items()):
    assert 1 <= bar <= BARS
    used = set()
    for s, m, l in sorted(ns):
        assert s + l <= 6 and not (set(range(s, s + l)) & used), (bar, ns); used |= set(range(s, s + l))
        notes.append([(bar - 1) * METER + s / 2, m, l / 2, 1])
notes.sort(key=lambda n: (n[0], n[1]))
reg = {'id': 'itsumo-v1', 'bars': BARS, 'meter': METER, 'notes': notes}
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write('window.PIANO_SCORES=window.PIANO_SCORES||{};\n')
    f.write('window.PIANO_SCORES["itsumo-v1"]=' + json.dumps(reg, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('bars', BARS, 'notes', len(notes), 'melody bars', len(bars))
