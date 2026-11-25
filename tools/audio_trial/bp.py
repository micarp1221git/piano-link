# -*- coding: utf-8 -*-
"""basic-pitch で声だけの音から音符を読む → notes_bp.json（秒・MIDI・強さ）。設定を変えて何通りか出す"""
import sys, json, itertools
from basic_pitch.inference import predict, Model
from basic_pitch import ICASSP_2022_MODEL_PATH
D = sys.argv[1]; model = Model(ICASSP_2022_MODEL_PATH); out = {}
for on, fr, ml in itertools.product((0.3, 0.5, 0.6), (0.3, 0.4), (80, 127.7)):
    _, _, ev = predict(D + "/vocals.wav", model, onset_threshold=on, frame_threshold=fr, minimum_note_length=ml, minimum_frequency=160, maximum_frequency=1000, melodia_trick=True)
    out["%s_%s_%s" % (on, fr, ml)] = sorted([float(s), float(e), int(p), float(a)] for s, e, p, a, _ in ev)
    print(on, fr, ml, len(ev))
json.dump(out, open(D + "/notes_bp.json", "w"))
