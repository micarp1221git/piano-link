/* Cancellable Web Audio sample playback, using the same Salamander piano as the original app. */
(function() {
  'use strict';
  const PITCHES=[33,36,39,42,45,48,51,54,57,60,63,66,69,72,75,78,81,84];
  const name=m=>['C','Cs','D','Ds','E','F','Fs','G','Gs','A','As','B'][m%12]+(Math.floor(m/12)-1);
  class LessonAudio {
    constructor() {this.buffers=new Map();this.sources=new Set();this.timer=null;this.enabled=false;this.generation=0;}
    async prepare() {
      // 2026-11-25 みかさん「iPhoneから音がならない」＝iPhoneは消音スイッチ（集中モードの消音も）でページの音が止まる。音楽の再生として扱ってもらう（iOS 17〜）
      try{if(navigator.audioSession)navigator.audioSession.type='playback';}catch(_){}
      // 同じ日 23:47 の画面: 再生中・音の部品18個・鳴らしている音6つ、なのに聞こえない＝iPhone側が止めている。
      // 古いiOSやアプリの中のブラウザ向けに、無音の <audio> を回しておく（これがあるとページの音が「音楽」として扱われ、消音でも鳴る）
      if(!this.keepAlive&&(/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.maxTouchPoints>1&&/Macintosh/.test(navigator.userAgent)))) {
        try {
          const rate=8000,len=rate/2,buf=new ArrayBuffer(44+len),v=new DataView(buf),w=(o,t)=>[...t].forEach((c,i)=>v.setUint8(o+i,c.charCodeAt(0)));
          w(0,'RIFF');v.setUint32(4,36+len,true);w(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);
          v.setUint32(24,rate,true);v.setUint32(28,rate,true);v.setUint16(32,1,true);v.setUint16(34,8,true);w(36,'data');v.setUint32(40,len,true);
          new Uint8Array(buf,44).fill(128);
          const a=new Audio(URL.createObjectURL(new Blob([buf],{type:'audio/wav'})));
          a.loop=true;a.setAttribute('playsinline','');a.setAttribute('x-webkit-airplay','deny');a.play().catch(()=>{});this.keepAlive=a;
        } catch(e){this.keepAliveError=String(e);}
      }
      this.context ||= new (window.AudioContext||window.webkitAudioContext)();
      await this.context.resume();
      if(this.buffers.size===PITCHES.length) {this.enabled=true;return;}
      if(!this.loading) this.loading=Promise.all(PITCHES.map(async midi=> {
        if(this.buffers.has(midi))return;
        const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),20000);
        try {
          const res=await fetch('https://tonejs.github.io/audio/salamander/'+name(midi)+'.mp3',{signal:controller.signal});
          if(!res.ok)throw new Error('piano sample '+res.status);
          const buffer=await this.context.decodeAudioData(await res.arrayBuffer());
          this.buffers.set(midi,buffer);
        } finally {clearTimeout(timer);}
      })).finally(()=>this.loading=null);
      await this.loading;this.enabled=true;
    }
    stop() {
      this.generation++;
      clearInterval(this.timer);this.timer=null;
      for(const source of this.sources) {try{source.stop();}catch(_){}source.disconnect();}
      this.sources.clear();
    }
    setVolume(value) {this.volume=Math.max(0,Math.min(2,value));if(this.master)this.master.gain.value=this.volume;}
    note(n,when,seconds,skip,song) {
      if(n[1]===127){this.stick(when,70/100*n[4]);return;} // 2026-11-18 みかさん「カウントはドラムのスティックのカチカチ」＝譜面の手の番号0・高さ127はスティックの音
      const ctx=this.context, midi=n[1], nearest=PITCHES.reduce((a,b)=>Math.abs(b-midi)<Math.abs(a-midi)?b:a);
      const source=ctx.createBufferSource(), gain=ctx.createGain(), rate=Math.pow(2,(midi-nearest)/12);
      source.buffer=this.buffers.get(nearest);source.playbackRate.value=rate;
      source.connect(gain);gain.connect(this.master);
      const volume=(n[3]===1?song.rightVolume:n[3]===2?song.leftVolume:70)/100*n[4];
      gain.gain.setValueAtTime(0,when);
      gain.gain.linearRampToValueAtTime(volume,when+.008);
      gain.gain.setValueAtTime(volume,when+Math.max(.009,seconds));
      gain.gain.exponentialRampToValueAtTime(.0001,when+Math.max(.01,seconds)+.10);
      const offset=Math.min(Math.max(0,skip*rate),Math.max(0,source.buffer.duration-.01));
      this.sources.add(source);source.onended=()=>{this.sources.delete(source);source.disconnect();gain.disconnect();};
      source.start(when,offset);source.stop(when+seconds+.12);
    }
    stick(when,volume) {
      // スティック同士を打つ「カチッ」: 高い所だけ残した短い雑音＋ごく短い高い音（太鼓・リムショットではない）
      const ctx=this.context;
      if(!this.noise) {
        const len=Math.floor(ctx.sampleRate*.05),buf=ctx.createBuffer(1,len,ctx.sampleRate),d=buf.getChannelData(0);
        for(let i=0;i<len;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/len,4);
        this.noise=buf;
      }
      const src=ctx.createBufferSource(),bp=ctx.createBiquadFilter(),g=ctx.createGain(),osc=ctx.createOscillator(),og=ctx.createGain();
      src.buffer=this.noise;bp.type='bandpass';bp.frequency.value=3500;bp.Q.value=1.4;
      osc.type='triangle';osc.frequency.value=2500;
      g.gain.setValueAtTime(volume*2.2,when);g.gain.exponentialRampToValueAtTime(.0001,when+.045);
      og.gain.setValueAtTime(volume*.6,when);og.gain.exponentialRampToValueAtTime(.0001,when+.025);
      src.connect(bp);bp.connect(g);g.connect(this.master);osc.connect(og);og.connect(this.master);
      this.sources.add(src);
      src.onended=()=>{this.sources.delete(src);[src,bp,g,osc,og].forEach(x=>x.disconnect());};
      src.start(when);src.stop(when+.06);osc.start(when);osc.stop(when+.04);
    }
    start(plan,song,startAt,offset=0,clockOffset=0) {
      this.stop();if(!this.enabled)return;
      const ctx=this.context, spb=60/song.bpm;
      this.master?.disconnect();this.master=ctx.createGain();this.master.gain.value=this.volume??1;this.master.connect(ctx.destination);
      // Freeze the mapping for this run. Later clock probes must not jump the audio.
      const t0=ctx.currentTime+(startAt-(Date.now()+clockOffset))/1000-offset*spb;
      let pass=0,index=0,list=plan.notes,base=0;
      const elapsed=Math.max(offset,(ctx.currentTime-t0)/spb);
      if(plan.loopLength&&elapsed>=plan.total) {
        pass=Math.floor((elapsed-plan.total)/plan.loopLength)+1;
        list=plan.cycleNotes;base=plan.total+(pass-1)*plan.loopLength;
      }
      while(index<list.length&&base+list[index][0]<elapsed-1e-7) {
        const n=list[index++],end=base+n[0]+n[2];
        if(end>elapsed+.02) this.note(n,Math.max(ctx.currentTime+.01,t0+elapsed*spb),(end-elapsed)*spb,(elapsed-base-n[0])*spb,song);
      }
      const tick=()=> {
        const now=ctx.currentTime,horizon=now+1.2;
        // Empty loops are legal (both hands muted or N.C.). Never busy-loop.
        for(let safety=0;safety<6000;safety++) {
          if(index>=list.length) {
            if(!plan.loopLength||!plan.cycleNotes.length) {clearInterval(this.timer);this.timer=null;return;}
            pass++;list=plan.cycleNotes;base=plan.total+(pass-1)*plan.loopLength;index=0;
          }
          const n=list[index],when=t0+(base+n[0])*spb;
          if(when>horizon)break;
          index++;
          const late=Math.max(0,now-when),duration=n[2]*spb-late;
          if(duration>.01)this.note(n,Math.max(when,now+.005),duration,late,song);
        }
      };
      this.timer=setInterval(tick,40);tick();
    }
  }
  window.LessonAudio=LessonAudio;
})();
