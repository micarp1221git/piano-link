# -*- coding: utf-8 -*-
"""公開中の overdrive-a1 の歌の音だけを入れ替える（ベース・コード打ち・カウントはそのまま）
使い方: python publish5.py <作業フォルダ> <piano-link> <いま入っている読み.json> <入れる読み.json>
5回目 = notes4.json → notes5.json（区切りは歌声専用モデル SOME・高さは4回目）"""
import sys, json
D, R, OLD, NEW = sys.argv[1:5]; path = R + "/lesson-data-overdrive-audio.js"
s = open(path).read(); d = json.loads(s[s.index("]=") + 2:s.rindex(";")])
vo = json.load(open(D + "/" + OLD))["vo"]; vn = json.load(open(D + "/" + NEW))["vo"]
old = {(round(a, 3), p) for a, p, l in vo}
keep = [n for n in d["notes"] if not (n[3] == 1 and (round(n[0], 3), n[1]) in old)]
print("今の音", len(d["notes"]), "／歌として外す", len(d["notes"]) - len(keep), "（いまの歌は", len(vo), "）／入れる", len(vn))
if len(d["notes"]) - len(keep) != len(vo): sys.exit("歌の音の数が合わないので書きません")
ref = next(n for n in d["notes"] if n[3] == 1 and (round(n[0], 3), n[1]) in old)
d["notes"] = sorted(keep + [[a, p, l, 1] + ref[4:] for a, p, l in vn])
open(path, "w").write("window.PIANO_SCORES=window.PIANO_SCORES||{};\nwindow.PIANO_SCORES[\"%s\"]=" % d["id"] + json.dumps(d, separators=(",", ":")) + ";\n")
print("書いた", len(d["notes"]))
