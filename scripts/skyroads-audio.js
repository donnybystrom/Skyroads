/* Original digital effects and pre-rendered AdLib music. Presentation only:
 * never changes physics, input masks, sound_busy or simulation timestamps. */
function createSkyRoadsAudio(manifest){
 let context,master,musicGain,fxGain,analyser,music,fx,track=1,position=0,musicStarted=0,playing=false,enabled=true,musicEnabled=true,volume=.35,generation=0,effectRequest=0;
 const buffers=new Map(),pending=new Map(),metrics={effects_started:0,effects_interrupted:0,music_starts:0,errors:[],last_effect:null};
 function activate(){
  if(!context){context=new AudioContext({latencyHint:'interactive'});master=context.createGain();musicGain=context.createGain();fxGain=context.createGain();
   analyser=context.createAnalyser();analyser.fftSize=2048;master.gain.value=volume;musicGain.gain.value=.65;fxGain.gain.value=.9;
   musicGain.connect(master);fxGain.connect(master);master.connect(analyser);analyser.connect(context.destination);}
  if(context.state==='suspended')context.resume().catch(error);return context;
 }
 function error(e){metrics.errors.push(e.message||String(e));}
 async function load(file){
  if(buffers.has(file))return buffers.get(file);if(pending.has(file))return pending.get(file);
  const task=(async()=>{const r=await fetch('/audio/'+file);if(!r.ok)throw Error('Ljudresurs saknas: '+file);
   const buffer=await context.decodeAudioData(await r.arrayBuffer());buffers.set(file,buffer);return buffer;})();
  pending.set(file,task);try{return await task;}finally{pending.delete(file);}
 }
 function musicPosition(){return position+(music?context.currentTime-musicStarted:0);}
 function stopMusic(){generation++;if(music){position=musicPosition();music.stop();music.disconnect();music=null;}}
 async function startMusic(){
  if(!context||!playing||!enabled||!musicEnabled||music)return;
  const selected=track,requested=context.currentTime,initial=position,version=generation;
  try{const t=manifest.tracks[selected],buffer=await load(t.file);
   if(version!==generation||selected!==track||!playing||!enabled||!musicEnabled||music)return;
   position=initial+context.currentTime-requested;
   let offset=position;if(offset>=t.loop_end_seconds)offset=t.loop_start_seconds+(offset-t.loop_start_seconds)%(t.loop_end_seconds-t.loop_start_seconds);
   const node=context.createBufferSource();node.buffer=buffer;node.loop=true;node.loopStart=t.loop_start_seconds;node.loopEnd=t.loop_end_seconds;
   node.connect(musicGain);node.start(0,offset);music=node;musicStarted=context.currentTime;metrics.music_starts++;
  }catch(e){error(e);}
 }
 function effect(index,targetTime,preview=false){
  if(!enabled||!context||!playing&&!preview)return;
  const spec=manifest.effects[index];if(!spec){error(Error('Okänd ljudeffekt '+index));return;}
  const request=++effectRequest,buffer=buffers.get(spec.file);
  if(!buffer){load(spec.file).then(()=>{if(request===effectRequest)effect(index,targetTime,preview);}).catch(error);return;}
  const now=context.currentTime,when=Math.max(now+.002,targetTime);
  if(fx){try{fx.stop(when);}catch{}metrics.effects_interrupted++;}
  fx=context.createBufferSource();fx.buffer=buffer;fx.connect(fxGain);fx.start(when);
  const node=fx;fx.onended=()=>{node.disconnect();if(fx===node)fx=null;};
  metrics.effects_started++;metrics.last_effect={index,target_time:targetTime,scheduled_time:when,late_ms:Math.max(0,(now-targetTime)*1000)};
 }
 function play(){activate();playing=true;for(const s of manifest.effects)load(s.file).catch(error);startMusic();}
 function pause(){playing=false;effectRequest++;stopMusic();if(fx){fx.stop();fx=null;}}
 function select(index){stopMusic();track=index;position=0;if(playing)startMusic();}
 function configure(e,m,v){enabled=e;musicEnabled=m;volume=v;if(master)master.gain.value=enabled?volume:0;
  if(!enabled||!musicEnabled)stopMusic();else startMusic();}
 function diagnostics(){let rms=0;if(analyser){const a=new Float32Array(analyser.fftSize);analyser.getFloatTimeDomainData(a);rms=Math.sqrt(a.reduce((s,v)=>s+v*v,0)/a.length);}
  return {...metrics,context:context?.state||'not-started',enabled,music_enabled:musicEnabled,playing,track,loaded_buffers:buffers.size,
   output_rms:+rms.toFixed(6),music_position_seconds:+musicPosition().toFixed(3),base_latency:context?.baseLatency??null,output_latency:context?.outputLatency??null};}
 async function preview(index){activate();await load(manifest.effects[index].file);effect(index,context.currentTime,true);}
 return {activate,play,pause,select,configure,effect,preview,diagnostics,now:()=>context?.currentTime||0};
}
if(typeof module!=='undefined')module.exports={createSkyRoadsAudio};
