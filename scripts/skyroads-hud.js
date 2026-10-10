/* Original VGA dashboard. Pure indexed pixel updates; no physics/sound writes.
 * Assembly: 0f62..1630, static gravity number in 2b3d. */
function createSkyRoadsHud(assets){
 const u16=n=>n&65535,u32=n=>n>>>0,s32=n=>n|0;
 function counters(){return {speed:0,oxygen:0,fuel:0,progress:0,assist:65535,blink:0};}
 function mask(frame,destination,width,height,bytes,one,two,transparent){
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
   const source=bytes[y*width+x],color=source===0?0:source===1?one:two;
   if(!transparent||color)frame[destination+y*320+x]=color;
  }
 }
 function number(frame,x,y,value,places){
  value=u16(value);
  for(let i=0;i<places;i++){
   if(!value&&i!==0)break;
   const power=10**i,digit=Math.floor(value/power)%10;
   mask(frame,y*320+x+(places-i-1)*5,4,5,assets.symbols.digits[digit],97,98,false);
   value-=digit*power;
  }
 }
 function initialize(frame,gravity){number(frame,96,156,u16((gravity-3)*100),4);return counters();}
 function levels(s,timer,rows){
  // 5e5a is signed long division; the low result word is then clamped unsigned.
  const speed=Math.min(34,u16(Math.trunc(s32(s.speed-s.speed_delta)/321)));
  const resource=n=>Math.min(10,Math.floor(u16(n+2999)/3000));
  // The denominator uses signed 5e5a; progress then uses unsigned 5d8c.
  const denominator=Math.trunc(s32((rows-3)*65536)/30);
  if(!denominator)throw Error('Invalid original progress denominator');
  return {speed,oxygen:resource(s.oxygen),fuel:resource(s.fuel),
   progress:Math.min(29,u16(Math.floor(u32(s.forward-3*65536)/denominator))),
   assist:u16(s.assist_flag),blink:Number(u16(timer)%9>4)};
 }
 function update(frame,previous,s,timer,rows){
  const next=levels(s,timer,rows);
  function instrument(key){
   for(let i=Math.min(previous[key],next[key]);i<Math.max(previous[key],next[key]);i++){
    const r=assets.instruments[key].records[i],on=next[key]>previous[key];
    mask(frame,r.destination,r.width,r.height,r.pixels,on?94:92,on?95:93,true);
   }
  }
  function swap(x,y,w,h){for(let r=0;r<h;r++)for(let c=0;c<w;c++){
   const at=(y+r)*320+x+c;if(frame[at]===99)frame[at]=100;else if(frame[at]===100)frame[at]=99;
  }}
  instrument('speed');instrument('oxygen');
  if(s.exit_state===5&&next.blink!==previous.blink)swap(160,161,7,7);
  instrument('fuel');
  if(s.exit_state===4&&next.blink!==previous.blink)swap(155,169,16,5);
  for(let i=previous.progress;i<next.progress;i++){
   const x=i+42,color=frame[143*320+x];let y=143;
   while(y>=0&&frame[y*320+x]===color)y--;
   if(y<0)throw Error('Original progress column has no upper boundary');
   while(++y<200&&frame[y*320+x]===color)frame[y*320+x]=96;
  }
  if(next.assist!==previous.assist){
   const bytes=assets.symbols.assist[next.assist];if(!bytes)throw Error('Invalid original assist flag');
   mask(frame,156*320+203,26,5,bytes,97,98,false);
  }
  return next;
 }
 return {initialize,counters,levels,update};
}
/* Snapshot history supplies the same HUD-call boundary as the verified cycle.
 * Original finish and P-pause loops do not call 12f8. Reuse identical pictures
 * rather than allocating a dashboard bitmap for every physics step. */
function createSkyRoadsHudTimeline(hud,background,gravity,rows){
 let source=null,images=[],frame,cache,image,id=0;
 function sync(frames){
  if(source!==frames){source=frames;images=[];id=0;}
  for(let i=images.length;i<frames.length;i++){
   const f=frames[i],newAttempt=i===0||f.attempt_number!==frames[i-1].attempt_number;
   let changed=newAttempt;
   if(newAttempt){frame=new Uint8Array(background);cache=hud.initialize(frame,gravity);}
   if(f.game_phase==='attempt'&&f.phase==='playing'){
    const next=hud.update(frame,cache,f.state,f.timer,rows);
    changed||=['speed','oxygen','fuel','progress','assist'].some(k=>cache[k]!==next[k])||
     ([4,5].includes(f.state.exit_state)&&cache.blink!==next.blink);
    cache=next;
   }
   if(changed)image={pixels:frame.slice(44160),id:++id};
   images.push({image,levels:{...cache}});
  }
 }
 return {sync,get:index=>images[index],pictures:()=>id};
}
if(typeof module!=='undefined')module.exports={createSkyRoadsHud,createSkyRoadsHudTimeline};
