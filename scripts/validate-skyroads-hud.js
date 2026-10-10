/* Independent original instrument rasterization against native VGA RAM. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..'),OUT=path.join(ROOT,'analysis/skyroads'),G=path.join(OUT,'graphics');
const read=p=>new Uint8Array(fs.readFileSync(p)),json=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const meta=json(path.join(G,'manifest.json')),assets={...meta,carsMeta:meta.cars,dashboardMeta:meta.dashboard,
 cars:read(path.join(G,meta.cars.images[0].file)),dashboard:read(path.join(G,meta.dashboard.images[0].file)),
 worldPixels:meta.worlds.map(w=>read(path.join(G,w.images[0].file))),banks:meta.trek_banks.map(b=>read(path.join(G,b.file)))};
const hudMeta=json(path.join(G,'hud-manifest.json')),hud=require('./skyroads-hud.js').createSkyRoadsHud(hudMeta);
const geometry=require('./skyroads-geometry.js').createGeometry(json(path.join(OUT,'collision-validation.json')).tables);
const renderer=require('./skyroads-renderer.js').createSkyRoadsRenderer(assets,geometry),roads=json(path.join(OUT,'roads/manifest.json')).roads;
const keys=['speed','oxygen','fuel','progress','assist','blink'];
assert.equal(sha(path.join(ROOT,'scripts/extract-skyroads-hud.py')),hudMeta.extractor_sha256);
assert.equal(sha(path.join(OUT,'runtime-load-image.bin')),hudMeta.module_sha256);
for(const a of Object.values(hudMeta.instruments)){
 assert.equal(sha(path.join(ROOT,'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10',a.source)),a.source_sha256);
 assert.equal(sha(path.join(G,a.file)),a.sha256);
}
assert.equal(sha(path.join(G,hudMeta.symbols.file)),hudMeta.symbols.sha256);
const coverage=Object.fromEntries(keys.map(k=>[k,new Set()])),roadSet=new Set(),runs=[],digest=crypto.createHash('sha256');
let updates=0,frames=0,pixels=0,initials=0,sequential=0;
function equalPixels(a,b,start,end,label){
 let count=0,first=[];for(let i=start;i<end;i++)if(a[i]!==b[i]){count++;if(first.length<8)first.push({x:i%320,y:Math.floor(i/320),actual:a[i],original:b[i]});}
 assert.equal(count,0,label+' '+JSON.stringify(first));
}
for(const arg of process.argv.slice(2)){
 const run=path.resolve(arg),manifest=json(path.join(run,'manifest.json')),events=fs.readFileSync(path.join(run,'trace.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
 assert(manifest.exit_code===0&&manifest.original_files_unchanged&&manifest.hud_observation&&!manifest.guest_program_patched);
 for(const [name,key] of [['probe-source.h','probe_sha256'],['runner-source.py','runner_sha256'],['dosbox.conf','config_sha256'],['emulator-build.json','build_manifest_sha256']])assert.equal(sha(path.join(run,name)),manifest[key]);
 for(const [name,h] of Object.entries(manifest.source_sha256))assert.equal(sha(path.join(manifest.source,name)),h);
 assert(events.at(-1).kind==='stop'&&events.at(-1).sessions>=manifest.requested_sessions);
 let index,before,cached,id,expected,complete,continuousCache,continuousAttempt=-1,initialAttempt=-1,count=0,steps=0;
 for(const e of events){
  if(e.kind==='initial'){index=e.mode===3?0:e.selected+1;roadSet.add(index);}
  else if(e.kind==='hud_step'){
   if(continuousAttempt!==e.attempt){continuousAttempt=e.attempt;complete=renderer.background(index);continuousCache=hud.initialize(complete,e.config[0]);}
   continuousCache=hud.update(complete,continuousCache,e.state,e.timer,e.config[3]);steps++;updates++;
  }
  else if(e.kind==='hud_before')before=e;
  else if(e.kind==='hud_cache'&&e.stage==='hud_before'){
   cached=Object.fromEntries(keys.map((k,i)=>[k,e.values[i]]));id=e.id;
   expected=read(path.join(run,`trace.jsonl.hud-${id}.before.bin`));
   if(initialAttempt!==before.attempt){initialAttempt=before.attempt;
    const base=renderer.background(index);hud.initialize(base,before.config[0]);
    equalPixels(base,expected,44160,64000,`${path.basename(run)}/${id}/initial dashboard`);initials++;
    for(const key of ['speed','oxygen','fuel'])assert.deepEqual(read(path.join(run,`trace.jsonl.hud-${id}.${key}.bin`)),read(path.join(G,hudMeta.instruments[key].file)),'Native '+key+' masks');
    assert.deepEqual(read(path.join(run,`trace.jsonl.hud-${id}.symbols.bin`)),read(path.join(G,hudMeta.symbols.file)),'Native symbols');
   }
   cached=hud.update(expected,cached,before.state,before.timer,before.config[3]);
  }
  else if(e.kind==='hud_cache'&&e.stage==='hud_after'){
   assert.equal(e.id,id);assert.deepEqual(keys.map(k=>cached[k]),e.values,'Native HUD counters');
   const native=read(path.join(run,`trace.jsonl.hud-${id}.after.bin`));
   equalPixels(expected,native,0,64000,`${path.basename(run)}/${id}/single update`);
   if(steps){equalPixels(complete,native,44160,64000,`${path.basename(run)}/${id}/continuous dashboard`);sequential++;}
   for(const k of keys)coverage[k].add(cached[k]);digest.update(native.subarray(44160));frames++;pixels+=64000;count++;
  }
 }
 runs.push({run:path.basename(run),frames:count,continuous_updates:steps,trace_sha256:sha(path.join(run,'trace.jsonl')),manifest_sha256:sha(path.join(run,'manifest.json'))});
}
assert(frames>0);
const report={verified:true,native_updates_match:frames,pixels_compared:pixels,initialized_dashboards_match:initials,
 continuous_updates:updates,continuous_dashboard_frames_match:sequential,road_indices:[...roadSet].sort((a,b)=>a-b),
 counter_coverage:Object.fromEntries(keys.map(k=>[k,[...coverage[k]].sort((a,b)=>a-b)])),
 renderer_sha256:sha(path.join(ROOT,'scripts/skyroads-hud.js')),manifest_sha256:sha(path.join(G,'hud-manifest.json')),
 result_sha256:digest.digest('hex'),runs,limits:['Each single update compares all 64000 VGA bytes, preserving its native input frame. Continuous reconstruction compares the 320x62 dashboard below the original scene allocation.','Finite native coverage; additional isolated original-code cases cover resource warnings and boundary values.','Physical keyboard/display latency and wrapper fades are separate work.']};
fs.writeFileSync(path.join(OUT,'hud-validation.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
