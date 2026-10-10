/* Touch controls feed the same timestamped eleven-key queue as the keyboard. */
function createSkyRoadsInputSources(emit){
 const held=new Map();
 const active=index=>[...held.values()].includes(index);
 function release(source,time){if(!held.has(source))return;const index=held.get(source);held.delete(source);if(!active(index))emit(index,false,time);}
 return {
   press(source,index,time){if(held.get(source)===index)return;release(source,time);const was=active(index);held.set(source,index);if(!was)emit(index,true,time);},
   release,
   clear(time){for(const source of [...held.keys()])release(source,time);},
   mask(){return [...held.values()].reduce((m,index)=>m|(1<<index),0);}
 };
}
if(typeof module!=='undefined')module.exports={createSkyRoadsInputSources};
if(typeof window!=='undefined')(()=>{
 const css=document.createElement('style');css.textContent=`
 .mobile-ui,.rotate-hint{display:none}
 @media (pointer:coarse), (max-width:900px) and (max-height:600px){
   html.mobile-layout body{overflow:hidden;overscroll-behavior:none}
   html.mobile-layout header,html.mobile-layout footer,html.mobile-layout .side,html.mobile-layout .desktop-controls{display:none}
   html.mobile-layout main{display:block;max-width:none;margin:0;padding:0}
   html.mobile-layout .stage{border:0;border-radius:0;margin:0;position:fixed;inset:0;background:#080c13}
   html.mobile-layout .stage canvas{height:100svh;min-height:0;width:100%;touch-action:none}
   html.mobile-layout .stage-caption{display:none}
   html.mobile-layout .stage .status{position:absolute;bottom:max(7px,env(safe-area-inset-bottom));left:25%;right:25%;min-height:0;border:0;padding:4px;background:#080c13c9;font-size:10px;pointer-events:none;text-align:center;border-radius:4px}
   html.mobile-layout .mobile-ui{display:flex}
   .mobile-bar{position:fixed;z-index:4;top:max(5px,env(safe-area-inset-top));left:max(10px,env(safe-area-inset-left));right:max(10px,env(safe-area-inset-right));align-items:center;gap:8px;pointer-events:none}
   .mobile-bar button{pointer-events:auto;font-size:12px;padding:7px 12px;background:#142234e8}
   .mobile-bar strong{margin-right:auto;font-size:12px;color:#bad0e5}
   .touch-pad{position:fixed;z-index:3;bottom:max(14px,env(safe-area-inset-bottom));gap:8px;touch-action:none}
   .touch-pad-left{left:max(12px,env(safe-area-inset-left));align-items:flex-end}
   .touch-pad-right{right:max(12px,env(safe-area-inset-right));display:grid!important;grid-template-columns:68px 68px}
   .touch-pad button{touch-action:none;-webkit-touch-callout:none;user-select:none;-webkit-user-select:none;border:1px solid #91b4d17d;background:#193047d9;color:#e7f4ff;font-weight:700;min-width:64px;min-height:58px;padding:6px;border-radius:14px}
   .touch-pad button[data-held=true]{background:#32765df2;border-color:#b2ffe2;transform:translateY(1px)}
   .touch-pad button:disabled{opacity:.35}
   .touch-pad-left button{font-size:28px;min-height:68px}
   .touch-pad-right .jump{grid-column:1/3;background:#245744dc;font-size:16px;min-height:60px}
   html.mobile-layout .side.mobile-options-open{display:block;position:fixed;inset:0 0 0 auto;z-index:8;width:min(370px,100%);padding:12px;background:#0b1522;overflow:auto;overscroll-behavior:contain}
   .mobile-close{display:block;margin:4px 0 14px auto}
   html.mobile-layout.portrait .rotate-hint{display:flex;position:fixed;inset:0;z-index:10;background:#0c1420f2;align-items:center;justify-content:center;text-align:center;padding:30px;font-size:20px;line-height:1.6}
 }
 @media (pointer:fine) and (min-width:901px){.mobile-close{display:none}}
 `;document.head.append(css);
 const controls=$('play').closest('.card');controls.classList.add('desktop-controls');
 const bar=document.createElement('div');bar.className='mobile-ui mobile-bar';bar.innerHTML='<strong>SkyRoads</strong><button type="button" id="touchPlay">Starta</button><button type="button" id="touchOptions">Bana / ljud</button><button type="button" id="touchFullscreen" aria-label="Helskärm">⛶</button>';
 const left=document.createElement('div');left.className='mobile-ui touch-pad touch-pad-left';
 left.innerHTML='<button type="button" data-key="2" aria-label="Styr vänster">◀</button><button type="button" data-key="3" aria-label="Styr höger">▶</button>';
 const right=document.createElement('div');right.className='mobile-ui touch-pad touch-pad-right';
 right.innerHTML='<button type="button" data-key="0" aria-label="Gasa">GAS</button><button type="button" data-key="1" aria-label="Bromsa">BROMS</button><button type="button" data-key="9" class="jump" aria-label="Hoppa">HOPP</button>';
 const hint=document.createElement('div');hint.className='rotate-hint';hint.textContent='Vrid mobilen till liggande läge för att spela ↻';
 document.body.append(bar,left,right,hint);
 const close=document.createElement('button');close.className='mobile-close';close.textContent='Tillbaka till spelet';document.querySelector('.side').prepend(close);
 const baseKey=recordKey,basePause=hostPause,baseCapture=capture;
 const sources=createSkyRoadsInputSources((index,down,time)=>baseKey(index,down,time));
 const pads=[...document.querySelectorAll('.touch-pad button')];
 function clear(){sources.clear(performance.now());for(const b of pads){b.dataset.held='false';b.setAttribute('aria-pressed','false');}}
 recordKey=function(index,down,time){const source='keyboard-'+index;if(down)sources.press(source,index,time);else sources.release(source,time);};
 hostPause=function(...args){clear();return basePause(...args);};
 capture=function(sample,before){const result=baseCapture(sample,before);if(sample.events.some(e=>e[0]==='restart'))clear();return result;};
 const eventTime=e=>e.timeStamp>1e12?e.timeStamp-performance.timeOrigin:e.timeStamp;
 function released(e){e.preventDefault();sources.release('pointer-'+e.pointerId,eventTime(e));e.currentTarget.dataset.held=String(!!(sources.mask()&(1<<Number(e.currentTarget.dataset.key))));e.currentTarget.setAttribute('aria-pressed',e.currentTarget.dataset.held);}
 for(const b of pads){b.setAttribute('aria-pressed','false');
   b.addEventListener('pointerdown',e=>{if(!running||e.pointerType==='mouse'&&e.button!==0)return;e.preventDefault();
     b.setPointerCapture(e.pointerId);sources.press('pointer-'+e.pointerId,Number(b.dataset.key),eventTime(e));b.dataset.held='true';b.setAttribute('aria-pressed','true');});
   for(const name of ['pointerup','pointercancel','lostpointercapture'])b.addEventListener(name,released);
   b.addEventListener('contextmenu',e=>e.preventDefault());
 }
 $('touchPlay').onclick=()=>{$('play').click();};
 $('touchOptions').onclick=()=>{hostPause('Inspektionspaus · välj bana eller ljud.');document.querySelector('.side').classList.add('mobile-options-open');};
 close.onclick=()=>document.querySelector('.side').classList.remove('mobile-options-open');
 $('touchFullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else if(document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen();else status('Använd webbläsarens helskärmsläge.');}catch{status('Helskärm är inte tillgängligt i webbläsaren.');}};
 function layout(){const mobile=matchMedia('(pointer:coarse), (max-width:900px) and (max-height:600px)').matches;
   document.documentElement.classList.toggle('mobile-layout',mobile);document.documentElement.classList.toggle('portrait',innerHeight>innerWidth);
   if(mobile&&innerHeight>innerWidth&&running)hostPause('Inspektionspaus · vrid mobilen.');dirty=true;}
 window.addEventListener('resize',()=>{clear();layout();});window.addEventListener('orientationchange',()=>{hostPause('Inspektionspaus · skärmen roterades.');layout();});
 document.addEventListener('fullscreenchange',()=>{clear();dirty=true;});
 for(const id of ['reset','road','assist'])$(id).addEventListener(id==='reset'?'click':'change',clear);
 setInterval(()=>{const b=$('touchPlay');b.textContent=$('play').textContent;b.disabled=$('play').disabled;
   for(const pad of pads)pad.disabled=!running;},100);
 layout();
})();
