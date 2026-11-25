# -*- coding: utf-8 -*-
"""odtest＝音源だけで読んだ3回目（overdrive-a1）／odmix＝右手はいまのレッスン版・左手は音源のベース（overdrive-m1）"""
import sys, json
D, R = sys.argv[1], sys.argv[2]
def load(path):
    s = open(path).read(); return json.loads(s[s.index("]=") + 2:s.rindex(";")])
def save(path, sid, bars, notes):
    open(path, "w").write("window.PIANO_SCORES=window.PIANO_SCORES||{};\nwindow.PIANO_SCORES[\"%s\"]=" % sid + json.dumps({"id": sid, "bars": bars, "meter": 4, "notes": sorted(notes)}, separators=(",", ":")) + ";\n")
a3 = load(D + "/out3.js"); v1 = load(R + "/lesson-data-overdrive.js")
save(R + "/lesson-data-overdrive-audio.js", "overdrive-a1", a3["bars"], a3["notes"])
mix = [n for n in v1["notes"] if n[3] == 1] + [n for n in a3["notes"] if n[3] in (0, 2)]
save(R + "/lesson-data-overdrive-mix.js", "overdrive-m1", v1["bars"], mix)
print("a1", len(a3["notes"]), "m1", len(mix))
