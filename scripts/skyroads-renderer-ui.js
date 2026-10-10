/* Rendering host kept outside the deterministic physics/input/replay identity. */
(()=>{
  const fallback=draw,screen=document.createElement('canvas');screen.width=320;screen.height=200;
  const pixels=screen.getContext('2d'),diagnostic={ready:false,frames:0,max_cpu_ms:0,error:null};
  window.skyroadsGraphicsStatus=diagnostic;
  let renderer,hud,hudTimeline,cachedBackground,cachedRoad=-1,cachedKey='',cachedFrames;
  async function load(){
    const response=await fetch('/graphics/manifest.json');if(!response.ok)throw Error('Grafikresurser kunde inte läsas');
    const meta=await response.json();
    async function read(file){const r=await fetch('/graphics/'+file);if(!r.ok)throw Error('Grafikresurs saknas: '+file);return new Uint8Array(await r.arrayBuffer());}
    const [cars,dashboard,worldPixels,banks,hudAssets]=await Promise.all([read(meta.cars.images[0].file),read(meta.dashboard.images[0].file),
      Promise.all(meta.worlds.map(w=>read(w.images[0].file))),Promise.all(meta.trek_banks.map(b=>read(b.file))),
      fetch('/graphics/hud-manifest.json').then(r=>{if(!r.ok)throw Error('Instrumentresurser kunde inte läsas');return r.json();})]);
    renderer=createSkyRoadsRenderer({...meta,carsMeta:meta.cars,dashboardMeta:meta.dashboard,cars,dashboard,worldPixels,banks},
      createGeometry((await api('/api/catalog')).tables));
    hud=createSkyRoadsHud(hudAssets);
    diagnostic.ready=true;document.querySelector('.stage-caption span').textContent='Originalets banor, färger och skepp';dirty=true;
  }
  draw=function(){
    if(!renderer||!catalog||!state){fallback();return;}
    const started=performance.now(),index=Number($('road').value),rows=road().rows;
    let shown=Number($('timeline').value);
    // The existing presentation contract holds the last picture during pause
    // and return. Use that picture's timer for original ship animation too.
    while(shown>0){const f=frames[shown],previous=frames[shown-1];
      if(f.attempt_number!==previous.attempt_number||f.game_phase==='attempt'&&['playing','finishing'].includes(f.phase))break;
      shown--;
    }
    const snapshot=frames[shown],s=snapshot.state,args=renderer.parameters(rows,s,snapshot.timer,presentationFrames[shown].height);
    if(cachedRoad!==index){cachedBackground=renderer.background(index);cachedRoad=index;
      hudTimeline=createSkyRoadsHudTimeline(hud,cachedBackground,road().metadata[0],rows.length);}
    if(cachedFrames!==frames){cachedFrames=frames;cachedKey='';}
    hudTimeline.sync(frames);const instruments=hudTimeline.get(Number($('timeline').value));
    const key=index+':'+args.slice(0,4).join(',')+':'+args[6]+':'+instruments.image.id;
    if(key!==cachedKey){const frame=renderer.renderIndexed(rows,args,cachedBackground);
      frame.set(instruments.image.pixels,44160);
      pixels.putImageData(new ImageData(renderer.rgba(frame,index),320,200),0,0);cachedKey=key;diagnostic.frames++;}
    $('hudDetails').textContent=JSON.stringify({hastighet:instruments.levels.speed+' / 34',syre:instruments.levels.oxygen+' / 10',
      bränsle:instruments.levels.fuel+' / 10',banförlopp:instruments.levels.progress+' / 30',
      hoppassistans:instruments.levels.assist,gravitation:(road().metadata[0]-3)*100},null,2);
    const [w,h]=resize(view),scale=Math.min(w/4,h/3),dw=scale*4,dh=scale*3;
    ctx.fillStyle='#080c13';ctx.fillRect(0,0,w,h);ctx.imageSmoothingEnabled=false;
    ctx.drawImage(screen,(w-dw)/2,(h-dh)/2,dw,dh);
    const [mw,mh]=resize(map),row=displayedState.forward/65536,base=Math.floor(row)-2,cell=mw/7,rh=mh/15;
    const palette=renderer.palette(index),color=n=>'rgb('+palette.slice(n*3,n*3+3).map(v=>(v<<2)|(v>>4)).join(',')+')';
    mctx.fillStyle='#080c13';mctx.fillRect(0,0,mw,mh);
    for(let k=0;k<15;k++){const r=base+k;if(!rows[r])continue;for(let c=0;c<7;c++){
      const v=rows[r][c],y=mh-(k+1)*rh;if(v&15){mctx.fillStyle=color(v&15);mctx.fillRect(c*cell+1,y+1,cell-2,rh-2);}
      if(v&0xf00){mctx.strokeStyle='#ffffffaa';mctx.strokeRect(c*cell+3,y+3,cell-6,rh-6);}
    }}
    mctx.fillStyle='#fff';mctx.beginPath();mctx.arc((displayedState.lateral-12160)/(7*5888)*mw,mh-((row-base)+.5)*rh,4*(devicePixelRatio||1),0,Math.PI*2);mctx.fill();
    diagnostic.max_cpu_ms=Math.max(diagnostic.max_cpu_ms,performance.now()-started);
  };
  load().catch(e=>{diagnostic.error=e.message;status(e.message,true);});
})();
