/* Original VGA span renderer. Geometry banks and indexed assets are decoded
 * from the original files; physics and host input scheduling are untouched.
 * Assembly basis: 2d1f..30a0,3153..3190,325b..336b,33fd..347e.
 * Full redraw replaces the original incremental copy optimization. */
function createSkyRoadsRenderer(assets,geometry){
  const u16=n=>n&65535,s16=n=>(n<<16)>>16;
  function parameters(rows,s,timer,displayHeight=s.height){
    const lane=Math.max(0,Math.min(6,Math.trunc(s16(Math.floor(s.lateral/128)-95)/46)));
    const inside=geometry.insideTunnel(rows,s.forward,s.lateral,s.height);
    const pose=inside?0:s.vertical_speed< -354||s.height<10240?2:s.vertical_speed<355?0:1;
    let frame=s.crash_ticks?Math.floor(s.crash_ticks/3):(lane*3+pose)*3+14+(s.exit_state===4?0:assets.ship_animation[Math.floor(timer/2)%4]);
    if(s.crash_ticks&&frame>=14)frame=-1;
    const support=x=>geometry.supportHeight(geometry.lookup(rows,s.forward,u16(x)),inside);
    const shadow=s.crash_ticks?32767:Math.floor(u16(s.height-Math.max(support(s.lateral-896),support(s.lateral+896)))/128);
    return [u16(Math.floor(s.lateral/128)+assets.ship_lane_offsets[lane]),u16(Math.floor(s.forward/8192)),
      frame<0?0:Math.floor(u16(displayHeight)/128),u16(frame*720),0,0,shadow,0];
  }
  function renderIndexed(rows,args,background,initial){
    const [shipX,forward,height,spriteOffset,,,shadow]=args;
    const frame=initial?new Uint8Array(initial):new Uint8Array(background);
    frame.set(background.subarray(0,44160));
    const bank=new Uint8Array(assets.banks[forward&7]);
    const word=p=>bank[p]|bank[p+1]<<8;
    const tile=(r,c)=>r>=0&&r<500&&c>=0&&c<7?(rows[r]?.[c]??0):0;
    let side=0,si=0;
    function span(skip=false){
      if(si<624||si+3>=bank.length)throw Error('Invalid original span pointer '+si);
      const color=assets.color_pairs[bank[si]]?.[side];let base=word(si+1);si+=3;
      if(!skip&&color===undefined)throw Error('Invalid original color '+bank[si-3]+' at '+(si-3));
      while(bank[si]!==255){
        const start=bank[si],width=bank[si+1];
        if(!skip){const address=side?base-1+start:base-start;
          for(let j=0;j<width;j++){const at=10240+u16(address+(side?-j:j));if(at<64000)frame[at]=color;}}
        base=u16(base+320);si+=3;
        if(si>=bank.length)throw Error('Unterminated original span');
      }
      si++;
    }
    function drawTile(r,c,table){
      const value=tile(r,c),ground=value&15,top=(value>>4)&15,kind=(value>>8)&15;
      const prevKind=(tile(r-1,c)>>8)&15,neighbor=tile(r,c+(side?-1:1)),neighborKind=(neighbor>>8)&15;
      const pointer=n=>word(table+n*2);
      function draw(n,color){si=pointer(n);if(color!==undefined)bank[si]=color;span();}
      if(ground){
        draw(0,ground);
        if(!(neighbor&15)){bank[si]=ground+30;span();}else span(true);
        if(!(tile(r-1,c)&15)){bank[si]=ground+15;span();}
      }
      switch(kind){
        case 0:return;
        case 1:
          if(prevKind<1)draw(1,67);
          si=pointer(4);for(let i=0;i<6;i++)span();
          if(prevKind<1){span();span();}return;
        case 2:
          if(prevKind<2)draw(3);
          draw(2,top||61);if(neighborKind<2)span();return;
        case 3:
          if(prevKind<2)draw(1,65);
          draw(2,top||61);if(neighborKind<2)span();
          if(prevKind<2){si=pointer(3);span(true);span();span();}return;
        case 4:
          if(prevKind<2)draw(3);
          si=pointer(2);span(true);if(neighborKind<2)span();
          draw(5,top||61);span(neighborKind>=4);if(prevKind<4)span();return;
        case 5:
          if(prevKind<2)draw(1,65);
          si=pointer(2);span(true);if(neighborKind<2)span();
          if(prevKind<2){si=pointer(3);span(true);span();span();}
          draw(5,top||61);span(neighborKind>=4);if(prevKind<4)span();return;
        default:throw Error('Unsupported original road structure '+kind);
      }
    }
    function ship(){
      const mask=new Uint8Array(33*29);let yHeight=height;
      for(let row=0;row<33;row++){
        if(yHeight>=20&&yHeight<=157){
          let left=110,right=430;const clip=assets.ship_clip[157-yHeight]??0;
          if(clip){const edge=270-clip;if(s16(shipX)>=edge)left=270+clip;else right=edge;}
          const start=Math.max(0,left-s16(shipX));
          const width=29-start-Math.max(0,s16(shipX)+29-right);
          if(start<29&&width>0)mask.fill(1,row*29+start,row*29+start+width);
        }
        yHeight=u16(yHeight-1);if(row===23)yHeight=u16(yHeight-(shadow-8));
      }
      const base=u16((157-height)*320+shipX-110);
      for(let x=0;x<29;x++)for(let y=0;y<24;y++){
        const color=assets.cars[u16(spriteOffset+x*24+y)],at=u16(base+x+y*320);
        if(color&&mask[y*29+x]){mask[y*29+x]=2;if(at<64000)frame[at]=color;}
      }
      const shadowIndex=Math.floor(shadow/5);
      if(shadowIndex<5){
        const shadowBase=u16((157-height+16+shadow)*320+shipX-110);
        for(let x=0;x<29;x++)for(let y=0;y<9;y++)if(assets.shadow_masks[shadowIndex*261+y*29+x]&&mask[(y+24)*29+x]){
          const at=u16(shadowBase+y*320+x);let color=frame[at];
          if(color===61)color=64;else if(color>0&&color<16)color+=45;
          if(at<64000)frame[at]=color;
        }
      }
    }
    for(let level=11;level>=1;level--){
      const r=(forward>>>3)+level-4,passes=level===4?[528,576]:[(11-level)*48];
      for(let pass=0;pass<passes.length;pass++){
        for(side=0;side<2;side++)for(let cell=0;cell<4;cell++)drawTile(r,side?6-cell:cell,passes[pass]+cell*12);
        if(level===4&&pass===0)ship();
      }
    }
    return frame;
  }
  function palette(index){return [...assets.road_palettes[index],...assets.carsMeta.palette_rgb6,...assets.dashboardMeta.palette_rgb6,...assets.worlds[index?Math.floor((index-1)/3):0].palette_rgb6];}
  function background(index){
    const result=new Uint8Array(64000),world=index?Math.floor((index-1)/3):0;
    result.set(assets.worldPixels[world]);
    const offset=assets.dashboardMeta.images[0].offset;
    for(let i=0;i<assets.dashboard.length;i++)if(assets.dashboard[i])result[offset+i]=assets.dashboard[i];
    return result;
  }
  function rgba(indices,index){const p=palette(index),out=new Uint8ClampedArray(indices.length*4);
    for(let i=0;i<indices.length;i++){for(let c=0;c<3;c++){const v=p[indices[i]*3+c];out[i*4+c]=(v<<2)|(v>>4);}out[i*4+3]=255;}return out;}
  return {parameters,renderIndexed,palette,background,rgba};
}
if(typeof module!=='undefined')module.exports={createSkyRoadsRenderer};
