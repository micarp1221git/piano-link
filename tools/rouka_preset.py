# -*- coding: utf-8 -*-
# 中間.json から コード譜テキスト（譜面の記号のまま＝preset.txt／名前を付け直した版＝preset_named.txt）と 区切り.json を作る
import sys, json
d = json.load(open(sys.argv[1], encoding='utf-8')); outdir = sys.argv[2]
bars, M = d['bars'], d['meter']
# 譜面のコード記号がずれていた小節（イントロ1〜4・Aメロ1の6と10）は、左手の最低音から付け直した
CHORD_FIX = {1: 'Db - Ab/C Bbm7', 2: 'Ab Gb - -', 3: 'Db - Ab/C Bbm7', 4: 'Ab Gb - -', 6: 'Ab Gb - -', 10: 'Ab Gb - -'}
by = {}
for t, sym, *_ in d['chords']: by.setdefault(int(t // M), []).append((t - (t // M) * M, sym))
cells = []; prev = None
for b in range(bars):
    cs = sorted(by.get(b, []))
    if b + 1 in CHORD_FIX:
        cell = CHORD_FIX[b + 1]; prev = [x for x in cell.split() if x != '-'][-1]
    else:
        if not cs: cell = '%' if prev else 'N.C.'
        elif len(cs) == 1 and cs[0][0] < 1e-6: cell = cs[0][1]
        else:
            slots = ['-'] * M
            if cs[0][0] > 1e-6: slots[0] = prev or 'N.C.'
            for pos, sym in cs: slots[min(M - 1, int(round(pos)))] = sym
            cell = ' '.join(slots)
        if cs: prev = cs[-1][1]
    cells.append(cell)
def text(secs):
    return '\\n'.join('[%s] | %s |' % (n, ' | '.join(cells[a - 1:e])) for n, a, e in secs)
orig = [('A', 1, 12), ('B', 13, 21), ('C', 22, 29), ('D', 30, 33), ('E', 34, 41), ('F', 42, 49), ('G', 50, 57), ('H', 58, 65),
        ('I', 66, 77), ('J', 78, 85), ('K', 86, 89), ('L', 90, 94)]
named = [('イントロ', 1, 4), ('Aメロ1', 5, 12), ('Bメロ1', 13, 21), ('サビ1', 22, 29), ('間奏1', 30, 33), ('Aメロ2', 34, 41),
         ('Bメロ2', 42, 49), ('サビ2', 50, 57), ('Cメロ', 58, 65), ('間奏2', 66, 69), ('落ちサビ', 70, 77), ('大サビ1', 78, 85),
         ('大サビ2', 86, 89), ('アウトロ', 90, 94)]
for s in (orig, named):
    assert s[0][1] == 1 and s[-1][2] == bars and all(s[i][2] + 1 == s[i + 1][1] for i in range(len(s) - 1))
    assert all(len(n) <= 12 for n, _, _ in s)
open(outdir + '/preset.txt', 'w', encoding='utf-8').write(text(orig) + '\n')
open(outdir + '/preset_named.txt', 'w', encoding='utf-8').write(text(named) + '\n')
json.dump([[n, a, e, cells[a - 1:e]] for n, a, e in named], open(outdir + '/rouka_secs.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(text(named).replace('\\n', '\n'))
