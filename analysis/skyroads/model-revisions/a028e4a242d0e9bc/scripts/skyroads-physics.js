/* Integer port. Intermediate wrap/division boundaries mirror the verified
 * Python/x86 core. No elapsed seconds or interpolated values enter physics. */
function createPhysics(tables) {
  const geometry=typeof createGeometry==='function'?createGeometry(tables):require('./skyroads-geometry.js').createGeometry(tables);
  const u16=n=>n&65535,u32=n=>n>>>0,s16=n=>(n<<16)>>16,s32=n=>n|0,div=(n,d)=>Math.trunc(n/d)||0;
  const abs16=n=>{n=s16(n);return n<=0?s16(-n):n;};
  const clamp=n=>Math.max(0,Math.min(10922,s32(n)));
  const defaults={forward:196608,lateral:32768,height:10240,speed:0,steering:0,vertical_speed:0,drift:0,
    speed_delta:0,assist_flag:0,fuel:30000,oxygen:30000,exit_state:0,crash_ticks:0,end_ticks:0,sound_tick:0,
    tick_counter:0,assist_used:0,jumping:0,jump_height:10240,grounded:1,surface8:0,surface2:0,
    edge_distance:0,previous_target_height:10240};
  const signed=new Set(['steering','vertical_speed','drift']),wide=new Set(['forward','speed','speed_delta']);
  function wrap(state){const s={};for(const k of Object.keys(defaults))s[k]=(wide.has(k)?u32:signed.has(k)?s16:u16)(state[k]??defaults[k]);return s;}
  const pos=p=>({forward:u32(p.forward),lateral:u16(p.lateral),height:u16(p.height)});
  function resolve(rows,current,target,emit=()=>{}){
    current=pos(current);target=pos(target);
    if(Object.keys(current).every(k=>current[k]===target[k]))return current;
    let probes=0;
    function hit(p){if(++probes>4096)throw Error('Movement probe budget exceeded');emit('collision',p.forward,p.lateral,p.height);return geometry.positionHit(rows,p.forward,p.lateral,p.height);}
    const fraction=n=>({forward:u32(current.forward+div(s32((target.forward-current.forward)*n),5)),
      lateral:u16(current.lateral+div(s16((target.lateral-current.lateral)*n),5)),height:u16(current.height+div(s16((target.height-current.height)*n),5))});
    let n=1;for(;n<=5;n++)if(hit(fraction(n)))break;
    let p=fraction(n-1);
    for(const step of [4096,256,16,1])while(step<=u32(target.forward-p.forward)){
      const candidate={...p,forward:u32(p.forward+step)};if(hit(candidate))break;p=candidate;
    }
    for(const axis of ['lateral','height']){
      const goal=target[axis];let step=p[axis]<goal?125:-125;
      while(step){while(abs16(goal-p[axis])>=Math.abs(step)){
        const candidate={...p,[axis]:u16(p[axis]+step)};if(hit(candidate))break;p=candidate;
      }step=div(step,5);}
    }return p;
  }
  function predict(rows,flight,env,emit=()=>{}){
    let {forward:f,lateral:x,height:y}=pos(flight.position),speed=u32(flight.speed),steering=s16(flight.steering),vertical=s16(flight.vertical_speed);
    emit('predict',f,x,y,speed,steering,vertical);
    for(let i=0;i<1024;i++){
      emit('flight',f,x,y,speed,vertical);const pf=f,px=x;
      vertical=s16(vertical+env.gravity);f=u32(f+speed);
      x=u16(x+div(s32(u32(speed+1560)*steering),512)+env.drift);
      if(x<12160||x>53376)return 0;
      y=u16(y+vertical);speed=u32(clamp(speed+s16(env.throttle)*75));
      if(y<=10240){for(const [lf,lx] of [[pf,px],[f,x]]){
        emit('landing',lf,lx);if(geometry.unsafeLanding(geometry.lookup(rows,lf,lx)))return 0;
      }return 1;}
    }throw Error('Landing prediction tick budget exceeded');
  }
  function adjust(rows,flight,env,emit=()=>{}){
    if(predict(rows,flight,env,emit))return flight;
    for(let n=1;n<=6;n++){
      const ds=div(s16(flight.steering*n),10),dv=div(s32(flight.speed*n),10),faster=u32(flight.speed+dv);
      const candidates=[{...flight,steering:s16(flight.steering+ds)},{...flight,steering:s16(flight.steering-ds)}];
      if(s32(faster)<10922)candidates.push({...flight,speed:faster});
      candidates.push({...flight,speed:u32(flight.speed-dv)});
      for(const c of candidates)if(predict(rows,c,env,emit))return {...c,speed_delta:u32(c.speed-flight.speed),assist_flag:1};
    }return {...flight,speed_delta:0};
  }
  function tick(rows,state,config,controls,observer){
    const s=wrap(state),timer=u16(controls.timer),emit=(...e)=>{if(observer)observer(e);};
    const sound=which=>{emit('sound',which);s.sound_tick=timer;};
    const hit=(f,x,y)=>{f=u32(f);x=u16(x);y=u16(y);emit('collision',f,x,y);return geometry.positionHit(rows,f,x,y);};
    const gravity=s16(-Math.floor(u16(config.gravity_factor)*5760/400));
    const tile=geometry.lookup(rows,s.forward,s.lateral),tilePresent=tile!==0;
    if(s.grounded){let surface=tile;
      if(s.height>10240){const kind=tile>>8;if(kind>=tables.support.length)throw Error('Unsupported structure table index');surface=s.height===tables.support[kind]?tile>>4:0;}
      const kind=surface&15;
      if(kind===2&&!s.crash_ticks)s.speed=u32(s.speed-303);
      else if(kind===9&&!s.exit_state){if(s.fuel<27000||s.oxygen<27000)sound(4);s.fuel=s.oxygen=30000;}
      else if(kind===10&&!s.crash_ticks)s.speed=u32(s.speed+303);
      else if(kind===12){if(!s.exit_state)s.exit_state=2;if(!s.crash_ticks){s.crash_ticks=1;sound(0);}}
      s.speed=clamp(s.speed);s.surface8=+(kind===8);s.surface2=+(kind===2);
    }else s.surface2=0;
    const endForward=u32(u16(config.road_rows)*65536-32768);
    if(s.forward>=endForward&&geometry.insideTunnel(rows,s.forward,s.lateral,s.height)&&!s.exit_state){emit('finish');return {state:s,completion_requested:true};}
    if(s.height!==s.previous_target_height){
      const threshold=Math.floor(u16(u16(config.gravity_factor)*260)/8),mag=s.vertical_speed<=0?u16(-s.vertical_speed):s.vertical_speed;
      if((s.drift===0||s.edge_distance>=2)&&mag>=threshold&&!s.crash_ticks){
        if(!s.exit_state&&s.vertical_speed<0){const busy=timer<u16(s.sound_tick+8);emit('sound_busy',+busy);if(!busy)sound(1);}
        s.vertical_speed=div(s16(-5*s.vertical_speed),10);
      }else s.vertical_speed=0;
    }
    if(!s.exit_state){
      s.speed=clamp(s.speed+s16(controls.throttle)*75);
      if(!s.surface8&&((!s.jumping&&tilePresent)||(s.steering===0&&s.vertical_speed>0&&u16(s.height-s.jump_height)<3840)))s.steering=s16(s16(controls.direction)*29);
      if(!s.jumping&&tilePresent&&u16(controls.jump)&&u16(config.gravity_factor)<20){s.vertical_speed=1152;s.jumping=1;s.jump_height=s.height;}
    }
    if(u16(config.assist_enabled)&&s.jumping&&!s.assist_used&&s.height>=14080){
      const result=adjust(rows,{position:pos(s),speed:s.speed,steering:s.steering,vertical_speed:s.vertical_speed,speed_delta:s.speed_delta,assist_flag:s.assist_flag},
        {gravity,drift:s.drift,throttle:controls.throttle},emit);
      for(const k of ['speed','steering','speed_delta','assist_flag'])s[k]=result[k];s.assist_used=1;
    }
    if(!s.crash_ticks){if(s.height<10240)s.vertical_speed=Math.min(s.vertical_speed,-106);else s.vertical_speed=s16(s.vertical_speed+gravity);}
    else {s.vertical_speed=Math.max(s.vertical_speed,0);s.vertical_speed=s.vertical_speed<71?s16(s.vertical_speed+39):71;}
    let tf=u32(s.forward+s.speed),tx=u16(s.lateral+s.drift+div(s32(u32(s.speed+(s.surface2?0:1560))*s.steering),512)),ty=u16(s.height+s.vertical_speed);
    if((s.lateral<12160&&tx>53376)||(tx<12160&&s.lateral>53376))tx=s.lateral;
    s.previous_target_height=ty;emit('resolve',tf,tx,ty);Object.assign(s,resolve(rows,pos(s),{forward:tf,lateral:tx,height:ty},emit));
    if(s.forward!==tf&&s.lateral===tx&&hit(tf,s.lateral,s.height))for(const side of [-928,928])if(!hit(tf,s.lateral+side,s.height)){s.lateral=u16(s.lateral+side);tf=s.forward;sound(2);break;}
    if(s.forward!==tf){if(s32(s.speed)<3640||s.crash_ticks){if(s.forward>u32(tf-s.speed))sound(2);}else{s.crash_ticks=1;sound(0);if(!s.exit_state)s.exit_state=1;}s.speed=0;}
    if(s.lateral!==tx){s.steering=0;if((s.drift>0&&s.lateral<tx)||(s.drift<0&&tx<s.lateral))s.drift=0;s.speed=clamp(s.speed-151);}
    s.grounded=0;
    if(s.height!==ty&&s.vertical_speed<0){s.assist_flag=s.assist_used=s.jumping=0;s.grounded=1;s.speed=clamp(s.speed-s.speed_delta);s.speed_delta=0;
      let edge=0;for(const sign of [1,-1])for(let distance=1;distance<15;distance++)if(!hit(s.forward,s.lateral+sign*distance*128,s.height-1)){edge+=sign;s.edge_distance=distance;break;}
      s.drift=edge?s16(s.drift+edge*17):0;
    }
    if(s.height>32767)s.height=0;
    if(!s.exit_state){const oxygenDiv=u16(config.oxygen_factor*36),fuelDiv=u16(config.fuel_divisor);if(!oxygenDiv||!fuelDiv)throw Error('Zero resource divisor');
      s.oxygen=u16(s.oxygen-Math.floor(30000/oxygenDiv));if(s.oxygen>30000)s.oxygen=0;
      const drain=div(s32(Math.floor(30000/fuelDiv)*s.speed),65536);s.fuel=u16(s.fuel-drain);if(s.fuel>30000)s.fuel=0;
    }
    if(!s.exit_state){if(s.height<10240)s.exit_state=3;if(s.fuel===0)s.exit_state=4;if(s.oxygen===0)s.exit_state=5;}
    else s.end_ticks=u16(s.end_ticks+1);
    if(s.crash_ticks)s.crash_ticks=u16(s.crash_ticks+1);s.tick_counter=u16(s.tick_counter+1);
    return {state:s,completion_requested:false};
  }
  return {tick,resolve,predict,adjust,defaults,geometry};
}
if(typeof module!=='undefined')module.exports={createPhysics};
