/* Quarter-note beat units throughout. This module is shared by both peers. */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.LessonCore = api;
})(typeof window !== 'undefined' ? window : this, function() {
  'use strict';
  const EPS = 1e-7;
  const RH = ['song','score','q','e','arp','hold','off'];
  const LH = ['kizami','score','groove','q','back','e','arp','h','w','dot','off'];
  // 2026-11-17 みかさん「1拍目に低い音があるとアクセントが来る。裏でとるリズムは2拍目と4拍目」→ back＝1・3拍目に小さめの低音、2・4拍目に和音
  const isBack = (x,meter) => meter===4 ? x%2===1 : x>0;
  function fields(o, bars, meter) {
    // 2026-11-13 曲ごとの譜面データ（window.PIANO_SCORES）に対応。node のテストでは表が無いので つつみ込む…だけ知っている
    const table = (typeof window !== 'undefined' && window.PIANO_SCORES) || {};
    const known = table[o.scoreId] || (o.scoreId === 'tsutsumi-v2' ? {bars:112, meter:4} : null);
    const attached = !!known && meter === known.meter;
    const max = known ? known.bars : 0;
    return {
      scoreId: attached ? o.scoreId : null,
      scoreMap: attached ? Array.from({length:bars},(_,i) => {
        const v = Array.isArray(o.scoreMap) ? o.scoreMap[i] : i;
        return Number.isInteger(v) && v >= 0 && v < max ? v : -1;
      }) : [],
      rh: RH.includes(o.rh) && (attached || !['score','song'].includes(o.rh)) ? o.rh : 'q',
      lh: LH.includes(o.lh) && (attached || !['score','groove','kizami'].includes(o.lh)) ? o.lh : 'q',
      // 2026-11-19 このMacの中だけの版（Vault 20261109_レッスン版）から移した: 歌に合わせる右手・この曲の刻み・はね具合
      vocalRh: ['comp','guide','soft','off'].includes(o.vocalRh) ? o.vocalRh : 'comp',
      swing: ['straight','light','hard'].includes(o.swing) ? o.swing : 'light',
      leadBars: [0,1,2].includes(+o.leadBars) ? +o.leadBars : 2,
      // 2026-11-19 みかさん「サビまでで終わるのはいいけど、次の間奏の頭の1、2小節は流しておいてほしい」＝弾く順番の最後のあと、続きを何小節か足して止まる
      tailBars: [0,1,2,4].includes(+o.tailBars) ? +o.tailBars : 0,
      click: o.click === true, // 2026-11-17 みかさん「クリックオンもあるといいな」＝曲の間ずっと拍ごとに鳴らす
      rightVolume: Number.isFinite(+o.rightVolume) ? Math.max(0,Math.min(100,+o.rightVolume)) : 75,
      leftVolume: Number.isFinite(+o.leftVolume) ? Math.max(0,Math.min(100,+o.leftVolume)) : 75
    };
  }
  // A bar is "singing" unless its section is marked sing:false (イントロ・間奏・アウトロなど).
  function singAt(song, bar) {
    const s = song.sections.find(s => bar >= s.start && bar <= s.end);
    return s ? s.sing !== false : true;
  }
  // 「この曲の刻み」= 楽譜冒頭の「リズム型」1小節ぶん(16分グリッド)。はね具合は3段階。
  // 刻みは曲ごとに違うので、譜面データ(score.kizami)が持っていればそれを使い、無ければ下の既定(つつみ込むように…)。
  // パターンの各音は [位置, 長さ, 度数?]。度数: なし/'r'=ベース音 '5'=5度 '10'=10度(3度+オクターブ)。
  // 拍の終わり際(off%1 > .7)の音は、次の拍のコードを先取りして鳴らす。
  // つつみ込むように…の下段: 4分 → 3拍目の直前に16分の先取り →「ド・ドゥン」→ 8分 → 次の小節の頭への先取り。
  // 上段: 8分の刻みと、2・4拍目の後ろの「タカ」。
  // straight=楽譜どおりの16分 / light=16分の裏を3連の位置へ / hard=8分の裏も付点の位置へ。
  const KIZAMI = {
    straight: {
      bass:  [[0,1],[1.75,.25],[2,.5],[2.5,.5],[3.75,.25]],
      chord: [[0,.5],[.5,.5],[1,.5],[1.5,.25],[1.75,.25],[2,.5],[2.5,.5],[3,.5],[3.5,.25],[3.75,.25]]
    },
    light: {
      bass:  [[0,1],[1+5/6,1/6],[2,.5],[2.5,.5],[3+5/6,1/6]],
      chord: [[0,.5],[.5,.5],[1,.5],[1.5,1/3],[1+5/6,1/6],[2,.5],[2.5,.5],[3,.5],[3.5,1/3],[3+5/6,1/6]]
    },
    hard: {
      bass:  [[0,1],[1.75,.25],[2,.5],[2.75,.25],[3.75,.25]],
      chord: [[0,.7],[.75,.25],[1,.5],[1.5,.25],[1.75,.25],[2,.7],[2.75,.25],[3,.5],[3.5,.25],[3.75,.25]]
    }
  };
  function mappedNotes(song, score) {
    if (song.scoreId !== score?.id || song.meter !== score.meter) return [];
    const out = [], last = new Map();
    song.scoreMap.forEach((source,bar) => {
      if (source < 0) return;
      const lo = source*song.meter, hi=lo+song.meter;
      score.notes.forEach((n,id) => {
        const a=Math.max(n[0],lo), b=Math.min(n[0]+n[2],hi);
        if (b-a <= EPS) return;
        const at=bar*song.meter+a-lo, prev=last.get(id);
        if (prev && Math.abs(prev[0]+prev[2]-at)<EPS && source === song.scoreMap[bar-1]+1) prev[2] += b-a;
        else { const note=[at,n[3]===0?n[1]:n[1]+song.key,b-a,n[3],n[3]===1?.63:n[3]===0?.5:.7]; out.push(note); last.set(id,note); } // 手の番号0＝譜面に置いたカウント（キーを変えても音の高さはそのまま）
      });
    });
    return out.sort((a,b)=>a[0]-b[0] || a[1]-b[1]);
  }
  function chordAt(song, beat) {
    let c=null;
    for (const x of song.chords) { if (x.bar*song.meter+x.beat>beat+EPS) break; c=x; }
    return c;
  }
  function rhythm(mode,meter) {
    if (mode==='q'||mode==='back') return Array.from({length:meter},(_,i)=>i);
    if (mode==='e'||mode==='arp') return Array.from({length:meter*2},(_,i)=>i/2);
    if (mode==='h') return [0,2].filter(x=>x<meter);
    if (mode==='dot') return [0,1.5,2].filter(x=>x<meter);
    return [0];
  }
  // パターンの度数('r'/'5'/'10')をそのコードの半音数に直す。5度・10度がコードに無い形(sus4・分数コード)は中の音から選ぶ。
  function degreeAdd(ch, deg) {
    if (!deg || deg === 'r') return 0;
    const base = ch.bass ?? ch.root;
    const tones = new Set(ch.iv.map(iv => (ch.root + iv) % 12));
    if (deg === '5') {
      if (tones.has((base + 7) % 12)) return 7;
      for (let t = 5; t <= 11; t++) if (tones.has((base + t) % 12)) return t;
      return 7;
    }
    if (deg === '10') {
      if (ch.bass != null && ch.bass !== ch.root) return 12;
      return 12 + (ch.iv.includes(4) ? 4 : ch.iv.includes(3) ? 3 : ch.iv.includes(5) ? 5 : 7);
    }
    return 0;
  }
  function notesForSong(song,score,parseChord) {
    const mapped = mappedNotes(song,score), out=[];
    const total = song.bars*song.meter;
    // 2026-11-18 みかさん「11小節目にカンカンカンカンとカウントを」＝譜面に手の番号0で置いたカウントは、右手・左手の設定に関係なく鳴らす
    out.push(...mapped.filter(n=>n[3]===0));
    const KZBook = (score && score.id === song.scoreId && score.kizami) || KIZAMI;
    const KZ = KZBook[song.swing] || KZBook.light || KIZAMI.light;
    const grooveBars = (pattern, onNote) => {
      for (let bar=0; bar<song.bars; bar++) for (const [off,dur,deg] of pattern) {
        const p=bar*song.meter+off, ahead=off%1>.7;
        const c=chordAt(song, ahead ? Math.floor(p)+1 : p), ch=c&&parseChord(c.sym);
        if (ch && !ch.rest && p+EPS < total) onNote(bar,p,Math.min(dur,total-p),ch,ahead,deg);
      }
    };
    for (const hand of [1,2]) {
      const mode=hand===1?song.rh:song.lh;
      if (mode==='off') continue;
      if (mode==='score') { out.push(...mapped.filter(n=>n[3]===hand)); continue; }
      if (mode==='song') {
        // Melody only where nobody sings; while singing, chord comping / comping+guide melody / quiet melody / rest.
        for (const n of mapped) {
          if (n[3]!==1) continue;
          const vocal = singAt(song, Math.floor(n[0]/song.meter));
          if (!vocal) out.push(n);
          else if (song.vocalRh==='soft') out.push([n[0],n[1],n[2],1,n[4]*.42]);
          // 2026-11-19 みかさん「メロディが聞こえにくかった」→ ガイドメロディーは譜面より少し強く（1.3倍・左手の刻みより前に出る）
          else if (song.vocalRh==='guide') out.push([n[0],n[1],n[2],1,Math.min(1,n[4]*1.3)]);
        }
        if (song.vocalRh==='comp') grooveBars(KZ.chord, (bar,p,dur,ch,ahead) => {
          if (!singAt(song,bar)) return;
          [...new Set(ch.iv.map(iv=>60+(ch.root+iv)%12))].forEach(m=>out.push([p,m+song.key,dur*.9,1,ahead?.34:.42]));
        });
        // 2026-11-19 みかさん「歌を歌っているところは、右手で細かく弾くのは控えめに」→ ガイドメロディーのときの和音は、細かい刻みをやめて2拍ごとに小さく伸ばす（メロディーより下の高さ）
        if (song.vocalRh==='guide') for (let bar=0; bar<song.bars; bar++) {
          if (!singAt(song,bar)) continue;
          for (let off=0; off<song.meter; off+=2) {
            const p=bar*song.meter+off, c=chordAt(song,p), ch=c&&parseChord(c.sym);
            if (!ch || ch.rest || p+EPS>=total) continue;
            const dur=Math.min(2,song.meter-off,total-p);
            [...new Set(ch.iv.map(iv=>48+(ch.root+iv)%12))].forEach(m=>out.push([p,m+song.key,dur*.95,1,.22]));
          }
        }
        continue;
      }
      if (mode==='kizami') {
        grooveBars(KZ.bass, (bar,p,dur,ch,ahead,deg) => out.push([p,36+(ch.bass??ch.root)+degreeAdd(ch,deg)+song.key,dur*.95,hand,ahead?.62:.75]));
        continue;
      }
      if (mode==='groove') {
        // Lowest LH attack at each onset carries the original bass rhythm/rests.
        const attacks=new Map();
        mapped.filter(n=>n[3]===2).forEach(n=> {
          const old=attacks.get(n[0]);
          if (!old || n[1]<old[1]) attacks.set(n[0],n);
        });
        const bassLine=[...attacks.values()].sort((a,b)=>a[0]-b[0]);
        for (const [index,n] of bassLine.entries()) {
          const end=Math.min(total,n[0]+n[2],bassLine[index+1]?.[0]??total);
          const cuts=[n[0],...song.chords.map(c=>c.bar*song.meter+c.beat).filter(p=>p>n[0]+EPS&&p<end-EPS),end];
          for(let i=0;i<cuts.length-1;i++) {
            const c=chordAt(song,cuts[i]), ch=c&&parseChord(c.sym);
            if(ch&&!ch.rest) out.push([cuts[i],36+(ch.bass??ch.root)+song.key,(cuts[i+1]-cuts[i])*.95,hand,.72]);
          }
        }
        continue;
      }
      song.chords.forEach((c,i)=> {
        const ch=parseChord(c.sym); if(!ch||ch.rest) return;
        const from=c.bar*song.meter+c.beat, nx=song.chords[i+1], to=nx?nx.bar*song.meter+nx.beat:total;
        const points=[from];
        if(mode!=='hold') for(let bar=Math.floor(from/song.meter);bar<song.bars;bar++) {
          if(bar*song.meter>=to) break;
          rhythm(mode,song.meter).forEach(x=> {const p=bar*song.meter+x;if(p>from+EPS&&p<to-EPS)points.push(p);});
        }
        points.sort((a,b)=>a-b);
        const base=hand===1?60+ch.root:36+(ch.bass??ch.root);
        const tones=hand===1?[...new Set(ch.iv.map(iv=>60+(ch.root+iv)%12))].sort((a,b)=>a-b):[base];
        const arp=hand===1?ch.iv.map(iv=>base+iv):[base,...ch.iv.slice(1).map(iv=>36+ch.root+iv),base+12];
        points.forEach((p,j)=> {
          const duration=((points[j+1]??to)-p)*(mode==='hold'?.98:.88);
          if (mode==='back' && hand===2) {
            const x=Math.round(((p%song.meter)+song.meter)%song.meter*1000)/1000;
            if (isBack(x,song.meter)) [...new Set(ch.iv.map(iv=>48+(ch.root+iv)%12))].sort((a,b)=>a-b).forEach(m=>out.push([p,m+song.key,duration*.85,hand,.66]));
            else out.push([p,base+song.key,duration,hand,.5]);
            return;
          }
          (mode==='arp'?[arp[j%arp.length]]:tones).forEach(m=>out.push([p,m+song.key,duration,hand,hand===1?.52:.7]));
        });
      });
    }
    return out.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
  }
  function compile(song, options, score, parseChord) {
    const section=song.sections.find(s=>s.id===options.sectionId), meter=song.meter;
    const target=section?section.start:0, lead=section?Math.min(target,song.leadBars):0;
    const count=song.countIn && !lead ? meter : 0;
    let ranges;
    if(section) ranges=[{start:target-lead,end:options.loop?section.end:song.bars-1}];
    else {
      ranges=song.order.map(id=>song.sections.find(s=>s.id===id)).filter(Boolean);
      if(!ranges.length) ranges=[{start:0,end:song.bars-1}];
      else if(song.tailBars) { const last=ranges.at(-1); ranges=[...ranges.slice(0,-1),{start:last.start,end:Math.min(song.bars-1,last.end+song.tailBars)}]; }
    }
    // Coalesce adjacent ranges, preserving ties across section boundaries.
    const merged=[];
    ranges.forEach(r=> {const last=merged.at(-1);if(last&&last.end+1===r.start)last.end=r.end;else merged.push({start:r.start,end:r.end});});
    const source=notesForSong(song,score,parseChord), timeline=[], notes=[];
    let t=count;
    if(count) for(let k=0;k<meter;k++) notes.push([k,k?79:84,.12,0,.25]);
    for(const range of merged) {
      const from=range.start*meter, end=(range.end+1)*meter;
      timeline.push({at:t,from,length:end-from});
      for(const n of source) {
        const a=Math.max(n[0],from),b=Math.min(n[0]+n[2],end);
        if(b>a+EPS) notes.push([t+a-from,n[1],b-a,n[3],n[4]]);
      }
      t+=end-from;
    }
    if(song.click) for(let k=count;k<t-EPS;k++) notes.push([k,(k-count)%meter?79:84,.12,0,.25]);
    const loopFrom=count+lead*meter, loopLength=section&&options.loop?(section.end-section.start+1)*meter:0;
    const cycleNotes=[];
    if(loopLength) for(const n of notes) {
      const a=Math.max(n[0],loopFrom), b=Math.min(n[0]+n[2],t);
      if(b>a+EPS)cycleNotes.push([a-loopFrom,n[1],b-a,n[3],n[4]]);
    }
    return {notes:notes.sort((a,b)=>a[0]-b[0]),cycleNotes,total:t,timeline,meter,count,
      target:target*meter,targetAt:count+lead*meter,sectionId:section?.id||'',loopFrom,loopLength};
  }
  function position(plan, beat) {
    let b=Math.max(0,beat), looping=false;
    if(plan.loopLength&&b>=plan.total) {b=plan.loopFrom+(b-plan.total)%plan.loopLength;looping=true;}
    const seg=plan.timeline.find(s=>b>=s.at&&b<s.at+s.length);
    const source=seg?seg.from+b-seg.at:0;
    return {bar:Math.floor(source/plan.meter),beat:source%plan.meter,
      count:b<plan.count,lead:!looping&&b>=plan.count&&b<plan.targetAt,
      remaining:Math.max(0,Math.ceil((plan.targetAt-b)/plan.meter)),done:!plan.loopLength&&beat>=plan.total};
  }
  function clockOffset(sent,received,server) {return server-(sent+received)/2;}
  return {fields,mappedNotes,chordAt,notesForSong,compile,position,clockOffset,singAt,degreeAdd,KIZAMI,RH,LH};
});
