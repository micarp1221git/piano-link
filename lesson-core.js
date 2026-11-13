/* Quarter-note beat units throughout. This module is shared by both peers. */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.LessonCore = api;
})(typeof window !== 'undefined' ? window : this, function() {
  'use strict';
  const EPS = 1e-7;
  const RH = ['score','q','e','arp','hold','off'];
  const LH = ['score','groove','q','e','arp','h','w','dot','off'];
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
      rh: RH.includes(o.rh) && (attached || o.rh !== 'score') ? o.rh : 'q',
      lh: LH.includes(o.lh) && (attached || !['score','groove'].includes(o.lh)) ? o.lh : 'q',
      leadBars: [0,1,2].includes(+o.leadBars) ? +o.leadBars : 2,
      rightVolume: Number.isFinite(+o.rightVolume) ? Math.max(0,Math.min(100,+o.rightVolume)) : 75,
      leftVolume: Number.isFinite(+o.leftVolume) ? Math.max(0,Math.min(100,+o.leftVolume)) : 75
    };
  }
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
        else { const note=[at,n[1]+song.key,b-a,n[3],n[3]===1?.63:.7]; out.push(note); last.set(id,note); }
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
    if (mode==='q') return Array.from({length:meter},(_,i)=>i);
    if (mode==='e'||mode==='arp') return Array.from({length:meter*2},(_,i)=>i/2);
    if (mode==='h') return [0,2].filter(x=>x<meter);
    if (mode==='dot') return [0,1.5,2].filter(x=>x<meter);
    return [0];
  }
  function notesForSong(song,score,parseChord) {
    const mapped = mappedNotes(song,score), out=[];
    const total = song.bars*song.meter;
    for (const hand of [1,2]) {
      const mode=hand===1?song.rh:song.lh;
      if (mode==='off') continue;
      if (mode==='score') { out.push(...mapped.filter(n=>n[3]===hand)); continue; }
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
  return {fields,mappedNotes,chordAt,notesForSong,compile,position,clockOffset,RH,LH};
});
