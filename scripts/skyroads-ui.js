'use strict';
const $=id=>document.getElementById(id),view=$('view'),ctx=view.getContext('2d'),map=$('map'),mctx=map.getContext('2d');
const C=['#172334','#789ab6','#d0ad4d','#86a6b9','#cd8f79','#839bb1','#79aab0','#a38ac0','#8ac6d3','#4fcaa1','#689efa','#a1bd72','#df687b','#a399c1','#c5b187','#728caa'];
const KEY_INDEX={ArrowUp:0,Numpad8:0,ArrowDown:1,Numpad2:1,ArrowLeft:2,Numpad4:2,ArrowRight:3,Numpad6:3,
  Home:4,Numpad7:4,PageUp:5,Numpad9:5,End:6,Numpad1:6,PageDown:7,Numpad3:7,Escape:8,Space:9,KeyP:10};
let catalog,geo,physics,cycle,game,input,state,frames=[],running=false,replayPlaying=false,replayIndex=0,busy=false,last=performance.now(),dirty=true;
let audit=[],segments=[],cpuMax=0,cpuTotal=0,cpuCount=0,lateEvents=0,renderMax=0,replayAccumulator=0,profile=Array(30).fill(0);
let quantum=0;
let frameTimes=[0];
let displayedState,presentationFrames=[];
const exits={1:'Krasch',2:'Farlig markyta',3:'Föll från banan',4:'Bränsle slut',5:'Syre slut'};
function status(text,error=false,terminal=false){$('status').textContent=text;$('status').dataset.error=error;$('status').dataset.terminal=terminal;}
async function api(path,body){const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),value=await r.json();if(!r.ok)throw Error(value.error||'Verifieringen misslyckades');return value;}
function road(){return catalog.roads[Number($('road').value)];}
function clockStart(){const now=performance.now();input.reset(now-quantum*catalog.tick_seconds*1000,quantum);
  segments.push({frame:game.samples.length,quantum,origin:input.origin,started:now});last=now;
  if($('auto').checked)recordKey(0,true,now);
}
function recordKey(index,down,time){
  // The original pause loops busy-poll IRQ bits between timer interrupts.
  // Preserve even a press/release entirely between two physics boundaries.
  if(game.phase==='attempt'&&game.attempt.phase.startsWith('pause_')){
    input.mask=down?input.mask|(1<<index):input.mask&~(1<<index);
    audit.push({index,down,timestamp:time,frame:quantum,applied:'pause_poll',sample:game.samples.length});
    const before=game.snapshot(),sample=game.advance(input.mask,0,false);capture(sample,before);refresh();return;
  }
  const e=input.enqueue(index,down,time);audit.push(e);if(e.late_frames)lateEvents++;
}
function hostPause(message){running=false;replayPlaying=false;replayAccumulator=0;if(input){input.pending=[];input.clearHeld();}if(message)status(message);refresh();}
function refresh(){if(!state)return;const snapshot=frames[Number($('timeline').value)]||game.snapshot();
  $('ticks').textContent=state.tick_counter+' · försök '+snapshot.attempt_number;
  $('time').textContent=(frameTimes[Number($('timeline').value)]??0).toFixed(2)+' s';
  $('row').textContent=(state.forward/65536).toFixed(3);$('speed').textContent=state.speed;$('height').textContent=state.height+' / '+state.vertical_speed;
  $('fuel').style.width=(state.fuel/300)+'%';$('oxygen').style.width=(state.oxygen/300)+'%';
  $('raw').textContent=JSON.stringify(snapshot,null,2);$('timelineLabel').textContent=$('timeline').value+' / '+(frames.length-1)+' steg';
  $('timeline').disabled=frames.length<2;$('replay').disabled=frames.length<2||busy;$('save').disabled=frames.length<2||busy;
  $('step').disabled=running||replayPlaying||busy||game.phase==='selection';$('play').disabled=busy;
  $('play').textContent=running||replayPlaying?'Inspektionspaus':game.phase==='selection'?'Välj nästa bana':'Starta';
  $('timing').textContent=JSON.stringify({frames:game.samples.length,timer_quanta:quantum,phase:game.attempt.phase,mask:input.mask,
    physics_cpu_max_ms:+cpuMax.toFixed(3),physics_cpu_mean_ms:+(cpuTotal/Math.max(1,cpuCount)).toFixed(3),
    render_interval_max_ms:+renderMax.toFixed(3),late_input_events:lateEvents,
    last_input_events:audit.slice(-8)},null,2);dirty=true;
}
function describe(sample){const a=game.attempt;
  if(game.phase==='selection'){running=false;profile=[...game.completed];status(a.result===7?'Till banvalet · Escape.':(game.last_road?'Alla banor klara.':'Bana klar.')+' Nästa banval är återvunnet från originalet.',false,true);}
  else if(game.phase==='notice')status(game.last_road?'The End · originalets väntetid.':'Road completed · originalets väntetid.',false,true);
  else if(a.phase==='finishing')status('Banslut · originalets 72 timersteg.',false,true);
  else if(a.phase==='pause_release')status('Originalpaus · släpp P.');
  else if(a.phase==='pause_press')status('Originalpaus · tryck valfri speltangent för att fortsätta.');
  else if(a.phase==='pause_clear')status('Originalpaus · släpp alla speltangenter.');
  else if(sample.events.some(e=>e[0]==='restart'))status('Omstart · försök '+game.attempt_number+'. Originalets starttillstånd återställt.');
  else if(a.state.exit_state)status((exits[a.state.exit_state]||'Slutförlopp')+' · originalets fysik fortsätter.',false,true);
  else if(running)status('Kör · pilar, Space, P och Escape.');
}
function reset(){hostPause();game=new cycle.Game(catalog,Number($('road').value),$('assist').checked,profile);
  state=game.attempt.state;frames=[game.snapshot()];frameTimes=[0];quantum=0;audit=[];segments=[];cpuMax=cpuTotal=cpuCount=lateEvents=renderMax=0;
  displayedState={...state};presentationFrames=[displayedState];
  input=new SkyRoadsInputQueue(catalog.tick_seconds*1000);input.reset(performance.now());
  $('timeline').max=$('timeline').value='0';$('caption').textContent=game.index?'Bana '+game.index+' / 30':'Demoarkiv · manuell analys';
  $('recordingNote').textContent='Varje originalsteg och tidsstämplad tangentändring spelas in lokalt.';
  status('Redo. Starta och styr med piltangenterna.');refresh();
}
function capture(sample,before){
  displayedState=selectSkyRoadsPresentation(before,sample.snapshot,displayedState);presentationFrames.push(displayedState);
  if(sample.events.some(e=>e[0]==='restart')){input.clearHeld();$('auto').checked=false;}
  frames.push(sample.snapshot);state=game.attempt.state;$('timeline').max=frames.length-1;$('timeline').value=frames.length-1;describe(sample);
  frameTimes.push(frameTimes.at(-1)+sample.input.elapsed*catalog.tick_seconds);
}
function advance(){const start=performance.now(),before=game.snapshot(),keys=input.consume(quantum++);
  // BIOS notice dismissal is disabled in the normal original af32=0 mode.
  const sample=game.advance(keys.mask,1,false),duration=performance.now()-start;
  cpuMax=Math.max(cpuMax,duration);cpuTotal+=duration;cpuCount++;
  capture(sample,before);
}
function toggle(){if(running||replayPlaying){hostPause('Inspektionspaus · spelets klocka är fryst.');return;}
  if(game.phase==='selection'){$('road').value=Math.min(30,Math.max(1,game.selected+1));reset();}
  state=game.attempt.state;displayedState=presentationFrames.at(-1);$('timeline').value=frames.length-1;clockStart();running=true;status('Kör · lokal heltalsfysik vid varje originalsteg.');view.focus();refresh();
}
function recording(){return {...game.recording(),browser_timing:{input_events:audit,clock_segments:segments,
  physics_cpu_max_ms:cpuMax,physics_cpu_mean_ms:cpuTotal/Math.max(1,cpuCount),render_interval_max_ms:renderMax,late_input_events:lateEvents}};}
$('play').onclick=toggle;$('step').onclick=()=>{if(!game||game.phase==='selection')return;
  input.reset(performance.now()-quantum*input.dt,quantum);if($('auto').checked)input.enqueue(0,true,performance.now());advance();refresh();};
$('reset').onclick=reset;$('road').onchange=reset;$('assist').onchange=reset;
$('auto').onchange=()=>{if(running)recordKey(0,$('auto').checked,performance.now());};
$('timeline').oninput=()=>{hostPause();state=frames[Number($('timeline').value)].state;displayedState=presentationFrames[Number($('timeline').value)];status('Inspektion · steg '+$('timeline').value+'.');refresh();};
$('replay').onclick=async()=>{hostPause();busy=true;refresh();try{
  const rec=recording(),result=await api('/api/cycles/replay',{recording:rec});
  frames=result.frames;replayIndex=0;state=frames[0].state;displayedState=presentationFrames[0];$('timeline').max=frames.length-1;$('timeline').value=0;
  replayPlaying=true;last=performance.now();status('Python verifierade hela replayen · '+result.ticks+' originalsteg.');
  $('recordingNote').textContent='Lokala tillstånd, inmatning och spelövergångar matchar Python steg för steg.';
}catch(e){status(e.message,true);}finally{busy=false;refresh();}};
$('save').onclick=async()=>{hostPause();busy=true;refresh();try{const result=await api('/api/cycles/save',{recording:recording()});
  $('recordingNote').textContent='Sparad och verifierad: '+result.saved_path;status('Körningen sparad · '+result.ticks+' originalsteg.');
}catch(e){status(e.message,true);}finally{busy=false;refresh();}};
window.addEventListener('keydown',event=>{if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(event.target.tagName))return;
  const index=KEY_INDEX[event.code];if(index===undefined)return;event.preventDefault();
  if(running)recordKey(index,true,event.timeStamp>1e12?event.timeStamp-performance.timeOrigin:event.timeStamp);
});
window.addEventListener('keyup',event=>{const index=KEY_INDEX[event.code];if(index===undefined)return;event.preventDefault();
  if(running)recordKey(index,false,event.timeStamp>1e12?event.timeStamp-performance.timeOrigin:event.timeStamp);
});
window.addEventListener('blur',()=>{if(running||replayPlaying)hostPause('Inspektionspaus när fönstret tappade fokus.');});
document.addEventListener('visibilitychange',()=>{if(document.hidden)hostPause('Inspektionspaus när fliken doldes.');});
function animate(now){const delta=Math.max(0,now-last);last=now;
  try{if(running){renderMax=Math.max(renderMax,delta);const due=Math.floor((now-input.origin)/input.dt)-quantum;
    if(due>36){hostPause('Inspektionspaus: fliken låg efter mer än en sekund.');}
    else {for(let n=0;n<due&&running;n++)advance();if(due>0)refresh();}
  }else if(replayPlaying){replayAccumulator+=delta;while(replayPlaying){
    const delay=(game.samples[replayIndex]?.input.elapsed??1)*input.dt;
    if(replayAccumulator<delay)break;replayAccumulator-=delay;
    if(++replayIndex>=frames.length){replayPlaying=false;status('Replay klar · varje originalsteg matchade.');break;}
    state=frames[replayIndex].state;displayedState=presentationFrames[replayIndex];$('timeline').value=replayIndex;refresh();}
  }if(dirty){draw();dirty=false;}}
  catch(e){hostPause();status(e.message,true);}
  requestAnimationFrame(animate);
}
window.addEventListener('resize',()=>dirty=true);
(async()=>{try{catalog=await api('/api/catalog');physics=createPhysics(catalog.tables);geo=physics.geometry;cycle=createCycle(physics);
  for(const r of catalog.roads){const option=document.createElement('option');option.value=r.index;option.textContent=r.index?'Bana '+String(r.index).padStart(2,'0')+' · '+r.rows.length+' rader':'Demoarkiv 00 · manuell analys';$('road').append(option);}
  $('road').value='1';$('road').disabled=false;$('reset').disabled=false;$('rate').textContent=catalog.physics_hz.toFixed(3)+' Hz · lokal fysik';reset();
}catch(e){status(e.message,true);}requestAnimationFrame(animate);})();

function resize(canvas){const rect=canvas.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,2);const w=Math.round(rect.width*ratio),h=Math.round(rect.height*ratio);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}return [w,h];}
function draw(){const state=displayedState;if(!state||!catalog)return;const [w,h]=resize(view),row=state.forward/65536,shipX=(state.lateral-32768)/5888,shipY=(state.height-10240)/5888;const focal=w*.64,cameraY=1.35+Math.max(0,shipY)*.45;
const sky=ctx.createLinearGradient(0,0,0,h);sky.addColorStop(0,'#10172b');sky.addColorStop(.4,'#253d58');sky.addColorStop(1,'#0b1522');ctx.fillStyle=sky;ctx.fillRect(0,0,w,h);ctx.strokeStyle='#628aa34a';ctx.beginPath();ctx.moveTo(0,h*.29);ctx.lineTo(w,h*.29);ctx.stroke();
const project=(x,y,z)=>{const depth=z+3.5;return [w*.5+(x-shipX*.65)*focal/depth,h*.29+(cameraY-y)*focal/depth];};
const faces=[];function face(points,color,stroke='#dbeaff24'){faces.push({points,color,stroke,depth:points.reduce((sum,p)=>sum+p[2],0)/points.length});}
function solid(x0,x1,lo0,lo1,hi0,hi1,z0,z1,color){if(Math.max(hi0,hi1)<=Math.min(lo0,lo1))return;face([[x0,hi0,z0],[x1,hi1,z0],[x1,hi1,z1],[x0,hi0,z1]],color);face([[x0,lo0,z0],[x1,lo1,z0],[x1,hi1,z0],[x0,hi0,z0]],color);face([[x0,lo0,z0],[x0,lo0,z1],[x0,hi0,z1],[x0,hi0,z0]],color);face([[x1,lo1,z0],[x1,lo1,z1],[x1,hi1,z1],[x1,hi1,z0]],color);}
for(let r=Math.max(0,Math.floor(row)-1);r<Math.min(road().rows.length,Math.floor(row)+22);r++){const z0=(r-row)*1.2,z1=z0+1.2;if(z0+3.5<=.4)continue;for(let c=0;c<7;c++){const v=road().rows[r][c],ground=v&15,top=(v>>4)&15,kind=(v>>8)&15,x0=c-3.5,x1=x0+1;if(ground)face([[x0,0,z0],[x1,0,z0],[x1,0,z1],[x0,0,z1]],C[ground]);if(kind===2||kind===4)solid(x0,x1,0,0,(catalog.tables.support[kind]-10240)/5888,(catalog.tables.support[kind]-10240)/5888,z0,z1,C[top||3]);else if([1,3,5].includes(kind)){for(let q=0;q<46;q+=4){const q1=Math.min(q+4,46),a=geo.fold((95+c*46+q)*128),b=geo.fold((95+c*46+Math.min(q1,45))*128),lowA=(8704+catalog.tables.lower[a]*128-10240)/5888,lowB=(8704+catalog.tables.lower[b]*128-10240)/5888;const highA=kind===1?(8704+catalog.tables.upper[a]*128-10240)/5888:(catalog.tables.support[kind]-10240)/5888,highB=kind===1?(8704+catalog.tables.upper[b]*128-10240)/5888:highA;solid(x0+q/46,x0+q1/46,Math.max(0,lowA),Math.max(0,lowB),highA,highB,z0,z1,C[top||3]);}}}}
faces.sort((a,b)=>b.depth-a.depth);for(const f of faces){const points=f.points.map(p=>project(...p));ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fillStyle=f.color;ctx.fill();ctx.strokeStyle=f.stroke;ctx.lineWidth=.65;ctx.stroke();}
// Own ship glyph: visual hull is illustrative, collision footprint follows the validated local integer core.
const hull=[[shipX-.29,shipY+.08,-.12],[shipX-.19,shipY+.16,.28],[shipX,shipY+.27,.43],[shipX+.19,shipY+.16,.28],[shipX+.29,shipY+.08,-.12],[shipX,shipY+.12,-.3]].map(p=>project(...p));ctx.beginPath();hull.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fillStyle=state.crash_ticks?'#e57a84':'#dcecff';ctx.fill();ctx.strokeStyle='#6bb3df';ctx.lineWidth=2;ctx.stroke();const canopy=project(shipX,shipY+.23,.04);ctx.fillStyle='#294f7f';ctx.beginPath();ctx.ellipse(canopy[0],canopy[1],w*.018,w*.009,0,0,Math.PI*2);ctx.fill();
const [mw,mh]=resize(map);mctx.fillStyle='#09111d';mctx.fillRect(0,0,mw,mh);const cell=mw/7,rh=mh/15,base=Math.floor(row)-2;for(let k=0;k<15;k++){const r=base+k;if(r<0||r>=road().rows.length)continue;for(let c=0;c<7;c++){const v=road().rows[r][c],y=mh-(k+1)*rh;mctx.fillStyle=C[v&15];if(v&15)mctx.fillRect(c*cell+1,y+1,cell-2,rh-2);if(v&0xf00){mctx.strokeStyle='#cbdaf099';mctx.strokeRect(c*cell+3,y+3,cell-6,rh-6);}}}const mx=(state.lateral-12160)/(7*5888)*mw,my=mh-((row-base)+.5)*rh;mctx.fillStyle='#fff';mctx.beginPath();mctx.arc(mx,my,4*(devicePixelRatio||1),0,Math.PI*2);mctx.fill();}
