# -*- coding: utf-8 -*-
"""声だけの音から、言葉の始まりの時刻を取る（whisper の単語ごとの時刻）。歌詞そのものは外に出さず、時刻と文字数だけ words.json に置く"""
import sys, json, mlx_whisper
D = sys.argv[1]
r = mlx_whisper.transcribe(D + "/vocals.wav", path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="ja", word_timestamps=True, condition_on_previous_text=False)
out = []
for s in r["segments"]:
    for w in s.get("words", []):
        t = w["word"].strip()
        if t: out.append([round(float(w["start"]), 3), round(float(w["end"]), 3), len(t), round(float(w.get("probability", 0)), 2)])
json.dump(out, open(D + "/words.json", "w"))
print("区切り", len(out), "／文字数の合計", sum(o[2] for o in out), "／最初と最後の時刻", out[0][0], out[-1][1])
