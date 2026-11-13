(function() {
  'use strict';
  const $=id=>document.getElementById(id);
  const MODES={score:'譜面どおり',groove:'この曲のリズム',q:'4分で刻む',e:'8分で刻む',arp:'アルペジオ',hold:'コードを伸ばす',h:'2分で刻む',w:'1小節伸ばす',dot:'ターン・タ・ターン',off:'なし'};
  class LessonPlayer {
    constructor(role,deps) {
      this.role=role;this.deps=deps;this.audio=new LessonAudio();this.clock=0;this.bestRTT=Infinity;
      this.status='stopped';this.offset=0;this.options={sectionId:'',loop:false};this.intent=0;
      this.epoch=Math.random().toString(36).slice(2);this.seq=0;this.lastIncoming=-1;
      this.host=$(role);this.mount();
      this.song=deps.cleanSong(deps.api?deps.api.getSong():deps.initialSong);
      if(new URLSearchParams(location.search).has('debug')) {
        this.debug=document.createElement('pre');this.debug.className='lesson-debug';this.root.append(this.debug);
        const report=e=>{this.debugError=String(e.reason?.stack||e.error?.stack||e.message||'Error');};
        addEventListener('error',report);addEventListener('unhandledrejection',report);
      }
      this.loadView();this.animate();
    }
    mount() {
      const teacher=this.role==='teacher';
      [...this.host.children].filter(e=>e.matches('h1,.sub')).forEach(e=>e.hidden=true);
      this.root=document.createElement('div');this.root.className='lesson';
      this.root.innerHTML=`<header class="lesson-head"><div><div class="lesson-brand">オンラインピアノ · ${teacher?'LESSON':'SCORE'}</div><h1 class="lesson-title"></h1></div>${teacher?'<button class="lesson-open-settings">設定</button>':''}</header>
        <nav class="lesson-sections" aria-label="ここから再生"></nav>
        ${teacher?'<div class="lesson-transport"><button class="main lesson-play">▶ はじめから</button><button class="lesson-pause" disabled>一時停止</button><button class="lesson-stop">停止</button><label><input type="checkbox" class="lesson-loop"> 区間をくり返す</label><span class="lesson-meta"></span></div>':'<div class="student-controls"></div>'}
        <div class="lesson-now"><div class="lesson-position"><span class="lesson-section-name"></span><span><b class="lesson-bar">1</b> 小節</span></div><div class="lesson-chord"></div><div class="lesson-cue" role="status"></div><div class="lesson-beats" aria-label="拍"></div></div>
        <div class="score-stage" aria-label="再生中の譜面"></div>
        <div class="lesson-footer"><span class="lesson-mode"></span><span class="score-caption">元の譜面</span></div><div class="lesson-error" role="alert"></div>`;
      this.host.prepend(this.root);
      this.q=selector=>this.root.querySelector(selector);
      if(teacher) {
        const dialog=document.createElement('dialog');dialog.className='lesson-settings';dialog.setAttribute('aria-label','先生の設定');
        dialog.innerHTML='<div class="settings-head"><h2>先生の設定</h2><button class="settings-close">閉じる</button></div><div class="settings-sound"><div class="setting-line"><label for="lessonLead">区間の助走</label><select id="lessonLead"><option value="2">2小節前から</option><option value="1">1小節前から</option><option value="0">その小節から</option></select></div><div class="setting-line"><label for="lessonRight">右手の音量</label><input id="lessonRight" type="range" min="0" max="100"><output id="lessonRightVal"></output><label for="lessonLeft">左手の音量</label><input id="lessonLeft" type="range" min="0" max="100"><output id="lessonLeftVal"></output></div></div>';
        dialog.insertBefore($('songLibrary'),dialog.querySelector('.settings-sound'));
        dialog.querySelector('.settings-sound').prepend($('accompanimentSettings'));
        $('tabAcc').textContent='コード・区切り';
        const connection=this.host.querySelector(':scope > .box');
        const details=document.createElement('details');details.innerHTML='<summary>生徒さんにつなぐ</summary>';details.append(connection);dialog.append(details);
        for(const el of [this.host.querySelector('.tabs'),$('paneScale'),$('paneAcc')])dialog.append(el);
        this.host.append(dialog);this.dialog=dialog;
        dialog.querySelector('.settings-close').onclick=()=>dialog.close();
        this.q('.lesson-open-settings').onclick=()=>{dialog.showModal();$('tabAcc').click();this.deps.api.redraw();};
        dialog.addEventListener('close',()=>this.q('.lesson-open-settings').focus());
        this.q('.lesson-play').onclick=()=>this.status==='paused'?this.resume():this.play('');
        this.q('.lesson-pause').onclick=()=>this.pause();
        this.q('.lesson-stop').onclick=()=>this.stop(true);
        this.q('.lesson-loop').onchange=e=> {this.options.loop=e.target.checked;if(this.status==='playing')this.play(this.options.sectionId);};
        $('lessonLead').onchange=e=>this.deps.api.patch({leadBars:+e.target.value});
        for(const [id,field] of [['lessonRight','rightVolume'],['lessonLeft','leftVolume']]) $(id).oninput=e=>this.deps.api.patch({[field]:+e.target.value});
        $('localSound').addEventListener('change',()=>this.audio.setVolume($('localSound').checked?1:0));
        document.addEventListener('piano-song-change',()=>this.changed());
        // Space belongs to playback only when the settings are closed.
        document.addEventListener('keydown',e=> {if(e.code==='Space'&&!dialog.open&&!/INPUT|SELECT|TEXTAREA|BUTTON/.test(e.target.tagName)&&!e.ctrlKey&&!e.metaKey&&!e.altKey){e.preventDefault();this.status==='playing'?this.pause():this.status==='paused'?this.resume():this.play(this.options.sectionId);}});
      } else {
        const controls=this.q('.student-controls');controls.append($('start'));
        const status=$('sStatus').closest('p');controls.append(status);
        const vol=$('vol');vol.setAttribute('aria-label','音量');controls.append(vol);
        this.host.querySelectorAll(':scope > .box').forEach(el=> {if(el.contains($('nowNote'))||el.contains($('sKb')))el.classList.add('scale-output');else el.hidden=true;});
        $('start').onclick=()=>this.enableAudio();
        vol.oninput=()=>{this.audio.setVolume(Math.pow(10,+vol.value/20));if(window.Tone)Tone.Destination.volume.value=+vol.value;};
      }
    }
    changed() {
      const updated=this.deps.cleanSong(this.deps.api.getSong());
      if(JSON.stringify(updated)===JSON.stringify(this.song))return;
      this.stop(false);this.song=updated;this.options.sectionId='';this.loadView();this.broadcast();
    }
    loadView() {
      this.plan=LessonCore.compile(this.song,this.options,(window.PIANO_SCORES||{})[this.song.scoreId]||PIANO_SCORE,this.deps.parseChord);
      this.q('.lesson-title').textContent=this.song.name;
      document.title=this.song.name+' | オンラインピアノ';
      const nav=this.q('.lesson-sections');nav.replaceChildren();
      for(const s of this.song.sections) {
        const b=document.createElement('button');b.dataset.section=s.id;
        const name=document.createElement('span');name.textContent=s.name;
        const bar=document.createElement('small');bar.textContent=String(s.start+1).padStart(2,'0');b.append(name,bar);
        if(this.role==='teacher')b.onclick=()=>this.play(s.id);else {b.disabled=true;b.tabIndex=-1;}
        nav.append(b);
      }
      this.q('.lesson-mode').textContent=`右手 ${MODES[this.song.rh]}　／　左手 ${MODES[this.song.lh]}`;
      this.q('.score-caption').textContent=this.song.scoreId&&window.SHOW_SCORE_IMAGES?'元の譜面'+(this.song.key?' · 表示は元のキー':''):'コード譜';
      if(this.role==='teacher') {
        this.q('.lesson-meta').textContent=`♩ ${this.song.bpm}　キー ${this.song.key>0?'+':''}${this.song.key}　${this.song.leadBars}小節前から`;
        $('lessonLead').value=this.song.leadBars;
        for(const [id,field] of [['lessonRight','rightVolume'],['lessonLeft','leftVolume']]){$(id).value=this.song[field];$(id+'Val').textContent=this.song[field];}
        for(const row of ['rhRow','lhRow']) $(row).querySelectorAll('[data-v="score"],[data-v="groove"]').forEach(el=>el.disabled=!this.song.scoreId);
      }
      this.q('.lesson-beats').replaceChildren(...Array.from({length:this.song.meter},()=>document.createElement('i')));
      this.lastSystem=null;this.lastBeat=null;this.drawPosition();this.updateButtons();
    }
    async enableAudio() {
      const button=$('start');
      if(this.audio.enabled){this.audio.stop();this.audio.enabled=false;this.deps.stopLegacy();button.textContent='音 OFF';return;}
      button.disabled=true;button.textContent='音を準備中…';this.error('');
      try {
        await this.audio.prepare();
        // Initialize the original keyboard too, but its failure must not prevent score playback.
        if(this.deps.unlock)this.deps.unlock().catch(()=>{});
        button.textContent='音 ON';button.disabled=false;
        if(this.status==='playing')this.audio.start(this.plan,this.song,this.startAt,this.offset,this.playClock);
        this.deps.send({type:'lesson-ready'});
      } catch(e) {button.disabled=false;button.textContent='音を出す';this.error('ピアノ音を読み込めませんでした。もう一度「音を出す」を押してください。');}
    }
    error(message) {this.q('.lesson-error').textContent=message;}
    async play(sectionId) {
      const intent=++this.intent;
      this.audio.stop();this.deps.stopLegacy();this.status='stopped';this.offset=0;this.broadcast();this.error('');
      this.q('.lesson-play').textContent='音を準備中…';
      try {await this.audio.prepare();}catch(e){if(intent===this.intent){this.error('ピアノ音を読み込めませんでした。もう一度再生してください。');this.updateButtons();}return;}
      if(intent!==this.intent)return;
      this.options.sectionId=sectionId||'';this.options.loop=this.q('.lesson-loop').checked;
      this.plan=LessonCore.compile(this.song,this.options,(window.PIANO_SCORES||{})[this.song.scoreId]||PIANO_SCORE,this.deps.parseChord);
      this.offset=0;this.startAt=Date.now()+700;this.status='playing';this.playClock=0;
      this.audio.setVolume($('localSound').checked?1:0);this.audio.start(this.plan,this.song,this.startAt,0,0);
      this.broadcast();this.updateButtons();this.lastSystem=null;
    }
    beatNow() {return this.status==='playing'?this.offset+(Date.now()+(this.playClock||0)-this.startAt)/1000*this.song.bpm/60:this.offset;}
    pause() {
      if(this.status!=='playing')return;
      this.offset=Math.max(0,this.beatNow());this.audio.stop();this.status='paused';this.broadcast();this.updateButtons();
    }
    async resume() {
      const intent=++this.intent;
      try {await this.audio.prepare();}catch(e){this.error('ピアノ音を読み込めませんでした。もう一度再生してください。');return;}
      if(intent!==this.intent)return;
      this.startAt=Date.now()+700;this.status='playing';this.playClock=0;
      this.audio.start(this.plan,this.song,this.startAt,this.offset,0);this.broadcast();this.updateButtons();
    }
    stop(send=false) {
      this.intent++;this.audio.stop();this.status='stopped';this.offset=0;
      this.deps.stopLegacy();this.updateButtons();if(send)this.broadcast();this.drawPosition();
    }
    updateButtons() {
      if(this.role!=='teacher')return;
      this.q('.lesson-play').textContent=this.status==='paused'?'▶ 続きから':'▶ はじめから';
      this.q('.lesson-pause').disabled=this.status!=='playing';
    }
    snapshot() {
      return {type:'lesson-state',epoch:this.epoch,seq:this.seq,song:this.song,options:this.options,status:this.status,startAt:this.startAt||0,offset:this.offset};
    }
    broadcast() {if(this.role==='teacher'){this.seq++;this.deps.send(this.snapshot());}}
    onPeer(connection) {
      if(this.role==='teacher')connection.send(this.snapshot());
      else {this.bestRTT=Infinity;this.probe();}
    }
    probe() {this.deps.send({type:'clock-ping',sent:Date.now()});}
    handle(ev,connection) {
      if(!ev||typeof ev!=='object')return false;
      if(ev.type==='clock-ping'&&this.role==='teacher') {connection?.send({type:'clock-pong',sent:ev.sent,server:Date.now()});return true;}
      if(ev.type==='clock-pong'&&this.role==='student') {
        const received=Date.now(),rtt=received-ev.sent;
        if(Number.isFinite(ev.sent)&&Number.isFinite(ev.server)&&rtt>=0&&rtt<this.bestRTT){
          const first=this.bestRTT===Infinity;
          this.bestRTT=rtt;this.clock=LessonCore.clockOffset(ev.sent,received,ev.server);
          if(first)this.deps.send({type:'lesson-ready'});
        }
        return true;
      }
      if(ev.type==='lesson-ready'&&this.role==='teacher'){connection?.send(this.snapshot());return true;}
      if(ev.type!=='lesson-state'||this.role!=='student')return false;
      if(JSON.stringify(ev).length>60000)return true;
      if(ev.epoch===this.incomingEpoch&&ev.seq<this.lastIncoming)return true;
      const song=this.deps.cleanSong(ev.song);if(!song)return true;
      this.incomingEpoch=ev.epoch;this.lastIncoming=ev.seq;
      this.audio.stop();this.deps.stopLegacy();this.song=song;
      this.options={sectionId:String(ev.options?.sectionId||''),loop:ev.options?.loop===true};
      this.status=['playing','paused','stopped'].includes(ev.status)?ev.status:'stopped';
      this.startAt=Number.isFinite(ev.startAt)?ev.startAt:Date.now();
      this.offset=Number.isFinite(ev.offset)?Math.max(0,ev.offset):0;
      this.playClock=this.clock;this.loadView();
      if(this.status==='playing')this.audio.start(this.plan,this.song,this.startAt,this.offset,this.playClock);
      return true;
    }
    drawPosition() {
      if(!this.plan)return;
      const beat=this.beatNow(),pos=LessonCore.position(this.plan,beat);
      if(pos.done) {
        if(this.status==='playing') {this.offset=this.plan.total-.001;this.status='stopped';this.audio.stop();this.updateButtons();if(this.role==='teacher')this.broadcast();}
        return;
      }
      const s=this.song.sections.find(s=>pos.bar>=s.start&&pos.bar<=s.end);
      const target=this.song.sections.find(s=>s.id===this.options.sectionId);
      this.q('.lesson-section-name').textContent=s?.name||'';
      this.q('.lesson-bar').textContent=pos.bar+1;
      const chord=LessonCore.chordAt(this.song,pos.bar*this.song.meter+pos.beat);
      this.q('.lesson-chord').textContent=chord?this.deps.transposeSym(chord.sym,this.song.key):'';
      this.q('.lesson-cue').textContent=pos.count?'カウント '+(Math.floor(Math.max(0,beat))+1):pos.lead?`${target?.name||''}まで あと${pos.remaining}小節`:this.status==='paused'?'一時停止':this.status==='playing'?'':' ';
      this.q('.lesson-beats').querySelectorAll('i').forEach((el,i)=>el.classList.toggle('on',i===Math.floor(pos.count?Math.max(0,beat)%this.song.meter:pos.beat)));
      this.q('.lesson-sections').querySelectorAll('button').forEach(el=>el.classList.toggle('active',el.dataset.section===(pos.lead?target?.id:s?.id)));
      // 2026-11-13 みかさん「譜面の画像は外して公開」→ 公開版は画像を出さずコードの升目で見せる（画像は assets/ に手元だけ）
      const src=this.song.scoreId&&window.SHOW_SCORE_IMAGES?this.song.scoreMap[pos.bar]:-1, box=src>=0&&this.song.scoreId===PIANO_SCORE.id?PIANO_SCORE.positions[src]:null;
      const stage=this.q('.score-stage');
      if(box) {
        if(this.lastSystem!==box.system) {
          stage.replaceChildren();
          for(let i=box.system;i<Math.min(box.system+2,PIANO_SCORE.systems.length);i++) {
            const sys=PIANO_SCORE.systems[i],row=document.createElement('div');row.className='score-row';
            const img=new Image();img.src=sys.image;img.alt=`元の譜面 ${sys.first+1}小節から`;img.style.aspectRatio=sys.ratio;
            const num=document.createElement('span');num.className='score-numbers';num.textContent=`${sys.first+1} – ${(PIANO_SCORE.systems[i+1]?.first||112)} 小節`;
            row.append(img,num);
            if(i===box.system){const hl=document.createElement('div');hl.className='score-highlight';hl.innerHTML='<div class="score-progress"></div>';row.append(hl);}
            stage.append(row);
          }
          this.lastSystem=box.system;
        }
        const hl=stage.querySelector('.score-highlight');hl.style.left=box.x*100+'%';hl.style.width=box.width*100+'%';
        hl.querySelector('.score-progress').style.transform=`scaleX(${pos.beat/this.song.meter})`;
      } else {
        const group=Math.floor(pos.bar/8),key='chords:'+group;
        if(this.lastSystem!==key) {
          const grid=document.createElement('div');grid.className='lesson-chords';
          for(let b=group*8;b<Math.min(this.song.bars,group*8+8);b++) {
            const cell=document.createElement('div');cell.dataset.bar=b;
            const num=document.createElement('small');num.textContent=b+1+' 小節';
            const text=document.createElement('span'),chords=this.song.chords.filter(c=>c.bar===b);
            text.textContent=chords.length?chords.map(c=>this.deps.transposeSym(c.sym,this.song.key)).join('  /  '):'−';cell.append(num,text);grid.append(cell);
          }
          stage.replaceChildren(grid);this.lastSystem=key;
        }
        stage.querySelectorAll('[data-bar]').forEach(el=>el.classList.toggle('active',+el.dataset.bar===pos.bar));
      }
    }
    animate() {
      this.drawPosition();
      if(this.debug)this.debug.textContent=JSON.stringify({status:this.status,beat:this.beatNow(),offset:this.offset,startAt:this.startAt,now:Date.now(),audio:this.audio.context?.state,buffers:this.audio.buffers.size,sources:this.audio.sources.size,clock:this.clock,error:this.debugError},null,2);
      this.raf=requestAnimationFrame(()=>this.animate());
    }
  }
  window.LessonPlayer=LessonPlayer;
})();
