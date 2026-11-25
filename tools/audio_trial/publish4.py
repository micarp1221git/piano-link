# -*- coding: utf-8 -*-
"""4回目: 公開中の overdrive-a1 の歌の音だけを notes4（しゃくりをまとめた読み）に入れ替える。ベース・コード打ち・カウントはそのまま"""
import sys, json
D, R = sys.argv[1], sys.argv[2]; path = R + "/lesson-data-overdrive-audio.js"
s = open(path).read(); d = json.loads(s[s.index("]=") + 2:s.rindex(";")])
v3 = json.load(open(D + "/notes3.json"))["vo"]; v4 = json.load(open(D + "/notes4.json"))["vo"]
old = {(round(a, 3), p) for a, p, l in v3}
keep = [n for n in d["notes"] if not (n[3] == 1 and (round(n[0], 3), n[1]) in old)]
print("今の音", len(d["notes"]), "／歌として外す", len(d["notes"]) - len(keep), "（3回目の歌は", len(v3), "）／入れる", len(v4))
if len(d["notes"]) - len(keep) != len(v3): sys.exit("歌の音の数が合わないので書きません")
ref = next(n for n in d["notes"] if n[3] == 1 and (round(n[0], 3), n[1]) in old)
d["notes"] = sorted(keep + [[a, p, l, 1] + ref[4:] for a, p, l in v4])
open(path, "w").write("window.PIANO_SCORES=window.PIANO_SCORES||{};\nwindow.PIANO_SCORES[\"%s\"]=" % d["id"] + json.dumps(d, separators=(",", ":")) + ";\n")
print("書いた", len(d["notes"]))
