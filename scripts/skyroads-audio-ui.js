/* Audio bridge outside the physics/input replay identity. */
(()=>{
 let engine,manifest,origin=0,active=false,replaySample=0,replayRequested=false,plan=[{sample:0,track:1}],audit=[],currentRoad=1;
 const names=['Krasch','Landning','Stöt mot hinder','Resursvarning','Påfyllning'];
 const audioStatus=$('audioStatus'),audioDetails=$('audioDetails'),trackSelect=$('musicTrack');
 for(let i=0;i<10;i++){const option=document.createElement('option');option.value=i;option.textContent=i?'Banspår '+i:'Titel / demo';trackSelect.append(option);}trackSelect.value='1';
 const captureBase=capture,refreshBase=refresh,clockBase=clockStart,pauseBase=hostPause,recordingBase=recording;
 function selectedTrack(){return Number(trackSelect.value);}
 function settings(){engine?.configure($('soundEnabled').checked,$('musicEnabled').checked,Number($('soundVolume').value)/100);}
 function effects(sample,index,time,record=true){for(const e of sample?.events||[])if(e[0]==='sound'){
  engine?.effect(e[1],time);if(record)audit.push({sample:index,effect:e[1],name:names[e[1]],simulation_seconds:frameTimes[index]});}}
 function begin(){if(!engine||active)return;engine.play();origin=engine.now()-(frameTimes[Number($('timeline').value)]||0);active=true;}
 function stop(){engine?.pause();active=false;}
 clockStart=function(){clockBase();if(game.index!==currentRoad)freshTrack(true);begin();};
 hostPause=function(...args){stop();return pauseBase(...args);};
 capture=function(sample,before){captureBase(sample,before);if(active)effects(sample,game.samples.length,origin+frameTimes.at(-1));};
 refresh=function(){refreshBase();if(!engine)return;
  if(replayPlaying){
   if(replayRequested){engine.select(plan[0].track);trackSelect.value=String(plan[0].track);replaySample=0;replayRequested=false;}
   begin();const current=Number($('timeline').value);
   for(let i=replaySample+1;i<=current;i++){
    const selection=plan.find(s=>s.sample===i);if(selection){engine.select(selection.track);trackSelect.value=String(selection.track);}
    effects(game.samples[i-1],i,origin+frameTimes[i],false);
   }replaySample=current;
  }else if(!running&&active)stop();
 };
 recording=function(){return {...recordingBase(),audio:{format:'skyroads-audio-plan-v1',music_selections:plan.map(x=>({...x})),
  sources:manifest?.source_sha256||{},effects:audit.filter(e=>e.sample<=game.samples.length)}};};
 function freshTrack(change){stop();audit=[];currentRoad=game?.index??1;if(change){let next=1+crypto.getRandomValues(new Uint32Array(1))[0]%9;
  if(next===selectedTrack())next=next%9+1;trackSelect.value=String(next);}
  if(currentRoad===0)trackSelect.value='0';
  plan=[{sample:0,track:selectedTrack()}];engine?.select(selectedTrack());replaySample=0;}
 $('road').addEventListener('change',()=>freshTrack(true));$('reset').addEventListener('click',()=>freshTrack(false));$('assist').addEventListener('change',()=>freshTrack(false));
 $('replay').addEventListener('click',()=>{replayRequested=true;});
 trackSelect.addEventListener('change',()=>{engine?.select(selectedTrack());const sample=replayPlaying?Number($('timeline').value):game?.samples.length||0;
  plan=plan.filter(s=>s.sample!==sample);plan.push({sample,track:selectedTrack()});plan.sort((a,b)=>a.sample-b.sample);view.focus();});
 for(const id of ['soundEnabled','musicEnabled','soundVolume'])$(id).addEventListener('input',settings);
 $('testSound').addEventListener('click',async()=>{if(!engine)return;try{await engine.preview(1);audioStatus.textContent='Provspelar originalets landningsljud.';}catch(e){audioStatus.textContent=e.message;}});
 fetch('/audio/manifest.json').then(r=>{if(!r.ok)throw Error('Ljudresurser kunde inte läsas');return r.json();}).then(m=>{
  manifest=m;engine=createSkyRoadsAudio(m);settings();audioStatus.textContent='Originalmusik och ljud redo · aktiveras när du startar.';
  $('testSound').disabled=false;
 }).catch(e=>audioStatus.textContent=e.message);
 setInterval(()=>{if(!engine)return;if(active&&!running&&!replayPlaying){stop();refreshBase();}
  const d=engine.diagnostics();audioDetails.textContent=JSON.stringify(d,null,2);
  if(d.errors.length)audioStatus.textContent=d.errors.at(-1);
  else if(active)audioStatus.textContent=$('soundEnabled').checked?'Ljud på · '+(d.music_enabled?'musikspår '+d.track:'musik av'):'Ljud av';
 },250);
})();
