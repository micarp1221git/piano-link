// いつかのメリークリスマス: 左手が「低い音1つを伸ばすだけ」の小節を、コード譜から分散和音に作り直す。
// 2026-11-19 みかさん「イントロの後、Aメロに入るときに急にコード感がなくなる。左手がベース音だけしか弾いてない感じ。すごい寂しい」
// 形はイントロ（1〜7小節目）と同じ「8分・8分・4分」を2拍ごと。同じコードが4拍続く小節は、後ろの2拍を1つ上の形に。
// 使い方: リポジトリの直下で python3 -m http.server 8766 --bind 127.0.0.1 を立ててから  node tools/merry_left_hand.js <puppeteer の場所> [--write]
//   9〜12小節目（イントロ2）と13小節目は tools/merry_a1_entry.js が作る（11/19）ので、ここでは触らない。もう作り直してある小節（和音や細かい音がある小節）も触らない＝何回かけても同じ結果
const fs = require('fs'), path = require('path');
const puppeteer = require(process.argv[2]);
const write = process.argv.includes('--write');
(async () => {
  const b = await puppeteer.launch({ headless: 'new' }); const p = await b.newPage();
  await p.goto('http://127.0.0.1:8766/?practice=merry&t=' + Date.now(), { waitUntil: 'networkidle2' });
  const out = await p.evaluate(() => {
    const song = cleanSong(MERRY_LESSON), score = window.PIANO_SCORES['merry-v1'], M = 4;
    const lh = bar => score.notes.filter(n => n[3] === 2 && n[0] >= bar * M - 1e-6 && n[0] < (bar + 1) * M - 1e-6);
    const thin = bar => { const ns = lh(bar); if (!ns.length || ns.length > 4) return false; const on = new Set(ns.map(n => n[0])); return on.size === ns.length && ns.every(n => n[2] >= 0.95) && Math.max(...ns.map(n => n[1])) <= 64 && Math.min(...ns.map(n => n[1])) >= 38; };
    const chordAt = beat => { let c = null; for (const x of song.chords) { if (x.bar * M + x.beat > beat + 1e-6) break; c = x; } return c; };
    const place = (pc, lo) => { let m = lo + ((pc - lo) % 12 + 12) % 12; return m; };
    const changed = [], add = [];
    for (let bar = 0; bar < score.bars; bar++) {
      if (bar >= 8 && bar <= 11) continue;
      // 対象は Aメロ・Bメロ・間奏（13〜28・46〜61・79〜94・113〜120小節目）と、アウトロ（121〜135・11/19 みかさん「左手が全音符しか弾いてないのも違和感」）。サビの終わりの伸ばし（44・77・78・110）は伸ばしのまま
      if (!((bar >= 12 && bar <= 27) || (bar >= 45 && bar <= 60) || (bar >= 78 && bar <= 93) || (bar >= 112 && bar <= 119) || (bar >= 120 && bar <= 134))) continue;
      if (!thin(bar)) continue;
      // この小節の中のコードの区切り
      // コードの変わり目は、元の左手が音を弾き直していた拍だけ使う（13小節目はコード譜に Gmaj7→Cmaj7 とあるが、元の左手はソを4拍伸ばしていた＝コード譜の記号のずれ）
      const onsets = new Set(lh(bar).map(n => Math.round((n[0] - bar * M) * 2) / 2));
      const cuts = [0, ...song.chords.filter(c => c.bar === bar && c.beat > 0 && onsets.has(c.beat)).map(c => c.beat), M].filter((v, i, a) => a.indexOf(v) === i).sort((x, y) => x - y);
      const made = [];
      for (let i = 0; i < cuts.length - 1; i++) {
        const from = cuts[i], len = cuts[i + 1] - from, c = chordAt(bar * M + from), ch = c && parseChord(c.sym);
        if (!ch || ch.rest) continue;
        const bass = place(ch.bass ?? ch.root, 43);                       // G2〜F#3
        const pcs = [...new Set(ch.iv.slice(0, 3).map(iv => (ch.root + iv) % 12))].filter(pc => pc !== bass % 12);
        const ups = pcs.map(pc => place(pc, bass + 1)).sort((x, y) => x - y);
        const t1 = ups[0] ?? bass + 7, t2 = ups[1] ?? bass + 12;
        const at = off => bar * M + from + off;
        if (len === 4) made.push([at(0), bass, .5], [at(.5), t1, .5], [at(1), t2, 1], [at(2), t1, .5], [at(2.5), t2, .5], [at(3), bass + 12, 1]);
        else if (len === 3) made.push([at(0), bass, .5], [at(.5), t1, .5], [at(1), t2, 1], [at(2), bass, .5], [at(2.5), t1, .5]);
        else if (len === 2) made.push([at(0), bass, .5], [at(.5), t1, .5], [at(1), t2, 1]);
        else if (len === 1) made.push([at(0), bass, .5], [at(.5), t1, .5], [at(.5), t2, .5]);
        else made.push([at(0), bass, len]);
      }
      if (!made.length) continue;
      changed.push(bar + 1); made.forEach(m => add.push([m[0], m[1], m[2], 2]));
    }
    const drop = new Set(changed.map(b => b - 1));
    const keep = score.notes.filter(n => !(n[3] === 2 && drop.has(Math.floor((n[0] + 1e-6) / M))));
    const notes = keep.concat(add).sort((a, b) => a[0] - b[0] || a[3] - b[3] || a[1] - b[1]);
    return { changed, score: { ...score, notes } };
  });
  await b.close();
  console.log('作り直す小節:', out.changed.join(' '), '（' + out.changed.length + '小節）');
  if (write) {
    const f = path.join(__dirname, '..', 'lesson-data-merry.js');
    fs.writeFileSync(f, 'window.PIANO_SCORES=window.PIANO_SCORES||{};\nwindow.PIANO_SCORES["merry-v1"]=' + JSON.stringify(out.score) + ';\n');
    console.log('書いた', f);
  }
})();
