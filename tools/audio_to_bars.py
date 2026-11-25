# -*- coding: utf-8 -*-
"""音源（m4a・wav）から「小節ごとの表」を作る。耳コピ譜（MusicXML・MIDI）の拍子や小節が当てにならないときに使う。

使い方: ffmpeg -i 曲.m4a -ac 1 -ar 22050 曲.wav
        /opt/homebrew/bin/python3 audio_to_bars.py 曲.wav <拍子=3> <だいたいのテンポ=129> [出力.json]
出るもの（標準出力）: 小節の番号・始まる秒・長さ・いちばん低い音・強い音の名前4つ（％）
  - 拍は librosa の拍の追いかけ。小節の頭は、低い音（60〜190Hz）の立ち上がりが強い拍を選ぶ（途中で拍が1つ余る所は「*」が付く＝息つぎ・ゆれ）
  - コードは、この表の「低い音」と「強い音」を見て人が決める（歌の音も混ざるので、同じ節のくり返しを見比べる）
  - 通した長さ（小節数×拍子÷テンポ）が音源の長さと合うかを最後に確かめる
2026-11-25 「いつも何度でも（木村弓キー）」で作った。耳コピ譜は3拍子の1小節が4拍ぶんに伸びていて使えなかった。
歌のメロディーはこの道具では起こせない（歌の高さの読み取りは長い音しか当たらなかった）。
"""
import sys, json, warnings
import numpy as np, librosa
warnings.filterwarnings('ignore')
src = sys.argv[1]; METER = int(sys.argv[2]) if len(sys.argv) > 2 else 3; BPM = float(sys.argv[3]) if len(sys.argv) > 3 else 120
y, sr = librosa.load(src, sr=22050); hop = 256; fps = sr / hop
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
tempo, bf = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, start_bpm=BPM, tightness=200)
bt = list(librosa.frames_to_time(bf, sr=sr, hop_length=hop)); ibi = float(np.median(np.diff(bt)))
while bt[0] - ibi > -ibi: bt.insert(0, bt[0] - ibi)
while bt[-1] + ibi < len(y) / sr + ibi: bt.append(bt[-1] + ibi)
bt = np.array(bt); N = len(bt)
S = np.abs(librosa.stft(y, n_fft=4096, hop_length=hop)); fr = librosa.fft_frequencies(sr=sr, n_fft=4096)
low = S[(fr > 60) & (fr < 190)].sum(0); lowon = np.maximum(0, np.diff(np.log1p(low), prepend=0))
def peak(t, w=0.06):
    a = max(0, int((t - w) * fps)); b = min(len(lowon), int((t + w) * fps) + 1); return float(lowon[a:b].max()) if b > a else 0.0
r = [peak(t) for t in bt]
# 小節の中の位置を追う: ふつうは次の拍へ。同じ位置に留まる・1つ飛ぶ は罰
PEN = 0.45; sc = np.full((N, METER), -1e9); bk = np.zeros((N, METER), int); sc[0] = [r[0]] + [0] * (METER - 1)
for i in range(1, N):
    for s in range(METER):
        v, p = max((sc[i-1][(s-1) % METER], (s-1) % METER), (sc[i-1][s] - PEN, s), (sc[i-1][(s-2) % METER] - PEN, (s-2) % METER))
        sc[i][s] = v + (r[i] if s == 0 else 0); bk[i][s] = p
s = int(np.argmax(sc[-1])); ph = [0] * N
for i in range(N - 1, -1, -1): ph[i] = s; s = int(bk[i][s])
starts = [i for i, p in enumerate(ph) if p == 0]
cq = np.abs(librosa.cqt(y, sr=sr, hop_length=512, fmin=librosa.note_to_hz('C1'), n_bins=72, bins_per_octave=12)) ** 2; cf = sr / 512
NN = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']; out = []
for k in range(len(starts) - 1):
    i, j = starts[k], starts[k + 1]; t0, t1 = float(bt[i]), float(bt[j]); a, b = int(t0 * cf), int(t1 * cf)
    if a < 0 or b > cq.shape[1] or b <= a: continue
    seg = cq[:, a:b]; lo = seg[12:40].sum(1); cand = [12 + x for x in np.argsort(lo)[::-1][:6] if lo[x] > lo.max() * 0.35]; lowest = min(cand) + 24
    pcs = seg[12:60].reshape(4, 12, -1).sum((0, 2)); pcs = pcs / pcs.sum()
    top = ' '.join('%s%.0f' % (NN[p], pcs[p] * 100) for p in np.argsort(pcs)[::-1][:4])
    out.append({'bar': k + 1, 't0': round(t0, 2), 'len': round(t1 - t0, 2), 'beats': j - i, 'low': NN[lowest % 12] + str(lowest // 12 - 1), 'top': top})
    print('%3d %6.1f 長さ%.2f %s 低い音 %-4s 強い音 %s' % (k + 1, t0, t1 - t0, '*' if j - i != METER else ' ', out[-1]['low'], top))
print('テンポ', float(np.atleast_1d(tempo)[0]), '／拍', N, '／小節', len(out), '／音源の長さ', round(len(y) / sr, 1), '秒')
if len(sys.argv) > 4: json.dump(out, open(sys.argv[4], 'w', encoding='utf-8'), ensure_ascii=False)
