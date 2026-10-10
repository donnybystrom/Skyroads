/* Original wait boundaries, pause protocol and attempt lifecycle. */
function createCycle(physics) {
  const u16=n=>n&65535,u32=n=>n>>>0,undefinedLocals=['jump_height','edge_distance','previous_target_height'];
  const copy=n=>JSON.parse(JSON.stringify(n));
  function decode(mask){if(!Number.isInteger(mask)||mask<0||mask>=2048)throw Error('Expected eleven-key mask');
    const held=(...ids)=>+ids.some(i=>mask&(1<<i));
    return {throttle:held(0,4,5)-held(1,6,7),direction:held(3,5,7)-held(2,4,6),jump:held(9)};
  }
  class Attempt {
    constructor(rows,config,seeds={}){this.rows=rows;this.config=config;this.state={...physics.defaults};
      for(const n of undefinedLocals)this.state[n]=u16(seeds[n]??0);
      this.timer=0;this.phase='playing';this.result=null;this.blink=0;this.pause_timer=0;
    }
    snapshot(){return {state:{...this.state},timer:this.timer,phase:this.phase,result:this.result,blink:this.blink,pause_timer:this.pause_timer};}
    finish(result,events){this.result=result;this.phase='returned';events.push(['return',result]);}
    gate(mask,events){const s=this.state;
      if(mask&256){this.finish(7,events);return;}
      if((s.crash_ticks===0||s.crash_ticks>42)&&([1,2].includes(s.exit_state)||(s.exit_state===3&&s.crash_ticks!==0)||s.end_ticks>=108)){this.finish(s.exit_state,events);return;}
      const blink=+(this.timer%9>4);
      if([4,5].includes(s.exit_state)&&blink!==this.blink&&blink){events.push(['sound',3]);s.sound_tick=this.timer;}
      this.blink=blink;this.phase='playing';
    }
    prepare(mask,events){if(this.timer<this.state.tick_counter)this.timer=this.state.tick_counter=0;
      this.pause_timer=this.timer;
      if(mask&1024){this.phase='pause_release';events.push(['pause']);return;}
      this.gate(mask,events);
    }
    advance(mask,elapsed=1,observer){decode(mask);const minimum=this.phase.startsWith('pause_')?0:1;if(!Number.isInteger(elapsed)||elapsed<minimum||elapsed>1024)throw Error('Invalid elapsed timer ticks');
      const events=[];if(this.phase==='returned')return events;this.timer=u16(this.timer+elapsed);
      if(this.phase.startsWith('pause_')){
        if(this.phase==='pause_release'&&!(mask&1024))this.phase='pause_press';
        if(this.phase==='pause_press'&&mask){if(mask&256)this.finish(7,events);else this.phase='pause_clear';}
        if(this.phase==='pause_clear'&&!mask){this.timer=this.pause_timer;this.phase='playing';events.push(['resume']);this.gate(0,events);}
      }else if(this.phase==='finishing'){
        this.state.forward=u32(this.state.forward+this.state.speed);events.push(['finish_frame']);
        if(this.timer>=72)this.finish(0,events);else if(mask&256)this.finish(7,events);
      }else{
        const controls=decode(mask);
        while(this.state.tick_counter<this.timer){const result=physics.tick(this.rows,this.state,this.config,{...controls,timer:this.timer},e=>events.push(e));this.state=result.state;
          if(result.completion_requested){this.state.height=0;this.timer=0;this.phase='finishing';if(mask&256)this.finish(7,events);break;}
        }
        if(this.phase==='playing')this.prepare(mask,events);
      }
      if(observer)for(const e of events)observer(e);return events;
    }
  }
  class Game {
    constructor(catalog,index=1,assist=true,completed=Array(30).fill(0)){
      this.catalog=catalog;this.index=index;this.assist=assist;this.completed=completed.map(u16);this.initial_completed=[...this.completed];
      if(this.completed.length!==30)throw Error('Expected thirty completion counters');
      this.attempt_number=1;this.phase='attempt';this.notice_ticks=0;this.selected=index?index-1:0;this.last_road=false;
      this.attempt=this.newAttempt();this.samples=[];
    }
    newAttempt(seeds={}){const r=this.catalog.roads[this.index],m=r.metadata;
      return new Attempt(r.rows,{gravity_factor:m[0],fuel_divisor:m[1],oxygen_factor:m[2],road_rows:r.rows.length,assist_enabled:+this.assist},seeds);}
    snapshot(){return {road_index:this.index,attempt_number:this.attempt_number,game_phase:this.phase,notice_ticks:this.notice_ticks,
      selected:this.selected,completed:[...this.completed],last_road:this.last_road,...this.attempt.snapshot()};}
    advance(mask,elapsed=1,notice_key=false){
      if(this.samples.length>=20000)throw Error('Recording limit reached');decode(mask);
      const minimum=this.phase==='attempt'&&this.attempt.phase.startsWith('pause_')?0:1;
      if(!Number.isInteger(elapsed)||elapsed<minimum||elapsed>1024)throw Error('Invalid elapsed timer ticks');if(typeof notice_key!=='boolean')throw Error('Invalid notice key');
      let events=[];
      if(this.phase==='notice'){
        this.notice_ticks=u16(this.notice_ticks+elapsed);
        if(this.notice_ticks>=27||notice_key){if(this.index){this.completed[this.index-1]=u16(this.completed[this.index-1]+1);this.selected=this.index;}
          this.phase='selection';events.push(['selection',this.selected]);}
      }else if(this.phase==='attempt'){
        events=this.attempt.advance(mask,elapsed);
        if(this.attempt.result!==null){const result=this.attempt.result;
          if(result===0){this.last_road=!!(this.index&&this.completed[this.index-1]===0&&this.completed.filter(n=>n!==0).length===29);this.phase='notice';this.notice_ticks=0;events.push(['notice',+this.last_road]);}
          else if(result===7||this.index===0){this.phase='selection';events.push(['selection',this.selected]);}
          else{const seeds={};for(const n of undefinedLocals)seeds[n]=this.attempt.state[n];this.attempt=this.newAttempt(seeds);this.attempt_number++;events.push(['restart',this.attempt_number]);}
        }
      }
      const selectedEvents=new Set(['sound','finish','finish_frame','pause','resume','return','restart','notice','selection']);
      const sample={frame:this.samples.length,input:{mask,elapsed,notice_key},snapshot:this.snapshot(),events:events.filter(e=>selectedEvents.has(e[0]))};
      this.samples.push(sample);return sample;
    }
    recording(){return {format:'skyroads-cycle-v2',road_index:this.index,assist:this.assist,
      road_sha256:this.catalog.roads[this.index].sha256,model_sha256:this.catalog.model_sha256,
      initial_completed:[...this.initial_completed],samples:copy(this.samples),final:this.snapshot()};}
  }
  function replay(catalog,recording){const g=new Game(catalog,recording.road_index,recording.assist,recording.initial_completed),frames=[g.snapshot()];
    for(const sample of recording.samples){const i=sample.input,actual=g.advance(i.mask,i.elapsed,i.notice_key);
      if(JSON.stringify(actual)!==JSON.stringify(sample))throw Error('Replay differs at frame '+sample.frame);frames.push(actual.snapshot);}
    return {verified:true,frames,ticks:g.samples.length,final:g.snapshot()};
  }
  return {Attempt,Game,decode,replay};
}

/* Timestamped hardware-key changes. First unprocessed timer boundary at or
 * after the event is the application frame. Render stalls cannot smear the
 * newest held state onto older frames. A genuinely late event is recorded. */
class SkyRoadsInputQueue {
  constructor(tickMilliseconds){this.dt=tickMilliseconds;this.reset(0);}
  reset(origin,nextFrame=0){this.origin=origin;this.nextFrame=nextFrame;this.mask=0;this.pending=[];this.audit=[];}
  enqueue(index,down,timestamp){
    if(!Number.isInteger(index)||index<0||index>10||!Number.isFinite(timestamp))throw Error('Invalid keyboard event');
    const intended=Math.max(0,Math.ceil((timestamp-this.origin)/this.dt)-1),frame=Math.max(this.nextFrame,intended);
    const event={index,down:!!down,timestamp,frame,intended_frame:intended,late_frames:frame-intended};
    this.pending.push(event);this.pending.sort((a,b)=>a.frame-b.frame||a.timestamp-b.timestamp);this.audit.push({...event});return event;
  }
  consume(frame){if(frame!==this.nextFrame)throw Error('Non-sequential input frame');let pressed=false;
    while(this.pending.length&&this.pending[0].frame<=frame){const e=this.pending.shift();if(e.down){this.mask|=1<<e.index;pressed=true;}else this.mask&=~(1<<e.index);}
    this.nextFrame++;return {mask:this.mask,pressed};
  }
  clearHeld(){this.mask=0;}
}
if(typeof module!=='undefined')module.exports={createCycle,SkyRoadsInputQueue};
