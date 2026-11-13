const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const dir=path.join(__dirname,'..'),C=require('../lesson-core.js');
const html=fs.readFileSync(path.join(dir,'index.html'),'utf8');
const inline=html.match(/<script>\s*"use strict";([\s\S]*?)<\/script>/)[1];
new vm.Script(inline);
const ctx=vm.createContext({LessonCore:C,window:{}});
vm.runInContext(fs.readFileSync(path.join(dir,'lesson-data.js'),'utf8'),ctx);
vm.runInContext(inline.slice(inline.indexOf('const PC ='),inline.indexOf('// ---- 伴奏：音の並び')),ctx);
const score=ctx.window.PIANO_SCORE;
const song=()=>vm.runInContext('cleanSong(LESSON_PRESET)',ctx);
const clean=o=>ctx.cleanSong(o),parse=s=>ctx.parseChord(s);
const compile=(s,options={})=>C.compile(s,options,score,parse);

test('112 measures, 2150 corrected notes; source mapping and settings survive serialization',()=>{
 const s=song();assert.equal(s.bars,112);assert.equal(s.chords.length,196);assert.equal(score.notes.length,2150);
 const mapped=C.mappedNotes(s,score);assert.equal(mapped.length,score.notes.length);
 const actual=mapped.map(n=>n.slice(0,4)).sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[3]-b[3]);
 const expected=JSON.parse(JSON.stringify(score.notes)).sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[3]-b[3]);
 assert.deepEqual(actual,expected);
 assert.deepEqual(JSON.parse(JSON.stringify(clean(JSON.parse(JSON.stringify(s))))),JSON.parse(JSON.stringify(s)));
 assert.deepEqual(Array.from(s.sections.flatMap(s=>Array.from({length:s.end-s.start+1},(_,i)=>s.start+i))),Array.from({length:112},(_,i)=>i));
});
test('section entrances use actual two-bar lead-in and exact boundaries',()=>{
 for(const id of ['a1','b1','chorus1','a2','b2','chorus2','last1']){
  const s=song(),sec=s.sections.find(x=>x.id===id),p=compile(s,{sectionId:id});
  assert.equal(p.timeline[0].from,(sec.start-2)*4);
  assert.equal(C.position(p,0).bar,sec.start-2);assert.equal(C.position(p,7.999).lead,true);
  assert.equal(C.position(p,8).bar,sec.start);assert.equal(C.position(p,8).lead,false);
 }
 assert.equal(C.position(compile(song(),{sectionId:'chorus2'}),8).bar,58);
});
test('silence after N.C., corrected G bass, continuous 4/4 at bars 13 and 58',()=>{
 const s=song();s.rh=s.lh='score';const p=compile(s);
 assert.equal(p.total,448);assert.equal(p.notes[0][0],8);
 assert.equal(p.notes.find(n=>n[3]===2)[1],43);
 for(const bar of [12,13,14,57,58])assert.equal(C.position(p,bar*4).bar,bar);
 assert.ok(!p.notes.some(n=>n[0]<0||n[0]>=448||n[2]<=0));
});
test('bass groove keeps onsets/rests and follows edited slash bass chords',()=>{
 const s=song();s.rh='off';s.lh='groove';
 const original=C.notesForSong(s,score,parse).filter(n=>n[0]>=8&&n[0]<12);
 s.chords.find(c=>c.bar===2).sym='C/E';
 const changed=C.notesForSong(s,score,parse).filter(n=>n[0]>=8&&n[0]<12);
 assert.deepEqual(changed.map(n=>n[0]),original.map(n=>n[0]));assert.ok(changed.every(n=>n[1]===40));
 assert.ok(changed.some(n=>n[0]%1!==0));
 assert.ok(changed.every((n,i)=>!i||changed[i-1][0]+changed[i-1][2]<=n[0]+1e-7));
 s.chords.find(c=>c.bar===2).sym='N.C.';
 assert.equal(C.notesForSong(s,score,parse).filter(n=>n[0]>=8&&n[0]<12).length,0);
});

function playerHarness() {
 let now=100000;const context=vm.createContext({window:{},document:{getElementById:()=>({checked:true})},LessonCore:C,PIANO_SCORE:score,Date:{now:()=>now}});
 vm.runInContext(fs.readFileSync(path.join(dir,'lesson-ui.js'),'utf8'),context);
 const make=role=> {
  const p=Object.create(context.window.LessonPlayer.prototype),messages=[];
  Object.assign(p,{role,song:song(),options:{sectionId:'',loop:false},status:'stopped',offset:0,intent:0,epoch:'test',seq:0,lastIncoming:-1,clock:0,bestRTT:Infinity,
   audio:{starts:0,stops:0,async prepare(){},stop(){this.stops++;},start(){this.starts++;},setVolume(){}},
   deps:{cleanSong:clean,parseChord:parse,transposeSym:s=>s,stopLegacy(){},send:m=>messages.push(JSON.parse(JSON.stringify(m)))},
   q:()=>({checked:false,textContent:''}),error(){},updateButtons(){},drawPosition(){},
   loadView(){this.plan=compile(this.song,this.options);}});
  p.plan=compile(p.song);return {p,messages};
 };
 return {make,setNow:value=>now=value};
}
test('rapid stop during sample loading cancels pending playback',async()=> {
 const {make}=playerHarness(),{p,messages}=make('teacher');let resolve;
 p.audio.prepare=()=>new Promise(r=>resolve=r);
 const pending=p.play('a1');p.stop(true);resolve();await pending;
 assert.equal(p.status,'stopped');assert.equal(p.audio.starts,0);assert.ok(messages.every(m=>m.status==='stopped'));
});
test('teacher start/pause/resume/stop and settings updates reach the student',async()=> {
 const h=playerHarness(),{p:teacher,messages}=h.make('teacher'),{p:student}=h.make('student');
 const forward=()=>student.handle(messages.at(-1));
 await teacher.play('chorus2');forward();
 assert.equal(student.status,'playing');assert.equal(student.plan.timeline[0].from,224);
 h.setNow(104450);teacher.pause();forward();assert.equal(student.status,'paused');assert.equal(student.offset,5);
 await teacher.resume();forward();assert.equal(student.status,'playing');assert.equal(student.offset,5);
 const old=messages.at(-1);teacher.stop(true);forward();assert.equal(student.status,'stopped');
 student.handle(old);assert.equal(student.status,'stopped');
 teacher.song.chords[2].sym='C/E';teacher.broadcast();forward();assert.equal(student.song.chords[2].sym,'C/E');
});
test('first clock probe requests a fresh snapshot; later probes do not jump a playing clock',()=> {
 const h=playerHarness(),{p,messages}=h.make('student');h.setNow(1040);
 p.handle({type:'clock-pong',sent:1000,server:5020});assert.equal(p.clock,4000);assert.equal(messages.at(-1).type,'lesson-ready');
 p.status='playing';p.playClock=4000;h.setNow(1060);p.handle({type:'clock-pong',sent:1050,server:5060});
 assert.equal(p.playClock,4000);assert.equal(p.clock,4005);
});
test('all accompaniment modes produce finite valid events; seventh survives arpeggiation',()=>{
 for(const rh of C.RH)for(const lh of C.LH){const s=song();s.rh=rh;s.lh=lh;const p=compile(s);assert.ok(p.notes.every(n=>n.every(Number.isFinite)&&n[2]>0&&n[0]+n[2]<=448+1e-7));}
 const s=clean({name:'Test',bars:1,meter:4,chords:[{bar:0,beat:0,sym:'Cmaj7'}],rh:'arp',lh:'off',countIn:false});
 assert.ok(compile(s).notes.some(n=>n[1]===71));
});
test('loop repeats only selected section after its initial lead-in; ties remain clipped',()=>{
 const s=song();s.rh=s.lh='score';const p=compile(s,{sectionId:'chorus2',loop:true});
 assert.equal(p.loopFrom,8);assert.equal(p.loopLength,40);assert.equal(p.total,48);
 assert.equal(C.position(p,48).bar,58);assert.equal(C.position(p,88).bar,58);
 assert.equal(C.position(p,48).lead,false);
 assert.ok(p.cycleNotes.every(n=>n[0]>=0&&n[0]+n[2]<=40+1e-7));
});
test('inserted blank bar preserves subsequent notation and breaks ties only at insertion',()=>{
 const s=song();s.bars++;s.scoreMap.splice(12,0,-1);const mapped=C.mappedNotes(clean(s),score);
 assert.ok(!mapped.some(n=>n[0]>=48&&n[0]<52));
 const old=score.notes.filter(n=>n[0]>=48&&n[0]<52).map(n=>n[1]).sort();
 const now=mapped.filter(n=>n[0]>=52&&n[0]<56).map(n=>n[1]).sort();assert.deepEqual(now,Array.from(old));
 const detached=clean({...s,meter:3});assert.equal(detached.scoreId,null);assert.equal(detached.rh,'q');assert.equal(detached.lh,'q');
});
test('full playback honors section order and merges adjacent ranges without retriggering ties',()=>{
 const s=song();s.rh=s.lh='score';const direct=compile(s);
 s.order=s.sections.map(s=>s.id);assert.deepEqual(compile(s).notes,direct.notes);
 s.order=['a1','a1'];const repeated=compile(s);assert.equal(repeated.total,80);assert.equal(C.position(repeated,40).bar,12);
});
test('optional count-in and reduced lead-in are distinct',()=>{
 const s=song();s.countIn=true;
 assert.equal(compile(s).count,4);assert.equal(compile(s,{sectionId:'a1'}).count,0);
 s.leadBars=0;assert.equal(compile(s,{sectionId:'a1'}).count,4);
});
test('clock offset calculation removes wall-clock difference',()=>assert.equal(C.clockOffset(1000,1040,5020),4000));

test('audio cancellation includes future scheduled notes, resume catches held notes, empty loops finish',()=>{
 const timers=new Set(),sources=[];
 const fake={currentTime:10,destination:{},createGain:()=>({connect(){},disconnect(){},gain:{value:1,setValueAtTime(){},linearRampToValueAtTime(){},exponentialRampToValueAtTime(){}}}),
  createBufferSource:()=>{const s={playbackRate:{value:1},connect(){},disconnect(){},start(when,offset){this.when=when;this.offset=offset;},stop(when){if(when===undefined)this.cancelled=true;}};sources.push(s);return s;}};
 const ac=vm.createContext({window:{},Date:{now:()=>100000},setInterval:fn=>{timers.add(fn);return fn;},clearInterval:id=>timers.delete(id),Map,Set});
 vm.runInContext(fs.readFileSync(path.join(dir,'lesson-audio.js'),'utf8'),ac);
 const audio=new ac.window.LessonAudio();audio.context=fake;audio.enabled=true;
 for(let midi=33;midi<=84;midi+=3)audio.buffers.set(midi,{duration:20});
 const s=song(),p={notes:[[0,60,4,1,.6],[.1,64,1,1,.6]],total:4,loopLength:0};
 audio.start(p,s,100100,0,0);assert.equal(sources.length,2);assert.ok(sources[0].when>10);
 audio.stop();assert.ok(sources.every(s=>s.cancelled));assert.equal(timers.size,0);
 audio.start(p,s,100000,2,0);assert.ok(sources.at(-1).offset>0);audio.stop();
 audio.start({notes:[],cycleNotes:[],total:4,loopLength:4},s,100000);assert.equal(timers.size,0);
});
