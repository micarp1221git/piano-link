// いつかのメリークリスマス: イントロ2（9〜12小節目）の左手を分散和音にし、Aメロ1の入りを音源どおりに直す。
// 2026-11-19 みかさん「イントロはアルペジオじゃないですか？ 12小節目の4拍目からAメロが始まります」
// 音源（~/Downloads の m4a）と照らした結果:
//  ・13小節目の頭の低音はド（Cmaj7）。曲データの左手とコード譜はソ（Gmaj7）になっていた
//  ・歌は12小節目の3拍目ウラから ソ・シ・レ と入り、13小節目は レー・レ・ミー・シ・ラ・ソ。曲データは頭の2音が無く、13小節目が半拍おくれていた
//    （同じ節の2回目＝16〜17小節目は音源と合っていたので、その形にそろえた）
// 何回かけても同じ結果。使い方: node tools/merry_a1_entry.js [--write]
const fs = require('fs'), path = require('path');
const f = path.join(__dirname, '..', 'lesson-data-merry.js');
global.window = {}; require(f);
const score = window.PIANO_SCORES['merry-v1'], M = 4, at = (bar, beat) => (bar - 1) * M + beat - 1;
const inBar = (n, a, b) => n[0] >= at(a, 1) - 1e-6 && n[0] < at(b + 1, 1) - 1e-6;
let notes = score.notes.filter(n =>
  !(n[3] === 2 && inBar(n, 9, 13)) &&                      // 左手 9〜13小節目
  !(n[3] === 1 && inBar(n, 13, 13)) &&                     // 右手 13小節目（歌の節）
  !(n[3] === 1 && inBar(n, 12, 12) && n[1] >= 65));        // 右手 12小節目の歌の入り（前に足したぶん）
const L = (bar, beat, midi, len) => notes.push([at(bar, beat), midi, len, 2]);
const R = (bar, beat, midi, len) => notes.push([at(bar, beat), midi, len, 1]);
const whole = (bar, a, b, c) => { L(bar, 1, a, .5); L(bar, 1.5, b, .5); L(bar, 2, c, 1); L(bar, 3, b, .5); L(bar, 3.5, c, .5); L(bar, 4, a + 12, 1); };
const half = (bar, beat, a, b, c) => { L(bar, beat, a, .5); L(bar, beat + .5, b, .5); L(bar, beat + 1, c, 1); };
whole(9, 48, 52, 55);            // Cmaj7: ド ミ ソ
whole(10, 47, 50, 54);           // Bm7: シ レ ファ#
half(11, 1, 45, 48, 52);         // Am7: ラ ド ミ
half(11, 3, 50, 54, 57);         // D: レ ファ# ラ
whole(12, 43, 47, 50);           // Gmaj7: ソ シ レ
whole(13, 48, 52, 55);           // Cmaj7（17小節目と同じ）
R(12, 3.5, 67, .5); R(12, 4, 71, .5); R(12, 4.5, 74, .5);                                   // ソ・シ・レ
R(13, 1, 74, 1); R(13, 2, 74, .5); R(13, 2.5, 76, 1); R(13, 3.5, 71, .5); R(13, 4, 69, .5); R(13, 4.5, 67, .5);
notes.sort((a, b) => a[0] - b[0] || a[3] - b[3] || a[1] - b[1]);
console.log('音の数', score.notes.length, '→', notes.length);
if (process.argv.includes('--write')) {
  fs.writeFileSync(f, 'window.PIANO_SCORES=window.PIANO_SCORES||{};\nwindow.PIANO_SCORES["merry-v1"]=' + JSON.stringify({ ...score, notes }) + ';\n');
  console.log('書いた', f);
}
