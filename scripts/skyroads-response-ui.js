/* Optional host timing observation. Does not alter input, clocks or physics. */
(()=>{
 const recordBase=recordKey,captureBase=capture,drawBase=draw,clockBase=clockStart,recordingBase=recording;
 const box=document.createElement('details'),pre=document.createElement('pre');
 box.innerHTML='<summary>Responsmätning</summary>';pre.id='responseDetails';pre.className='raw';box.append(pre);$('timing').parentElement.after(box);
 let events=[],pending=[],epoch=0,draws=0,observedFrames=frames;
 const stateOf=()=>{const s=game.attempt.state;return {forward:s.forward,lateral:s.lateral,height:s.height,speed:s.speed,vertical_speed:s.vertical_speed};};
 function report(){pre.textContent=JSON.stringify({endpoint:'keydown receipt → original step → canvas draw return; excludes physical display latency',
   epoch,draws,events:events.slice(-16)},null,2);}
 clockStart=function(){if(observedFrames!==frames){events=[];draws=0;observedFrames=frames;}epoch++;pending=[];return clockBase();};
 recordKey=function(index,down,timestamp){
   const received=performance.now(),before=stateOf(),n=audit.length,result=recordBase(index,down,timestamp),entry=audit[n];
   if(events.length>=4096)events.shift();
   const e={epoch,index,down,timestamp,received_ms:received,queued_frame:entry?.frame,
     applied:entry?.applied||'timer',before};events.push(e);
   if(entry?.applied==='pause_poll'){e.applied_ms=performance.now();e.sample=frames.length-1;e.after=stateOf();}
   else pending.push(e);report();return result;
 };
 capture=function(sample,before){const result=captureBase(sample,before),now=performance.now();
   pending=pending.filter(e=>{if(e.queued_frame>quantum-1)return true;
     e.applied_ms=now;e.sample=frames.length-1;e.after=stateOf();return false;});return result;
 };
 draw=function(){const result=drawBase(),now=performance.now();draws++;
   for(const e of events)if(e.applied_ms!==undefined&&e.canvas_ms===undefined){e.canvas_ms=now;
     e.receipt_to_step_ms=+(e.applied_ms-e.received_ms).toFixed(3);
     e.receipt_to_canvas_ms=+(now-e.received_ms).toFixed(3);}
   report();return result;
 };
 recording=function(){return {...recordingBase(),response_observation:{format:'skyroads-host-response-v1',
   endpoint:'canvas draw return, not compositor or photons',events:events.map(e=>({...e}))}};};
 report();
})();
